"""
Data processing module for merging and formatting pitcher data.

This module combines data from multiple sources (FanGraphs, proPitching+, MLB API)
into a single formatted DataFrame ready for display and voting.
"""

import pandas as pd
from typing import Dict, List
import streamlit as st
from data_fetcher import (
    fetch_fangraphs_data,
    fetch_propitching_data,
    fetch_mlb_player_info,
    get_player_image_url,
    get_team_logo_url
)


@st.cache_data(ttl=3600)
def get_pitcher_data(award_category: str, season: int = 2025) -> pd.DataFrame:
    """
    Get complete pitcher data for an award category.

    Merges data from FanGraphs, proPitching+, and MLB Stats API.

    Args:
        award_category: Award category key (e.g., "al_cy_young")
        season: MLB season year (default: 2025)

    Returns:
        DataFrame with columns:
        - nameFirstLast: Player full name
        - xMLBAMID: MLB Advanced Media ID
        - currentTeamID: Team ID
        - currentTeamName: Team name
        - IP: Innings pitched (1 decimal)
        - ERA: Earned run average (2 decimals)
        - FIP: Fielding independent pitching (2 decimals)
        - WAR: Wins above replacement (1 decimal, labeled as fWAR)
        - proStuff+: Advanced metric (rounded int)
        - player_image_url: URL for player headshot
        - team_logo_url: URL for team logo
    """
    # Step 1: Fetch FanGraphs data
    fg_data = fetch_fangraphs_data(award_category, season)

    if not fg_data:
        return pd.DataFrame()

    # Convert to DataFrame
    fg_df = pd.DataFrame(fg_data)

    # Step 2: Fetch proPitching+ data
    try:
        pp_data = fetch_propitching_data()
        pp_df = pd.DataFrame(pp_data)

        # Filter for the current season
        pp_df = pp_df[pp_df["game_year"] == season]

        # Filter for regular season games only (exclude spring training, playoffs, etc.)
        if "game_type" in pp_df.columns:
            pp_df = pp_df[pp_df["game_type"] == "R"]

        # Rename columns for merging
        pp_df = pp_df.rename(columns={"pitcher_id": "xMLBAMID"})

        # Keep only relevant columns
        pp_df = pp_df[["xMLBAMID", "stuff_plus"]]

        # Remove duplicates - keep first entry per pitcher
        pp_df = pp_df.drop_duplicates(subset=["xMLBAMID"], keep="first")

    except Exception as e:
        print(f"Warning: Could not fetch proPitching+ data: {e}")
        pp_df = pd.DataFrame(columns=["xMLBAMID", "stuff_plus"])

    # Step 3: Merge FanGraphs with proPitching+
    df = fg_df.merge(pp_df, on="xMLBAMID", how="left")

    # Step 4: Fetch MLB player info for each player
    player_info = []
    for mlbam_id in df["xMLBAMID"].values:
        info = fetch_mlb_player_info(int(mlbam_id))
        if info:
            player_info.append({
                "xMLBAMID": mlbam_id,
                "nameFirstLast": info["nameFirstLast"],
                "currentTeamID": info["currentTeamID"],
                "currentTeamName": info["currentTeamName"]
            })
        else:
            # Fallback if MLB API fails
            player_info.append({
                "xMLBAMID": mlbam_id,
                "nameFirstLast": "Unknown",
                "currentTeamID": None,
                "currentTeamName": "Unknown"
            })

    player_df = pd.DataFrame(player_info)

    # Step 5: Merge with player info
    df = df.merge(player_df, on="xMLBAMID", how="left")

    # Step 6: Select and format final columns
    final_df = pd.DataFrame({
        "nameFirstLast": df["nameFirstLast"],
        "xMLBAMID": df["xMLBAMID"],
        "currentTeamID": df["currentTeamID"],
        "currentTeamName": df["currentTeamName"],
        "IP": df["IP"].round(1),
        "ERA": df["ERA"].round(2),
        "FIP": df["FIP"].round(2),
        "K-BB%": (df["K-BB%"] * 100).round(1).astype(str) + "%",  # Convert to percentage string
        "fWAR": df["WAR"].round(1),  # Rename WAR to fWAR
        "proStuff+": df["stuff_plus"].fillna(100).round(0).astype(int),  # Default 100 if missing
        "player_image_url": df["xMLBAMID"].apply(lambda x: get_player_image_url(int(x))),
        "team_logo_url": df["currentTeamID"].apply(
            lambda x: get_team_logo_url(int(x)) if pd.notna(x) else ""
        )
    })

    # Remove any rows with missing critical data
    final_df = final_df.dropna(subset=["nameFirstLast", "xMLBAMID"])

    # Keep only top 20 pitchers by fWAR
    final_df = final_df.nlargest(20, 'fWAR')

    return final_df


def format_player_stats_table(player: pd.Series) -> str:
    """
    Format a player's statistics as an HTML table for display.

    Args:
        player: Series containing player stats

    Returns:
        HTML string for stats table
    """
    return f"""
    <table style="width:100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>IP</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{player['IP']}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>ERA</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{player['ERA']}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>FIP</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{player['FIP']}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>proStuff+</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{player['proStuff+']}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>fWAR</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{player['fWAR']}</td>
        </tr>
    </table>
    """