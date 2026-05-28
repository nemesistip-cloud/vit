VIT_OS — Sports Coverage Expansion
GitHub Copilot Instruction File
Paste this file into your repo root as COPILOT_INSTRUCTIONS.md or open it alongside your codebase.
Copilot will use this as context to complete and upgrade the application.

PROJECT OVERVIEW
App: VIT_OS — AI-powered sports match prediction platform
Stack: Python (scikit-learn, XGBoost, joblib), Flask or FastAPI, Replit deployment
Existing pipeline: CSV training data → train_model.py → .pkl model → /predict API endpoint
Existing sports: Football (EPL, La Liga, Bundesliga, Serie A, Ligue 1, Champions League)
Goal: Expand to 5 additional sports with full data, model, API, and UI support

DIRECTORY STRUCTURE TO CREATE
Code
SPORT 1 — BASKETBALL (NBA / EUROLEAGUE)
CSV Schema
Files: data/sports/basketball/nba_matches.csv, euroleague_matches.csv
Code
result column values: H (home win), A (away win)
Data Sources
Basketball-Reference.com — box scores 2015–2024
NBA Stats API — pace and efficiency metrics
Kaggle NBA datasets — supplementary historical data
Odds Portal — B365 pre-match odds
Feature Engineering (write in train_model.py)
ELO rating per team, updated after each game (k=20, HFA=100)
Rolling 5-game home_last5_wins and away_last5_wins
home_rest_days / away_rest_days — days since previous game
Pace-adjusted OffRtg and DefRtg per 100 possessions
Model
Algorithm: RandomForest + XGBoost ensemble (VotingClassifier)
Target: result (H or A — no draws in basketball)
Cross-validation: 5-fold StratifiedKFold
Target AUC: > 0.78
Output: models/basketball_model.pkl
API Endpoint
Code
TODO Checklist
[ ] Scrape Basketball-Reference box scores (2015–2024), save to nba_matches.csv
[ ] Compute OffRtg / DefRtg per game (points per 100 possessions)
[ ] Add B365 odds columns via Odds Portal scraper or manual merge
[ ] Generate separate euroleague_matches.csv with same schema
[ ] Write feature engineering pipeline in scikit-learn Pipeline object
[ ] Train and serialize to models/basketball_model.pkl via joblib
[ ] Register /predict/basketball route in api/routes/basketball.py
[ ] Validate on 2023–24 holdout — confirm AUC > 0.78
SPORT 2 — TENNIS (ATP / WTA)
CSV Schema
Files: data/sports/tennis/atp_matches.csv, wta_matches.csv
Code
winner column values: 1 (player1 wins), 2 (player2 wins)
Data Sources
Jeff Sackmann's tennis_atp GitHub repo (github.com/JeffSackmann/tennis_atp) — free, clean CSVs per year
Jeff Sackmann's tennis_wta GitHub repo — same structure
Ultimate Tennis Statistics — serve/return stats
Odds Portal — B365 match odds
Feature Engineering
surface_winrate: rolling win rate per player per surface (hard, clay, grass)
fatigue_days: days since player's last match
h2h_win_ratio: historical head-to-head wins per player pair
rank_delta: abs(p1_rank - p2_rank) — useful signal
serve_dominance: (1stWon / svpt) ratio per player
Model
Algorithm: Gradient Boosting Classifier (XGBoost preferred)
Target: winner (1 or 2)
Train SEPARATE models for ATP and WTA
Cross-validation: 5-fold StratifiedKFold
Target AUC: > 0.74
Output: models/tennis_model.pkl (ATP), models/tennis_wta_model.pkl (WTA)
API Endpoint
Code
TODO Checklist
[ ] Clone tennis_atp repo, merge year CSVs into single atp_matches.csv (2000–2024)
[ ] Clone tennis_wta repo, merge year CSVs into wta_matches.csv (2010–2024)
[ ] Standardize column names to schema above
[ ] Engineer surface_winrate (rolling per player per surface)
[ ] Compute fatigue_days (date diff from player's previous match)
[ ] Compute h2h win counts per player pair across full history
[ ] Train ATP model → models/tennis_model.pkl
[ ] Train WTA model → models/tennis_wta_model.pkl
[ ] Register /predict/tennis route with tour param to select correct model
[ ] Add tennis to /sports status endpoint
SPORT 3 — AMERICAN FOOTBALL (NFL)
CSV Schema
File: data/sports/american_football/nfl_matches.csv
Code
result values: H (home win), A (away win)
surface values: turf, grass
Data Sources
nflfastR: github.com/nflverse/nflfastR — play-by-play exports, aggregate to game level
Pro Football Reference — game logs, team stats
FootballOutsiders.com — DVOA efficiency ratings (OffDVOA, DefDVOA)
DraftKings / Odds Portal — B365 moneyline and spread odds
Feature Engineering
ELO rating per team using 538-style formula: k=20, HFA=55 points
DVOA columns: normalize to z-score across season
qb_rating_delta: home QB passer rating minus away QB passer rating
spread_implied_prob: convert b365_spread to win probability
weather_flag: binary — 1 if outdoor stadium AND wind > 20mph (via weather API)
Model
Algorithm: XGBoost Classifier
Target: result (H or A)
Also train a SEPARATE spread prediction model (regression) on spread
Cross-validation: 5-fold StratifiedKFold
Target AUC: > 0.68
Output: models/nfl_model.pkl, models/nfl_spread_model.pkl
API Endpoint
Code
TODO Checklist
[ ] Download nflfastR game-level aggregates from GitHub (2000–2024)
[ ] Add DVOA columns (OffDVOA, DefDVOA) via FootballOutsiders CSVs
[ ] Engineer ELO ratings from game history (iterate chronologically)
[ ] Add home_qb / away_qb starting QB passer rating for each game
[ ] Include Vegas spread as a training feature
[ ] Add weather_flag for outdoor stadiums via OpenWeatherMap API
[ ] Train nfl_model.pkl (win/loss) and nfl_spread_model.pkl (spread regression)
[ ] Register /predict/nfl route in api/routes/american_football.py
[ ] Validate spread model MAE < 4.5 points on holdout
[ ] Add NFL to /sports status endpoint
SPORT 4 — BASEBALL (MLB)
CSV Schema
File: data/sports/baseball/mlb_matches.csv
Code
result values: H (home win), A (away win)
game_type values: regular, playoff
park_factor is normalized to 100 (>100 = hitter-friendly, <100 = pitcher-friendly)
moneyline in American odds format — convert to decimal in preprocessing
Data Sources
Retrosheet.org — free game logs 1990–2024 (game-level CSV per year)
Baseball Savant (Statcast) — pitcher and batter advanced metrics
FanGraphs — FIP, WHIP, K/9, BB/9 per starting pitcher
Odds Portal — B365 moneyline odds
Feature Engineering
bullpen_era_l7: 7-day rolling ERA for each team's bullpen
starter_fip_delta: home_fip minus away_fip (lower = better pitcher)
park_factor: per-stadium run environment (source from Baseball Reference)
elo per team updated each game (k=15 for baseball — high variance sport)
Convert American moneyline to implied probability and decimal odds
Model
Algorithm: XGBoost Classifier
Target: result (H or A)
Also train a SEPARATE run total model (binary: over/under 8.5 runs) on total_runs
Cross-validation: 5-fold StratifiedKFold
Target AUC: > 0.62 (baseball is high variance — expect lower AUC)
Output: models/mlb_model.pkl, models/mlb_runline_model.pkl
API Endpoint
Code
TODO Checklist
[ ] Download Retrosheet game logs (1990–2024), merge into mlb_matches.csv
[ ] Join FanGraphs pitcher stats (FIP, WHIP, K/9) per home_starter and away_starter
[ ] Add park_factor per stadium from Baseball Reference park factors table
[ ] Compute bullpen_era_l7 rolling per team per date
[ ] Convert American moneyline to decimal odds in preprocessing step
[ ] Engineer ELO per team (k=15)
[ ] Train mlb_model.pkl (win/loss) and mlb_runline_model.pkl (over/under)
[ ] Register /predict/baseball route in api/routes/baseball.py
[ ] Validate: require home_starter and away_starter in request — return 422 if missing
[ ] Add MLB to /sports status endpoint
SPORT 5 — RUGBY (SIX NATIONS / PREMIERSHIP / URC / RUGBY CHAMPIONSHIP)
CSV Schema
File: data/sports/rugby/rugby_matches.csv
Code
result values: H (home win), D (draw), A (away win)
competition values: six_nations, premiership, urc, rugby_championship, champions_cup
is_test_match values: 1 (international), 0 (club)
is_neutral values: 1 (neutral venue), 0 (home ground)
Data Sources
ESPN Scrum — match results and stats for Six Nations, Premiership, URC, Rugby Championship
World Rugby official rankings — updated weekly, use as feature per match date
Rugby Reference — historical results
Odds Portal — B365 home/draw/away odds
Feature Engineering
ELO per team with HFA coefficient of 65 points (rugby has strong home advantage)
try_scoring_rate: rolling 5-game tries scored per team
tackle_success_rate: tackles / (tackles + missed_tackles)
lineout_dominance: lineouts_won / (lineouts_won + lineouts_lost)
For international matches: use world_ranking_delta as primary feature over club ELO
Model
Algorithm: RandomForest Classifier (handles draw class better)
Target: result (H, D, A — 3-class problem)
Also train a SEPARATE points margin regression model
Cross-validation: 5-fold StratifiedKFold
Target AUC (macro): > 0.70
Output: models/rugby_model.pkl
API Endpoint
Code
TODO Checklist
[ ] Scrape ESPN Scrum for match results + stats (Six Nations, Premiership, URC, Rugby Championship)
[ ] Pull World Rugby rankings per week from World Rugby API or archived CSVs
[ ] Engineer ELO ratings per team with HFA = 65 points
[ ] Compute try_scoring_rate (rolling 5-game) per team
[ ] Add neutral venue flag — used for international tournaments at neutral sites
[ ] Train 3-class RandomForest → models/rugby_model.pkl
[ ] Train secondary points margin regression model
[ ] Register /predict/rugby route in api/routes/rugby.py
[ ] Validate: competition-specific model tuning (club vs international differ significantly)
[ ] Add rugby to /sports status endpoint
SHARED SCRIPTS TO BUILD
1. train_model.py — Unified Training Script
Code
2. data_audit.py — Schema Validator
Code
3. retrain_cron.py — Weekly Retrain Script
Code
API ROUTES TO ADD
Existing app.py — Add these alongside current football routes
Python
UI UPGRADES TO MAKE
Sport Selector
Add dropdown at top of prediction UI — default to Football (existing)
On sport change: swap input fields dynamically to match that sport's required inputs
Show expected accuracy range per sport next to selector
Prediction Output Panel
Confidence meter: LOW (< 60% top prob) / MEDIUM (60–72%) / HIGH (> 72%)
Top 3 feature importance bars (use model's feature_importances_ from sklearn)
Animated probability distribution bar (home / draw / away)
Predictions History Tab
Store last 50 predictions in localStorage or lightweight DB
Columns: date, sport, home_team, away_team, predicted, actual (editable), correct?
Show rolling accuracy per sport from history
Accuracy Dashboard
Per sport: model AUC (from training_log.csv), recent 30-day prediction accuracy
Simple bar chart per sport
Last trained date + retrain button (calls retrain_cron.py for that sport)
Add data_manifest.json — Create This File
Json
TESTS TO WRITE — tests/test_endpoints.py
Code
ACCURACY TARGETS SUMMARY
Sport
Model
Target AUC
Training Rows
Key Signal
Basketball
RF + XGBoost ensemble
0.78
12,000+
OffRtg / DefRtg
Tennis (ATP)
XGBoost
0.74
60,000+
Surface win rate
Tennis (WTA)
XGBoost
0.72
40,000+
Rank delta
NFL
XGBoost
0.68
8,000+
ELO + DVOA
MLB
XGBoost
0.62
50,000+
Starter FIP
Rugby
RandomForest
0.70
6,000+
ELO + possession %
IMPLEMENTATION ORDER (recommended)
Create directory structure and data_manifest.json
Build data_audit.py and validate existing football CSVs first
Add tennis (most data available for free via Sackmann repo) — easiest win
Add basketball (NBA data well-documented, high AUC potential)
Add rugby (moderate data, clean ESPN source)
Add NFL (requires DVOA data join — extra step)
Add baseball (most complex feature engineering — do last)
Build unified train_model.py with --sport flag
Add all /predict routes to api/app.py
Write pytest tests for all endpoints
Build UI upgrades: sport selector, history tab, accuracy dashboard
Set up retrain_cron.py and test CRON on Replit
Write README_SPORTS.md
VIT_OS — built for accuracy. Every column counts.
