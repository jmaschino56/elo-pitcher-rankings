"""
ELO rating system for pitcher rankings.

Implements standard ELO algorithm with Supabase database persistence.
"""

import pandas as pd
from typing import Tuple
import streamlit as st
from supabase import create_client, Client

# ELO Configuration
DEFAULT_RATING = 1500
K_FACTOR = 32

# Initialize Supabase client
@st.cache_resource
def get_supabase_client() -> Client:
    """Get cached Supabase client."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def calculate_expected_score(rating_a: float, rating_b: float) -> float:
    """
    Calculate expected score for player A against player B.

    Args:
        rating_a: ELO rating of player A
        rating_b: ELO rating of player B

    Returns:
        Expected score between 0 and 1 (probability player A wins)
    """
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def update_ratings(winner_rating: float, loser_rating: float) -> Tuple[float, float]:
    """
    Update ELO ratings after a matchup.

    Args:
        winner_rating: Current ELO rating of the winner
        loser_rating: Current ELO rating of the loser

    Returns:
        Tuple of (new_winner_rating, new_loser_rating)
    """
    # Calculate expected scores
    winner_expected = calculate_expected_score(winner_rating, loser_rating)
    loser_expected = calculate_expected_score(loser_rating, winner_rating)

    # Update ratings
    # Actual score is 1 for winner, 0 for loser
    new_winner_rating = winner_rating + K_FACTOR * (1 - winner_expected)
    new_loser_rating = loser_rating + K_FACTOR * (0 - loser_expected)

    return new_winner_rating, new_loser_rating


def load_ratings(award_category: str) -> pd.DataFrame:
    """
    Load ELO ratings from Supabase for a specific award category.

    Args:
        award_category: Award category key

    Returns:
        DataFrame with columns: player_id, player_name, elo_rating, matches_played
    """
    supabase = get_supabase_client()

    try:
        response = supabase.table("elo_ratings").select("*").eq("award_category", award_category).execute()

        if response.data:
            df = pd.DataFrame(response.data)
            # Return only needed columns
            return df[["player_id", "player_name", "elo_rating", "matches_played"]]
        else:
            # Return empty DataFrame with correct schema
            return pd.DataFrame(columns=["player_id", "player_name", "elo_rating", "matches_played"])
    except Exception as e:
        st.error(f"Error loading ratings: {e}")
        return pd.DataFrame(columns=["player_id", "player_name", "elo_rating", "matches_played"])


def update_player_rating(award_category: str, player_id: int, player_name: str,
                         new_rating: float, matches_played: int) -> None:
    """
    Update or insert a player's rating in Supabase.

    Args:
        award_category: Award category key
        player_id: MLB Advanced Media ID
        player_name: Player full name
        new_rating: New ELO rating
        matches_played: Total matches played
    """
    supabase = get_supabase_client()

    try:
        # Upsert: insert or update if exists
        # Convert numpy types to native Python types for JSON serialization
        data = {
            "award_category": award_category,
            "player_id": int(player_id),
            "player_name": player_name,
            "elo_rating": float(new_rating),
            "matches_played": int(matches_played)
        }

        supabase.table("elo_ratings").upsert(data, on_conflict="award_category,player_id").execute()
    except Exception as e:
        st.error(f"Error updating rating: {e}")


def get_or_create_player_rating(
    ratings_df: pd.DataFrame,
    player_id: int,
    player_name: str
) -> float:
    """
    Get existing rating for a player, or create new entry with default rating.

    Args:
        ratings_df: Current ratings DataFrame
        player_id: MLB Advanced Media ID
        player_name: Player full name

    Returns:
        Current ELO rating for the player
    """
    player_row = ratings_df[ratings_df["player_id"] == player_id]

    if len(player_row) > 0:
        return player_row.iloc[0]["elo_rating"]
    else:
        # New player - initialize with default rating
        return DEFAULT_RATING


def record_matchup(
    award_category: str,
    winner_id: int,
    winner_name: str,
    loser_id: int,
    loser_name: str
) -> Tuple[float, float]:
    """
    Record a matchup result and update ELO ratings.

    Args:
        award_category: Award category key
        winner_id: MLB ID of winning player
        winner_name: Name of winning player
        loser_id: MLB ID of losing player
        loser_name: Name of losing player

    Returns:
        Tuple of (new_winner_rating, new_loser_rating)
    """
    # Load current ratings
    ratings_df = load_ratings(award_category)

    # Get current ratings
    winner_rating = get_or_create_player_rating(ratings_df, winner_id, winner_name)
    loser_rating = get_or_create_player_rating(ratings_df, loser_id, loser_name)

    # Calculate new ratings
    new_winner_rating, new_loser_rating = update_ratings(winner_rating, loser_rating)

    # Get current match counts
    winner_matches = 0
    loser_matches = 0

    winner_row = ratings_df[ratings_df["player_id"] == winner_id]
    if len(winner_row) > 0:
        winner_matches = winner_row.iloc[0]["matches_played"]

    loser_row = ratings_df[ratings_df["player_id"] == loser_id]
    if len(loser_row) > 0:
        loser_matches = loser_row.iloc[0]["matches_played"]

    # Update both players in database
    update_player_rating(award_category, winner_id, winner_name, new_winner_rating, winner_matches + 1)
    update_player_rating(award_category, loser_id, loser_name, new_loser_rating, loser_matches + 1)

    return new_winner_rating, new_loser_rating


def get_leaderboard(award_category: str, top_n: int = None) -> pd.DataFrame:
    """
    Get top N players by ELO rating for an award category.

    Args:
        award_category: Award category key
        top_n: Number of top players to return (None returns all)

    Returns:
        DataFrame with top players sorted by ELO rating
    """
    ratings_df = load_ratings(award_category)

    if ratings_df.empty:
        return ratings_df

    # Sort by rating and return top N (or all if top_n is None)
    sorted_df = ratings_df.sort_values("elo_rating", ascending=False)
    return sorted_df.head(top_n) if top_n is not None else sorted_df