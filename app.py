"""
MLB Pitcher ELO Ranking System - Streamlit App

Interactive voting application for ranking MLB pitchers using ELO ratings.
"""

import streamlit as st
import pandas as pd
import random
from data_processor import get_pitcher_data
from elo_system import record_matchup, get_leaderboard

# Page configuration
st.set_page_config(
    page_title="MLB Pitcher ELO Rankings",
    page_icon="⚾",
    layout="wide"
)

# Load custom CSS
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Award category display names
AWARD_NAMES = {
    "al_cy_young": "AL Cy Young Award",
    "nl_cy_young": "NL Cy Young Award",
    "al_mariano_rivera": "AL Mariano Rivera Award",
    "nl_trevor_hoffman": "NL Trevor Hoffman Award",
    "al_rookie": "AL Rookie Pitcher of the Year",
    "nl_rookie": "NL Rookie Pitcher of the Year",
}


def initialize_session_state():
    """Initialize session state variables."""
    # Note: Session state is now managed per award category in display_award_tab()
    pass


def select_random_matchup(df: pd.DataFrame) -> tuple:
    """
    Select two random players for comparison.

    Args:
        df: DataFrame with player data

    Returns:
        Tuple of (player1_series, player2_series)
    """
    if len(df) < 2:
        return None, None

    # Retry logic to ensure we get two different players
    max_attempts = 10
    for attempt in range(max_attempts):
        # Sample 2 random players without replacement
        sample = df.sample(n=2, replace=False)
        player1, player2 = sample.iloc[0], sample.iloc[1]

        # Verify they're actually different players
        if int(player1["xMLBAMID"]) != int(player2["xMLBAMID"]):
            return player1, player2

    # If we failed after all retries, raise an error
    raise ValueError(f"Failed to select two different players after {max_attempts} attempts")


def display_player_card(player: pd.Series, column, button_key: str):
    """
    Display a player card with image, stats, and vote button.

    Args:
        player: Series containing player data
        column: Streamlit column to display in
        button_key: Unique key for the vote button
    """
    with column:
        # Vote button at top
        if st.button(f"Vote for {player['nameFirstLast']}", key=button_key, width="stretch", type="primary"):
            return True

        # Custom divider
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

        # Player image - centered and larger
        st.markdown(f'<div style="text-align: center;"><img src="{player["player_image_url"]}" width="280" style="border-radius: 16px; border: 2px solid rgba(255, 255, 255, 0.8); box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);" /></div>', unsafe_allow_html=True)

        # Player name and team on same line
        st.markdown(f'''
            <div class="player-card-header">
                <h3 style="margin: 0;">{player['nameFirstLast']}</h3>
                <div style="font-weight: 600; color: var(--text-secondary);">{player['currentTeamName']}</div>
            </div>
        ''', unsafe_allow_html=True)

        # Stats table with custom divider
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="stats-container">', unsafe_allow_html=True)

        # Team logo watermark behind stats
        st.markdown(f'<img src="{player["team_logo_url"]}" class="team-logo-watermark" />', unsafe_allow_html=True)

        stats_col1, stats_col2 = st.columns(2)

        with stats_col1:
            st.metric("IP", f"{player['IP']:.1f}")
            st.metric("ERA", f"{player['ERA']:.2f}")
            st.metric("FIP", f"{player['FIP']:.2f}")

        with stats_col2:
            st.metric("K-BB%", player["K-BB%"])
            st.metric("proStuff+", int(player["proStuff+"]))
            st.metric("fWAR", f"{player['fWAR']:.1f}")

        st.markdown('</div>', unsafe_allow_html=True)  # Close stats-container

        # Vote button at bottom
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        if st.button(f"Vote for {player['nameFirstLast']}", key=f"{button_key}_bottom", width="stretch", type="primary"):
            return True

    return False


def handle_vote(award_category: str, winner: pd.Series, loser: pd.Series):
    """
    Handle a vote submission and update ELO ratings.

    Args:
        award_category: Award category key
        winner: Series for winning player
        loser: Series for losing player
    """
    winner_id = int(winner["xMLBAMID"])
    winner_name = winner["nameFirstLast"]
    loser_id = int(loser["xMLBAMID"])
    loser_name = loser["nameFirstLast"]

    # Record matchup and get new ratings
    new_winner_rating, new_loser_rating = record_matchup(
        award_category,
        winner_id,
        winner_name,
        loser_id,
        loser_name
    )

    # Show success message
    st.success(f"Vote recorded! {winner_name} wins this matchup.")

    # Clear matchup to generate new one (using award-specific keys)
    matchup_key = f"current_matchup_{award_category}"
    vote_key = f"vote_submitted_{award_category}"
    st.session_state[matchup_key] = None
    st.session_state[vote_key] = True

    # Rerun to show new matchup
    st.rerun()


def display_award_tab(award_category: str, award_name: str):
    """
    Display content for a single award category tab.

    Args:
        award_category: Award category key
        award_name: Display name for the award
    """
    st.header(award_name)

    # Initialize award-specific session state
    matchup_key = f"current_matchup_{award_category}"
    vote_key = f"vote_submitted_{award_category}"

    if matchup_key not in st.session_state:
        st.session_state[matchup_key] = None
    if vote_key not in st.session_state:
        st.session_state[vote_key] = False

    # Load player data
    with st.spinner("Loading player data..."):
        try:
            df = get_pitcher_data(award_category)
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            return

    if df.empty:
        st.warning("No player data available for this category.")
        return

    # Generate or retrieve current matchup
    if st.session_state[matchup_key] is None or st.session_state[vote_key]:
        player1, player2 = select_random_matchup(df)
        if player1 is None or player2 is None:
            st.warning("Not enough players for a matchup.")
            return
        st.session_state[matchup_key] = (player1, player2)
        st.session_state[vote_key] = False

    player1, player2 = st.session_state[matchup_key]

    # Safety check: ensure players are different
    if int(player1["xMLBAMID"]) == int(player2["xMLBAMID"]):
        # Force regeneration if duplicate detected
        st.session_state[matchup_key] = None
        st.rerun()

    # Display matchup
    col1, vs_col, col2 = st.columns([5, 1, 5])

    # Display player cards
    vote_player1 = display_player_card(player1, col1, f"vote_p1_{award_category}")

    with vs_col:
        st.markdown("""
            <div class="vs-container">
                <div class="vs-text">VS</div>
            </div>
        """, unsafe_allow_html=True)

    vote_player2 = display_player_card(player2, col2, f"vote_p2_{award_category}")

    # Handle votes
    if vote_player1:
        handle_vote(award_category, player1, player2)
    elif vote_player2:
        handle_vote(award_category, player2, player1)

    # Show leaderboard
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    leaderboard = get_leaderboard(award_category)
    if not leaderboard.empty:
        # Format leaderboard
        leaderboard_display = leaderboard.copy()
        leaderboard_display["elo_rating"] = leaderboard_display["elo_rating"].round(0).astype(int)

        # Build custom HTML table
        table_html = '<div class="rankings-table-container"><table class="rankings-table">'
        table_html += '<thead><tr><th>Rank</th><th>Player</th><th>ELO Rating</th><th>Matches</th></tr></thead>'
        table_html += '<tbody>'

        for idx, row in enumerate(leaderboard_display.itertuples(), start=1):
            rank_class = "rank-1" if idx == 1 else "rank-2" if idx == 2 else "rank-3" if idx == 3 else ""
            table_html += f'<tr class="{rank_class}">'
            table_html += f'<td class="rank-cell"><span class="rank-badge">{idx}</span></td>'
            table_html += f'<td class="player-cell">{row.player_name}</td>'
            table_html += f'<td class="rating-cell">{row.elo_rating}</td>'
            table_html += f'<td class="matches-cell">{row.matches_played}</td>'
            table_html += '</tr>'

        table_html += '</tbody></table></div>'
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("No rankings yet. Start voting to build the leaderboard!")


def main():
    """Main application entry point."""
    initialize_session_state()

    # Title
    st.title("2025 Crowdsourced Pitcher Awards")
    st.markdown("Vote on head-to-head matchups to determine the best pitchers in each award category.")

    # Create tabs for each award plus external links
    tab_names = list(AWARD_NAMES.values()) + ["Pitch Profiler", "Patreon"]
    tabs = st.tabs(tab_names)

    # Display award tabs
    for tab, (award_key, award_name) in zip(tabs[:len(AWARD_NAMES)], AWARD_NAMES.items()):
        with tab:
            display_award_tab(award_key, award_name)

    # Pitch Profiler tab
    with tabs[-2]:
        st.markdown("### Visit Pitch Profiler")
        st.markdown("""
        Click below to visit Pitch Profiler for advanced pitching analytics and visualizations.
        """)
        st.markdown("""
            <div style="display: flex; justify-content: center; margin-top: 2rem;">
                <a href="https://www.MLBPitchProfiler.com" target="_blank" style="
                    background: linear-gradient(135deg, rgba(0, 122, 255, 0.2), rgba(255, 59, 48, 0.2));
                    backdrop-filter: blur(20px);
                    -webkit-backdrop-filter: blur(20px);
                    border: 1px solid rgba(0, 122, 255, 0.3);
                    border-radius: 16px;
                    color: #1D1D1F;
                    font-weight: 600;
                    font-size: 1.1rem;
                    padding: 1rem 2rem;
                    text-decoration: none;
                    box-shadow: 0 8px 24px rgba(0, 122, 255, 0.15);
                    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                    display: inline-block;
                ">Go to Pitch Profiler</a>
            </div>
        """, unsafe_allow_html=True)

    # Patreon tab
    with tabs[-1]:
        st.markdown("### Support on Patreon")
        st.markdown("""
        Support Pitch Profiler on Patreon to access exclusive content and features!
        """)
        st.markdown("""
            <div style="display: flex; justify-content: center; margin-top: 2rem;">
                <a href="https://www.patreon.com/mlbpitchprofiler/membership" target="_blank" style="
                    background: linear-gradient(135deg, rgba(0, 122, 255, 0.2), rgba(255, 59, 48, 0.2));
                    backdrop-filter: blur(20px);
                    -webkit-backdrop-filter: blur(20px);
                    border: 1px solid rgba(0, 122, 255, 0.3);
                    border-radius: 16px;
                    color: #1D1D1F;
                    font-weight: 600;
                    font-size: 1.1rem;
                    padding: 1rem 2rem;
                    text-decoration: none;
                    box-shadow: 0 8px 24px rgba(0, 122, 255, 0.15);
                    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                    display: inline-block;
                ">Join on Patreon</a>
            </div>
        """, unsafe_allow_html=True)

    # Footer with attribution
    st.markdown('''
        <div class="footer-container">
            <div class="footer-content">
                <div class="footer-section">
                    <strong>Data:</strong> FanGraphs, MLB and Pitch Profiler
                </div>
                <div class="footer-section">
                    <strong>Images:</strong> MLB
                </div>
            </div>
        </div>
    ''', unsafe_allow_html=True)


if __name__ == "__main__":
    main()