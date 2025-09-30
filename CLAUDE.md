# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Streamlit web application for crowdsourced MLB pitcher rankings using an ELO rating system. Users vote on head-to-head matchups between pitchers, and rankings are computed across multiple award categories (AL/NL Cy Young, Mariano Rivera/Trevor Hoffman reliever awards, and rookie awards).

## Running the Application

**Local development:**
```bash
uv run streamlit run app.py
```

The app will be available at `http://localhost:8501` (or 8502 if 8501 is occupied).

## Architecture

### Core Data Flow
1. **Data Fetching** (`data_fetcher.py`): Fetches from three APIs:
   - FanGraphs API: Pitching statistics (ERA, FIP, WAR, K-BB%, etc.)
   - proPitching+ API: Advanced metrics (proStuff+)
   - MLB Stats API: Player names, team info, headshots, team logos

2. **Data Processing** (`data_processor.py`): Merges all data sources into a single DataFrame with the `get_pitcher_data()` function. This is cached for 1 hour via `@st.cache_data(ttl=3600)`. Returns top 20 pitchers by fWAR per award category.

3. **ELO System** (`elo_system.py`):
   - Standard ELO algorithm (K=32, default rating=1500)
   - **Persists to Supabase PostgreSQL database** (not CSV files)
   - Single table `elo_ratings` with columns: `award_category`, `player_id`, `player_name`, `elo_rating`, `matches_played`
   - Uses upsert operations with conflict resolution on `(award_category, player_id)`
   - **Critical**: All numeric values must be converted to native Python types (`int()`, `float()`) before sending to Supabase to avoid JSON serialization errors with numpy types

4. **Streamlit App** (`app.py`):
   - Tab-based UI with one tab per award category
   - **Session state is per-award-category** (not global) - each tab maintains its own matchup
   - Displays two random pitchers with vote buttons, stats, images
   - Shows live leaderboard below each matchup
   - Footer with data attribution (FanGraphs, MLB, Pitch Profiler)

### Award Categories
The system supports 6 award categories defined in `AWARD_NAMES`:
- `al_cy_young`: AL Cy Young Award
- `nl_cy_young`: NL Cy Young Award
- `al_mariano_rivera`: AL Mariano Rivera Award (relievers)
- `nl_trevor_hoffman`: NL Trevor Hoffman Award (relievers)
- `al_rookie`: AL Rookie Pitcher of the Year
- `nl_rookie`: NL Rookie Pitcher of the Year

### Design System

**Liquid Glass Aesthetic:**
The entire UI uses a "liquid glass" design with:
- Frosted glass backgrounds: `backdrop-filter: blur(20px)`
- CSS variables for colors in `style.css` (`:root`)
- Gradient accents (blue to red)
- Animated background gradient
- No borders on tables/components (use `border: none !important;`)
- Custom HTML tables for rankings (not Streamlit's default dataframe)

**When adding new UI components:**
- Follow the liquid glass pattern from existing components
- Use `var(--glass-bg)` for backgrounds
- Add backdrop blur and subtle shadows
- No visible borders or outlines
- Include hover animations with scale/shadow effects

## Database Configuration

### Supabase Setup
The app uses Supabase (PostgreSQL) for persistent storage. Configuration is stored in `.streamlit/secrets.toml`:

```toml
[supabase]
url = "https://xxx.supabase.co"
key = "your-anon-key"
```

**Database schema:**
```sql
CREATE TABLE elo_ratings (
  id BIGSERIAL PRIMARY KEY,
  award_category TEXT NOT NULL,
  player_id BIGINT NOT NULL,
  player_name TEXT NOT NULL,
  elo_rating FLOAT NOT NULL DEFAULT 1500,
  matches_played INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(award_category, player_id)
);
```

**Important**: The `.streamlit/secrets.toml` file is gitignored. For deployment on Streamlit Cloud, add these secrets through the Streamlit Cloud dashboard.

## Key Implementation Details

### Preventing Duplicate Players in Matchups
The `select_random_matchup()` function in `app.py` has retry logic (10 attempts) to ensure two different players are selected. It verifies by comparing `xMLBAMID` values.

### Session State Management
Each award category uses its own session state keys:
- `current_matchup_{award_category}`: Stores (player1, player2) tuple
- `vote_submitted_{award_category}`: Boolean flag to trigger new matchup generation

### Data Caching
- `fetch_fangraphs_data()` and `get_pitcher_data()` use `@st.cache_data(ttl=3600)` to cache for 1 hour
- `get_supabase_client()` uses `@st.cache_resource` to maintain a single database connection

### ELO Rating Persistence
- Each vote immediately writes to Supabase via `record_matchup()`
- Uses upsert operations to handle both new players and updates
- **All ratings are shared globally across all users** - this is a collaborative ranking system

### Type Conversion for Database Operations
**Critical**: When sending data to Supabase, convert pandas/numpy types to native Python types:
```python
data = {
    "player_id": int(player_id),      # numpy.int64 → int
    "elo_rating": float(new_rating),   # numpy.float64 → float
    "matches_played": int(matches)     # numpy.int64 → int
}
```
Failure to do this will cause `Object of type int64 is not JSON serializable` errors.

## Common Tasks

### Clearing all ELO ratings:
Delete all rows from the Supabase table via SQL editor:
```sql
DELETE FROM elo_ratings;
```

### Screenshot testing:
Use Playwright for UI testing:
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("http://localhost:8502")
    page.screenshot(path="screenshot.png")
    browser.close()
```

## Deployment to Streamlit Cloud

1. **Push to GitHub** (ensure `.streamlit/secrets.toml` is in `.gitignore`)
2. **Create app on Streamlit Cloud** at share.streamlit.io
3. **Add secrets** in Streamlit Cloud dashboard under app settings
4. **Set main file** to `app.py`

The app will automatically handle concurrent users with proper database transactions.

## Standard Workflow

1. First think through the problem, read the codebase for relevant files, and write a plan using TodoWrite tool
2. The plan should have a list of todo items that you can check off as you complete them
3. Before you begin working, check in with me and I will verify the plan
4. Then, begin working on the todo items, marking them as complete as you go
5. Please every step of the way just give me a high level explanation of what changes you made
6. Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity
7. Finally, add a review section to the TodoWrite with a summary of the changes you made and any other relevant information

## The Ten Universal Commandments

1. Thou shalt ALWAYS use MCP tools before coding
2. Thou shalt NEVER assume; always question
3. Thou shalt write code that's clear and obvious
4. Thou shalt be BRUTALLY HONEST in assessments
5. Thou shalt PRESERVE CONTEXT, not delete it
6. Thou shalt make atomic, descriptive commits
7. Thou shalt document the WHY, not just the WHAT
8. Thou shalt test before declaring done
9. Thou shalt handle errors explicitly
10. Thou shalt treat user data as sacred

## Final Reminders

- Codebase > Documentation > Training data (in order of truth)
- Research current docs using context7, don't trust outdated knowledge
- Ask questions early and often
- Use slash commands for consistent workflows
- Derive documentation on-demand
- Extended thinking for complex problems
- Visual inputs for UI/UX debugging
- Test locally before pushing
- Think simple: clear, obvious, no bullshit

---

**Remember: Write code as if the person maintaining it is a junior developer. Make it that clear.**
