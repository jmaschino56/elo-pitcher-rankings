"""
Data fetching module for MLB pitcher data from multiple APIs.

This module handles API calls to:
- FanGraphs (pitching statistics)
- proPitching+ (advanced metrics)
- MLB Stats API (player biographical info, images, team data)
"""

import requests
from typing import Dict, List, Optional
import streamlit as st


# Award category to FanGraphs API parameter mapping
AWARD_CATEGORIES = {
    "al_cy_young": {"stats": "pit", "lg": "al", "ind": 0},
    "nl_cy_young": {"stats": "pit", "lg": "nl", "ind": 0},
    "al_mariano_rivera": {"stats": "rel", "lg": "al", "ind": 0},
    "nl_trevor_hoffman": {"stats": "rel", "lg": "nl", "ind": 0},
    "al_rookie": {"stats": "pit", "lg": "al", "ind": 2},
    "nl_rookie": {"stats": "pit", "lg": "nl", "ind": 2},
}


@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_fangraphs_data(award_category: str, season: int = 2025) -> List[Dict]:
    """
    Fetch pitching statistics from FanGraphs API.

    Args:
        award_category: One of the AWARD_CATEGORIES keys
        season: MLB season year (default: 2025)

    Returns:
        List of player dictionaries with pitching stats

    Raises:
        ValueError: If award_category is invalid
        requests.RequestException: If API call fails
    """
    if award_category not in AWARD_CATEGORIES:
        raise ValueError(f"Invalid award category: {award_category}")

    params = AWARD_CATEGORIES[award_category]

    # Build FanGraphs API URL
    url = "https://www.fangraphs.com/api/leaders/major-league/data"
    query_params = {
        "age": "",
        "pos": "all",
        "stats": params["stats"],
        "lg": params["lg"],
        "qual": "y",
        "season": season,
        "season1": season,
        "startdate": f"{season}-03-01",
        "enddate": f"{season}-11-01",
        "month": 0,
        "hand": "",
        "team": 0,
        "pageitems": 50,  # Get top 50 qualified pitchers
        "pagenum": 1,
        "ind": params["ind"],
        "rost": 0,
        "players": "",
        "type": 8,  # Standard pitching stats
        "postseason": "",
        "sortdir": "default",
        "sortstat": "WAR"
    }

    response = requests.get(url, params=query_params, timeout=30)
    response.raise_for_status()

    data = response.json()

    # FanGraphs wraps data in a "data" key
    if isinstance(data, dict) and "data" in data:
        return data["data"]

    return data


@st.cache_data(ttl=3600)
def fetch_propitching_data() -> List[Dict]:
    """
    Fetch advanced pitching metrics from proPitching+ API.

    Returns:
        List of pitcher records with Pitching_plus metric

    Raises:
        requests.RequestException: If API call fails
    """
    url = "https://g837e5a6fbcb0dd-ch2sockkby63dgzo.adb.us-chicago-1.oraclecloudapps.com/ords/admin/pitcher_leaderboards/GET_SEASON"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()

    # proPitching+ wraps data in an "items" key
    if isinstance(data, dict) and "items" in data:
        return data["items"]

    return data


@st.cache_data(ttl=3600)
def fetch_mlb_player_info(mlbam_id: int) -> Optional[Dict]:
    """
    Fetch player biographical info and current team from MLB Stats API.

    Args:
        mlbam_id: MLB Advanced Media player ID (xMLBAMID from FanGraphs)

    Returns:
        Dictionary with player info, or None if not found
        Contains: nameFirstLast, currentTeam (id and name)

    Raises:
        requests.RequestException: If API call fails
    """
    url = f"https://statsapi.mlb.com/api/v1/people/{mlbam_id}"
    params = {"hydrate": "currentTeam"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        # MLB API wraps data in a "people" array
        if "people" in data and len(data["people"]) > 0:
            player = data["people"][0]

            # Extract relevant fields
            result = {
                "nameFirstLast": player.get("fullName", "Unknown"),
                "currentTeamID": None,
                "currentTeamName": None
            }

            # Get current team if available
            if "currentTeam" in player:
                result["currentTeamID"] = player["currentTeam"].get("id")
                result["currentTeamName"] = player["currentTeam"].get("name")

            return result

        return None

    except requests.RequestException as e:
        # Log error but don't fail - we can continue without this player's info
        print(f"Error fetching MLB player info for ID {mlbam_id}: {e}")
        return None


def get_player_image_url(mlbam_id: int) -> str:
    """
    Generate URL for player headshot image.

    Args:
        mlbam_id: MLB Advanced Media player ID

    Returns:
        URL string for player image (includes fallback to generic headshot)
    """
    return f"https://img.mlbstatic.com/mlb-photos/image/upload/w_175,d_people:generic:headshot:silo:current.png,q_auto:best,f_auto/v1/people/{mlbam_id}/headshot/silo/current"


def get_team_logo_url(team_id: int) -> str:
    """
    Generate URL for team logo SVG.

    Args:
        team_id: MLB team ID from currentTeam

    Returns:
        URL string for team logo
    """
    return f"https://www.mlbstatic.com/team-logos/{team_id}.svg"