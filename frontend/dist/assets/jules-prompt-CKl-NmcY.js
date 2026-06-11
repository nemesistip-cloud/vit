import{r as l,j as e}from"./vendor-query-DVSq1XXW.js";const c=[{id:"basketball",emoji:"🏀",name:"Basketball (NBA/EuroLeague)",color:"#FF6B35",accent:"#FF9A3C",csvColumns:["home_team","away_team","league","season","date","home_score","away_score","result","home_fg_pct","away_fg_pct","home_3p_pct","away_3p_pct","home_reb","away_reb","home_ast","away_ast","home_to","away_to","home_pace","away_pace","home_off_rating","away_off_rating","home_def_rating","away_def_rating","b365_home","b365_draw","b365_away","home_rest_days","away_rest_days","home_last5_wins","away_last5_wins","is_playoff"],dataSources:["Basketball-Reference.com","NBA Stats API","Kaggle NBA datasets","Odds Portal (B365)"],modelFeatures:["ELO ratings","pace-adjusted stats","rest days","H2H record","home court factor"],trainingRows:"12,000+ rows (2015–2024)",accuracy:"~72–78%",todo:["Scrape Basketball-Reference for play-by-play box scores (2015–2024)","Engineer pace/efficiency metrics (OffRtg, DefRtg) per game","Add B365 pre-match odds columns","Generate separate CSVs per league: nba_matches.csv, euroleague_matches.csv","Train RandomForest + XGBoost ensemble; export basketball_model.pkl","Add fixtures endpoint: /predict/basketball with JSON payload","Validate with 2023–24 holdout set — target AUC > 0.78"]},{id:"tennis",emoji:"🎾",name:"Tennis (ATP/WTA)",color:"#4CAF50",accent:"#81C784",csvColumns:["player1","player2","tournament","surface","round","year","date","winner","p1_rank","p2_rank","p1_rank_points","p2_rank_points","p1_age","p2_age","p1_ht","p2_ht","p1_hand","p2_hand","p1_ace","p2_ace","p1_df","p2_df","p1_svpt","p2_svpt","p1_1stIn","p2_1stIn","p1_1stWon","p2_1stWon","p1_bpFaced","p2_bpFaced","p1_bpSaved","p2_bpSaved","p1_SvGms","p2_SvGms","b365_p1","b365_p2","p1_h2h_wins","p2_h2h_wins","p1_surface_winrate","p2_surface_winrate","p1_fatigue_days","p2_fatigue_days"],dataSources:["Jeff Sackmann's tennis_atp/tennis_wta GitHub","Ultimate Tennis Statistics","Odds Portal"],modelFeatures:["surface-specific win rate","H2H","ranking delta","fatigue index","serve stats"],trainingRows:"60,000+ rows (ATP 2000–2024 / WTA 2010–2024)",accuracy:"~68–74%",todo:["Clone Jeff Sackmann's tennis_atp repo — already has clean CSVs per year","Merge ATP + WTA CSVs; standardize column schema above","Engineer surface_winrate rolling per player per surface","Add fatigue_days (days since last match)","Compute H2H win ratio per player pair","Train gradient boosting classifier; export tennis_model.pkl","Fixtures input: /predict/tennis — accepts player1, player2, surface, tournament_level","Separate models for ATP and WTA for accuracy boost"]},{id:"american_football",emoji:"🏈",name:"American Football (NFL)",color:"#1565C0",accent:"#42A5F5",csvColumns:["home_team","away_team","season","week","date","stadium","surface","home_score","away_score","total_score","result","spread","over_under","home_yards_gained","away_yards_gained","home_pass_yards","away_pass_yards","home_rush_yards","away_rush_yards","home_turnovers","away_turnovers","home_penalties","away_penalties","home_3rd_pct","away_3rd_pct","home_red_zone_pct","away_red_zone_pct","b365_home","b365_away","b365_spread","b365_ou","home_elo","away_elo","home_off_dvoa","away_off_dvoa","home_def_dvoa","away_def_dvoa","home_qb","away_qb","is_playoff"],dataSources:["nflfastR (R package / CSV exports)","Pro Football Reference","The Football Database","DraftKings/B365 odds"],modelFeatures:["ELO","DVOA efficiency","QB rating","spread line","weather","turf type"],trainingRows:"8,000+ rows (2000–2024)",accuracy:"~63–70% (ATS: ~55%)",todo:["Pull nflfastR play-by-play exports from GitHub (2000–2024) and aggregate to game level","Add DVOA columns (OffDVOA, DefDVOA) from FootballOutsiders data","Engineer ELO ratings using 538-style formula (k=20, HFA=55)","Add QB starter column — affects prediction significantly","Include Vegas spread as feature; train spread model separately","Export nfl_model.pkl and nfl_spread_model.pkl","Fixtures: /predict/nfl — output: win probability + spread prediction","Add weather API call for outdoor games (wind > 20mph flags)"]},{id:"baseball",emoji:"⚾",name:"Baseball (MLB)",color:"#D32F2F",accent:"#EF5350",csvColumns:["home_team","away_team","season","date","stadium","game_type","home_score","away_score","result","total_runs","home_starter","away_starter","home_era","away_era","home_whip","away_whip","home_k9","away_k9","home_bb9","away_bb9","home_fip","away_fip","home_babip","away_babip","home_woba","away_woba","home_ops","away_ops","home_iso","away_iso","home_team_era_l10","away_team_era_l10","home_bullpen_era","away_bullpen_era","b365_home","b365_away","home_moneyline","away_moneyline","run_line","home_elo","away_elo","park_factor","is_day_game","is_playoff"],dataSources:["Retrosheet.org","Baseball Savant (Statcast)","Baseball Reference","FanGraphs","Odds Portal"],modelFeatures:["starter FIP/ERA","bullpen ERA","park factor","platoon splits","weather"],trainingRows:"50,000+ rows (2000–2024)",accuracy:"~60–66% (high variance sport)",todo:["Download Retrosheet game logs (free, 1990–2024) as base CSV","Enrich with FanGraphs pitcher FIP, WHIP, K/9 for each starter","Add park_factor per stadium (normalized to 100)","Engineer bullpen_era_l7 (7-day rolling bullpen ERA)","Moneyline odds from Odds Portal — convert American to decimal","Train XGBoost classifier per home/away win + run total model","Export mlb_model.pkl and mlb_runline_model.pkl","Fixtures: /predict/baseball — requires home_starter, away_starter params"]},{id:"rugby",emoji:"🏉",name:"Rugby (Six Nations / Premiership / URC)",color:"#6A1B9A",accent:"#AB47BC",csvColumns:["home_team","away_team","competition","season","date","stage","venue","home_score","away_score","home_tries","away_tries","home_conversions","away_conversions","home_penalties_scored","away_penalties_scored","home_possession_pct","away_possession_pct","home_territory_pct","away_territory_pct","home_tackles","away_tackles","home_missed_tackles","away_missed_tackles","home_lineouts_won","away_lineouts_won","home_scrums_won","away_scrums_won","home_turnovers_won","away_turnovers_won","home_meters_made","away_meters_made","home_elo","away_elo","home_world_ranking","away_world_ranking","b365_home","b365_draw","b365_away","home_last5_wins","away_last5_wins","is_neutral","is_test_match"],dataSources:["ESPN Scrum","Rugby Reference","World Rugby Stats","Odds Portal","ESPN API"],modelFeatures:["ELO","world rankings","home advantage (strong in rugby)","possession/territory","form"],trainingRows:"6,000+ rows (2010–2024)",accuracy:"~68–75%",todo:["Scrape ESPN Scrum for match results + stats (Six Nations, Premiership, URC, Rugby Championship)","Add World Rugby official rankings as a feature column","Engineer ELO per team with high HFA coefficient (~65 pts)","Add try_scoring_rate per team (tries/match rolling 5-game window)","Include neutral venue flag — test matches often played at neutral sites","Train RandomForest classifier; export rugby_model.pkl","Fixtures: /predict/rugby — competition type matters (club vs. international)","Add separate model for points spread prediction"]}],h=[{phase:"Phase 1 — Data Infrastructure",icon:"🗄️",color:"#FF6B35",tasks:["Create /data/sports/ directory with one subfolder per sport","Generate train CSV + fixtures CSV per sport using the column schemas above","Validate CSVs: no nulls in key columns, correct dtypes, date format YYYY-MM-DD","Add a data_manifest.json listing each CSV path, row count, date range, and feature count","Write a data_audit.py script that auto-checks schema compliance across all CSVs"]},{phase:"Phase 2 — Model Training Pipeline",icon:"🤖",color:"#4CAF50",tasks:["Create train_model.py with a --sport flag: python train_model.py --sport basketball","Standardize feature engineering pipeline per sport using scikit-learn Pipeline objects","Add cross-validation (5-fold StratifiedKFold) and print AUC, F1, accuracy per fold","Serialize each model to /models/{sport}_model.pkl using joblib","Log training results to training_log.csv (date, sport, AUC, F1, n_rows)"]},{phase:"Phase 3 — Prediction API (Replit)",icon:"⚡",color:"#1565C0",tasks:["Add /predict/{sport} route for each new sport in Flask/FastAPI app","Each endpoint accepts JSON: { home_team, away_team, ...sport-specific features }","Load .pkl models at startup — cache in memory, don't reload per request","Return: { home_win_prob, draw_prob, away_win_prob, confidence, top_features }","Add /sports endpoint listing all active sports with model version and last trained date"]},{phase:"Phase 4 — VIT_OS UI Integration",icon:"🖥️",color:"#D32F2F",tasks:["Add sport selector dropdown to the prediction UI (football already default)","Render sport-specific input fields dynamically based on selected sport","Display confidence meter and top-3 feature importance per prediction","Add a Predictions History tab — stores last 50 predictions with outcome tracking","Add accuracy dashboard per sport (model AUC, recent prediction accuracy)"]},{phase:"Phase 5 — Quality & Monitoring",icon:"📊",color:"#6A1B9A",tasks:["Set up a weekly retrain CRON job that pulls new match results and retrains all models","Add model drift detection: alert if rolling 2-week accuracy drops > 5% vs baseline","Write pytest unit tests for each prediction endpoint (mock fixture inputs)","Add a /health endpoint that reports model load status for all 5 new sports","Document all sports, their schemas, and model metrics in a README_SPORTS.md"]}];function f(){const[n,d]=l.useState(!1),[r,_]=l.useState(null),[s,m]=l.useState(null),u=()=>`## VIT_OS — Sports Coverage Expansion (5 New Sports)

You are working on VIT_OS, an AI-powered sports prediction platform. The existing system predicts football (soccer) matches using trained ML models (.pkl files) with a CSV → train → predict pipeline deployed on Replit.

Your task is to **expand VIT_OS to cover 5 additional sports** with full ecosystem support. Each sport requires: a CSV training dataset, feature engineering, a trained model, and a prediction API endpoint.

---

### 🏀 SPORT 1: Basketball (NBA / EuroLeague)
**CSV file:** \`data/sports/basketball/nba_matches.csv\` + \`euroleague_matches.csv\`
**Columns:** home_team, away_team, league, season, date, home_score, away_score, result, home_fg_pct, away_fg_pct, home_3p_pct, away_3p_pct, home_reb, away_reb, home_ast, away_ast, home_to, away_to, home_pace, away_pace, home_off_rating, away_off_rating, home_def_rating, away_def_rating, b365_home, b365_draw, b365_away, home_rest_days, away_rest_days, home_last5_wins, away_last5_wins, is_playoff
**Data Sources:** Basketball-Reference.com, NBA Stats API, Kaggle NBA datasets, Odds Portal (B365)
**Target Rows:** 12,000+ (2015–2024)
**Model:** RandomForest + XGBoost ensemble → \`models/basketball_model.pkl\`
**Endpoint:** POST /predict/basketball
**TODO:**
1. Scrape Basketball-Reference for play-by-play box scores (2015–2024)
2. Engineer pace/efficiency metrics (OffRtg, DefRtg) per game
3. Add B365 pre-match odds columns
4. Generate separate CSVs per league: nba_matches.csv, euroleague_matches.csv
5. Train RandomForest + XGBoost ensemble; export basketball_model.pkl
6. Add fixtures endpoint: /predict/basketball with JSON payload
7. Validate with 2023–24 holdout set — target AUC > 0.78

---

### 🎾 SPORT 2: Tennis (ATP / WTA)
**CSV file:** \`data/sports/tennis/atp_matches.csv\` + \`wta_matches.csv\`
**Columns:** player1, player2, tournament, surface, round, year, date, winner, p1_rank, p2_rank, p1_rank_points, p2_rank_points, p1_age, p2_age, p1_ht, p2_ht, p1_hand, p2_hand, p1_ace, p2_ace, p1_df, p2_df, p1_svpt, p2_svpt, p1_1stIn, p2_1stIn, p1_1stWon, p2_1stWon, p1_bpFaced, p2_bpFaced, p1_bpSaved, p2_bpSaved, p1_SvGms, p2_SvGms, b365_p1, b365_p2, p1_h2h_wins, p2_h2h_wins, p1_surface_winrate, p2_surface_winrate, p1_fatigue_days, p2_fatigue_days
**Data Sources:** Jeff Sackmann's tennis_atp/tennis_wta GitHub (free), Ultimate Tennis Statistics, Odds Portal
**Target Rows:** 60,000+ rows (ATP 2000–2024 / WTA 2010–2024)
**Model:** Gradient Boosting → \`models/tennis_model.pkl\` (separate ATP + WTA models)
**Endpoint:** POST /predict/tennis
**TODO:**
1. Clone Jeff Sackmann's tennis_atp repo — already has clean CSVs per year
2. Merge ATP + WTA CSVs; standardize column schema above
3. Engineer surface_winrate rolling per player per surface
4. Add fatigue_days (days since last match)
5. Compute H2H win ratio per player pair
6. Train gradient boosting classifier; export tennis_model.pkl
7. Fixtures input: /predict/tennis — accepts player1, player2, surface, tournament_level
8. Separate models for ATP and WTA for accuracy boost

---

### 🏈 SPORT 3: American Football (NFL)
**CSV file:** \`data/sports/american_football/nfl_matches.csv\`
**Columns:** home_team, away_team, season, week, date, stadium, surface, home_score, away_score, total_score, result, spread, over_under, home_yards_gained, away_yards_gained, home_pass_yards, away_pass_yards, home_rush_yards, away_rush_yards, home_turnovers, away_turnovers, home_penalties, away_penalties, home_3rd_pct, away_3rd_pct, home_red_zone_pct, away_red_zone_pct, b365_home, b365_away, b365_spread, b365_ou, home_elo, away_elo, home_off_dvoa, away_off_dvoa, home_def_dvoa, away_def_dvoa, home_qb, away_qb, is_playoff
**Data Sources:** nflfastR (R package CSV exports on GitHub), Pro Football Reference, DraftKings/B365 odds
**Target Rows:** 8,000+ rows (2000–2024)
**Model:** XGBoost → \`models/nfl_model.pkl\` + \`models/nfl_spread_model.pkl\`
**Endpoint:** POST /predict/nfl
**TODO:**
1. Pull nflfastR play-by-play exports from GitHub (2000–2024) and aggregate to game level
2. Add DVOA columns (OffDVOA, DefDVOA) from FootballOutsiders data
3. Engineer ELO ratings using 538-style formula (k=20, HFA=55)
4. Add QB starter column — affects prediction significantly
5. Include Vegas spread as feature; train spread model separately
6. Export nfl_model.pkl and nfl_spread_model.pkl
7. Fixtures: /predict/nfl — output: win probability + spread prediction
8. Add weather API call for outdoor games (wind > 20mph flags)

---

### ⚾ SPORT 4: Baseball (MLB)
**CSV file:** \`data/sports/baseball/mlb_matches.csv\`
**Columns:** home_team, away_team, season, date, stadium, game_type, home_score, away_score, result, total_runs, home_starter, away_starter, home_era, away_era, home_whip, away_whip, home_k9, away_k9, home_bb9, away_bb9, home_fip, away_fip, home_babip, away_babip, home_woba, away_woba, home_ops, away_ops, home_iso, away_iso, home_team_era_l10, away_team_era_l10, home_bullpen_era, away_bullpen_era, b365_home, b365_away, home_moneyline, away_moneyline, run_line, home_elo, away_elo, park_factor, is_day_game, is_playoff
**Data Sources:** Retrosheet.org (free game logs), Baseball Savant (Statcast), FanGraphs, Odds Portal
**Target Rows:** 50,000+ rows (2000–2024)
**Model:** XGBoost → \`models/mlb_model.pkl\` + \`models/mlb_runline_model.pkl\`
**Endpoint:** POST /predict/baseball
**TODO:**
1. Download Retrosheet game logs (free, 1990–2024) as base CSV
2. Enrich with FanGraphs pitcher FIP, WHIP, K/9 for each starter
3. Add park_factor per stadium (normalized to 100)
4. Engineer bullpen_era_l7 (7-day rolling bullpen ERA)
5. Moneyline odds from Odds Portal — convert American to decimal
6. Train XGBoost classifier per home/away win + run total model
7. Export mlb_model.pkl and mlb_runline_model.pkl
8. Fixtures: /predict/baseball — requires home_starter, away_starter params

---

### 🏉 SPORT 5: Rugby (Six Nations / Premiership / URC)
**CSV file:** \`data/sports/rugby/rugby_matches.csv\`
**Columns:** home_team, away_team, competition, season, date, stage, venue, home_score, away_score, home_tries, away_tries, home_conversions, away_conversions, home_penalties_scored, away_penalties_scored, home_possession_pct, away_possession_pct, home_territory_pct, away_territory_pct, home_tackles, away_tackles, home_missed_tackles, away_missed_tackles, home_lineouts_won, away_lineouts_won, home_scrums_won, away_scrums_won, home_turnovers_won, away_turnovers_won, home_meters_made, away_meters_made, home_elo, away_elo, home_world_ranking, away_world_ranking, b365_home, b365_draw, b365_away, home_last5_wins, away_last5_wins, is_neutral, is_test_match
**Data Sources:** ESPN Scrum, Rugby Reference, World Rugby official rankings, Odds Portal
**Target Rows:** 6,000+ rows (2010–2024)
**Model:** RandomForest → \`models/rugby_model.pkl\`
**Endpoint:** POST /predict/rugby
**TODO:**
1. Scrape ESPN Scrum for match results + stats (Six Nations, Premiership, URC, Rugby Championship)
2. Add World Rugby official rankings as a feature column
3. Engineer ELO per team with high HFA coefficient (~65 pts)
4. Add try_scoring_rate per team (tries/match rolling 5-game window)
5. Include neutral venue flag — test matches often played at neutral sites
6. Train RandomForest classifier; export rugby_model.pkl
7. Fixtures: /predict/rugby — competition type matters (club vs. international)
8. Add separate model for points spread prediction

---

## 🔧 FULL ECOSYSTEM SUPPORT

### Phase 1 — Data Infrastructure
- Create /data/sports/ directory with one subfolder per sport
- Generate train CSV + fixtures CSV per sport using column schemas above
- Validate CSVs: no nulls in key columns, correct dtypes, date format YYYY-MM-DD
- Add a data_manifest.json listing each CSV path, row count, date range, and feature count
- Write data_audit.py script that auto-checks schema compliance across all CSVs

### Phase 2 — Model Training Pipeline
- Create train_model.py with --sport flag: \`python train_model.py --sport basketball\`
- Standardize feature engineering pipeline per sport using scikit-learn Pipeline objects
- Add cross-validation (5-fold StratifiedKFold) and print AUC, F1, accuracy per fold
- Serialize each model to /models/{sport}_model.pkl using joblib
- Log training results to training_log.csv (date, sport, AUC, F1, n_rows)

### Phase 3 — Prediction API (Replit)
- Add /predict/{sport} route for each new sport in Flask/FastAPI app
- Each endpoint accepts JSON: { home_team, away_team, ...sport-specific features }
- Load .pkl models at startup — cache in memory, don't reload per request
- Return: { home_win_prob, draw_prob, away_win_prob, confidence, top_features }
- Add /sports endpoint listing all active sports with model version and last trained date

### Phase 4 — VIT_OS UI Integration
- Add sport selector dropdown to the prediction UI (football remains default)
- Render sport-specific input fields dynamically based on selected sport
- Display confidence meter and top-3 feature importance per prediction
- Add a Predictions History tab — stores last 50 predictions with outcome tracking
- Add accuracy dashboard per sport (model AUC, recent prediction accuracy)

### Phase 5 — Quality & Monitoring
- Set up a weekly retrain CRON job that pulls new match results and retrains all models
- Add model drift detection: alert if rolling 2-week accuracy drops > 5% vs baseline
- Write pytest unit tests for each prediction endpoint (mock fixture inputs)
- Add a /health endpoint that reports model load status for all sports
- Document all sports, their schemas, and model metrics in a README_SPORTS.md

---

**Expected model file outputs:**
- models/basketball_model.pkl
- models/tennis_model.pkl (ATP) + tennis_wta_model.pkl
- models/nfl_model.pkl + nfl_spread_model.pkl
- models/mlb_model.pkl + mlb_runline_model.pkl
- models/rugby_model.pkl

All models must follow the existing VIT_OS pipeline conventions and be compatible with the current Replit deployment.`,p=()=>{navigator.clipboard.writeText(u()),d(!0),setTimeout(()=>d(!1),2e3)};return e.jsxs("div",{style:{fontFamily:"'Courier New', Courier, monospace",background:"linear-gradient(135deg, #0a0a0f 0%, #0f0f1a 50%, #0a0f0a 100%)",minHeight:"100vh",color:"#e0e0e0",padding:"0",margin:"0"},children:[e.jsxs("div",{style:{background:"linear-gradient(90deg, #0d1117 0%, #1a1f2e 50%, #0d1117 100%)",borderbottom:"1px solid #1e3a1e",padding:"24px 32px",position:"sticky",top:0,zIndex:10,display:"flex",alignItems:"center",justifyContent:"space-between",boxShadow:"0 4px 24px rgba(0,0,0,0.4)"},children:[e.jsxs("div",{style:{display:"flex",alignItems:"center",gap:"16px"},children:[e.jsx("div",{style:{background:"linear-gradient(135deg, #00ff88, #00cc66)",borderRadius:"8px",padding:"8px 12px",fontWeight:"bold",fontSize:"14px",color:"#000",letterSpacing:"2px"},children:"VIT_OS"}),e.jsxs("div",{children:[e.jsx("div",{style:{fontSize:"18px",fontWeight:"bold",color:"#00ff88",letterSpacing:"1px"},children:"JULES EXPANSION PROMPT"}),e.jsx("div",{style:{fontSize:"11px",color:"#556655",letterSpacing:"2px",marginTop:"2px"},children:"5 SPORTS · FULL ECOSYSTEM · PRODUCTION READY"})]})]}),e.jsx("button",{onClick:p,style:{background:n?"linear-gradient(135deg, #00cc66, #009944)":"linear-gradient(135deg, #00ff88, #00cc66)",border:"none",borderRadius:"8px",padding:"10px 24px",color:"#000",fontWeight:"bold",fontFamily:"'Courier New', monospace",fontSize:"13px",cursor:"pointer",letterSpacing:"1px",transition:"all 0.2s",boxShadow:"0 4px 16px rgba(0,255,136,0.3)"},children:n?"✓ COPIED":"⎘ COPY PROMPT"})]}),e.jsxs("div",{style:{maxWidth:"1100px",margin:"0 auto",padding:"32px 24px"},children:[e.jsxs("div",{style:{marginbottom:"40px"},children:[e.jsx("div",{style:{fontSize:"11px",color:"#556655",letterSpacing:"3px",marginbottom:"16px",textTransform:"uppercase"},children:"▸ NEW SPORTS COVERAGE"}),e.jsx("div",{style:{display:"grid",gridTemplateColumns:"repeat(auto-fit, minmax(200px, 1fr))",gap:"12px"},children:c.map(a=>e.jsxs("button",{onClick:()=>_(r===a.id?null:a.id),style:{background:r===a.id?`linear-gradient(135deg, ${a.color}22, ${a.accent}11)`:"rgba(255,255,255,0.03)",border:`1px solid ${r===a.id?a.color:"#1e3a1e"}`,borderRadius:"12px",padding:"16px",cursor:"pointer",textAlign:"left",transition:"all 0.2s",color:"#e0e0e0",fontFamily:"'Courier New', monospace",boxShadow:r===a.id?`0 0 20px ${a.color}33`:"none"},children:[e.jsx("div",{style:{fontSize:"28px",marginbottom:"8px"},children:a.emoji}),e.jsx("div",{style:{fontSize:"12px",fontWeight:"bold",color:r===a.id?a.color:"#aaa",letterSpacing:"0.5px",lineHeight:"1.3"},children:a.name}),e.jsxs("div",{style:{marginTop:"8px",fontSize:"10px",color:"#556655",letterSpacing:"1px"},children:["ACC: ",a.accuracy]})]},a.id))})]}),r&&(()=>{const a=c.find(t=>t.id===r);return a?e.jsxs("div",{style:{background:`linear-gradient(135deg, ${a.color}11, rgba(0,0,0,0.4))`,border:`1px solid ${a.color}44`,borderRadius:"16px",padding:"24px",marginbottom:"32px",animation:"fadeIn 0.2s ease"},children:[e.jsxs("div",{style:{display:"flex",gap:"8px",alignItems:"center",marginbottom:"20px"},children:[e.jsx("span",{style:{fontSize:"24px"},children:a.emoji}),e.jsx("span",{style:{color:a.color,fontWeight:"bold",fontSize:"16px",letterSpacing:"1px"},children:a.name.toUpperCase()}),e.jsx("span",{style:{marginLeft:"auto",background:`${a.color}22`,border:`1px solid ${a.color}44`,borderRadius:"6px",padding:"4px 12px",fontSize:"11px",color:a.accent},children:a.trainingRows})]}),e.jsxs("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"20px",marginbottom:"20px"},children:[e.jsxs("div",{children:[e.jsx("div",{style:{fontSize:"10px",color:"#556655",letterSpacing:"2px",marginbottom:"8px"},children:"DATA SOURCES"}),a.dataSources.map((t,o)=>e.jsxs("div",{style:{fontSize:"11px",color:"#aaa",padding:"4px 0",borderbottom:"1px solid #1a1a1a"},children:["→ ",t]},o))]}),e.jsxs("div",{children:[e.jsx("div",{style:{fontSize:"10px",color:"#556655",letterSpacing:"2px",marginbottom:"8px"},children:"KEY MODEL FEATURES"}),a.modelFeatures.map((t,o)=>e.jsxs("div",{style:{fontSize:"11px",color:"#aaa",padding:"4px 0",borderbottom:"1px solid #1a1a1a"},children:["◆ ",t]},o))]})]}),e.jsxs("div",{children:[e.jsx("div",{style:{fontSize:"10px",color:"#556655",letterSpacing:"2px",marginbottom:"10px"},children:"TODO CHECKLIST"}),e.jsx("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"6px"},children:a.todo.map((t,o)=>e.jsxs("div",{style:{background:"rgba(0,0,0,0.3)",border:`1px solid ${a.color}22`,borderRadius:"8px",padding:"8px 12px",fontSize:"11px",color:"#ccc",display:"flex",gap:"8px"},children:[e.jsxs("span",{style:{color:a.accent,flexShrink:0},children:[o+1,"."]}),t]},o))})]}),e.jsxs("div",{style:{marginTop:"16px"},children:[e.jsxs("div",{style:{fontSize:"10px",color:"#556655",letterSpacing:"2px",marginbottom:"8px"},children:["CSV SCHEMA (",a.csvColumns.length," COLUMNS)"]}),e.jsx("div",{style:{background:"rgba(0,0,0,0.4)",border:"1px solid #1e3a1e",borderRadius:"8px",padding:"12px",fontSize:"10px",color:"#00ff88",fontFamily:"'Courier New', monospace",lineHeight:"1.8",wordBreak:"break-all"},children:a.csvColumns.join(", ")})]})]}):null})(),e.jsxs("div",{children:[e.jsx("div",{style:{fontSize:"11px",color:"#556655",letterSpacing:"3px",marginbottom:"16px"},children:"▸ FULL ECOSYSTEM SUPPORT — 5 PHASES"}),e.jsx("div",{style:{display:"flex",flexDirection:"column",gap:"10px"},children:h.map((a,t)=>e.jsxs("div",{children:[e.jsxs("button",{onClick:()=>m(s===t?null:t),style:{width:"100%",background:s===t?`linear-gradient(90deg, ${a.color}22, rgba(0,0,0,0.2))`:"rgba(255,255,255,0.02)",border:`1px solid ${s===t?a.color+"66":"#1e3a1e"}`,borderRadius:"10px",padding:"14px 20px",cursor:"pointer",textAlign:"left",color:"#e0e0e0",fontFamily:"'Courier New', monospace",display:"flex",alignItems:"center",gap:"12px",transition:"all 0.2s"},children:[e.jsx("span",{style:{fontSize:"20px"},children:a.icon}),e.jsx("span",{style:{fontWeight:"bold",fontSize:"12px",color:s===t?a.color:"#aaa",letterSpacing:"1px",flex:1},children:a.phase}),e.jsxs("span",{style:{fontSize:"10px",color:"#556655",background:"rgba(0,0,0,0.3)",padding:"3px 10px",borderRadius:"4px"},children:[a.tasks.length," TASKS"]}),e.jsx("span",{style:{color:"#556655",fontSize:"12px"},children:s===t?"▲":"▼"})]}),s===t&&e.jsx("div",{style:{background:"rgba(0,0,0,0.2)",border:`1px solid ${a.color}33`,borderTop:"none",borderRadius:"0 0 10px 10px",padding:"16px 20px"},children:a.tasks.map((o,i)=>e.jsxs("div",{style:{display:"flex",gap:"12px",padding:"8px 0",borderbottom:i<a.tasks.length-1?"1px solid #111":"none",fontSize:"12px",color:"#ccc"},children:[e.jsxs("span",{style:{color:a.color,fontWeight:"bold",flexShrink:0,fontSize:"11px"},children:["[",String(i+1).padStart(2,"0"),"]"]}),o]},i))})]},t))})]}),e.jsxs("div",{style:{marginTop:"40px",background:"linear-gradient(135deg, rgba(0,255,136,0.05), rgba(0,0,0,0.3))",border:"1px solid #1e3a1e",borderRadius:"16px",padding:"24px",display:"flex",alignItems:"center",justifyContent:"space-between",gap:"20px",flexWrap:"wrap"},children:[e.jsxs("div",{children:[e.jsx("div",{style:{fontSize:"14px",color:"#00ff88",fontWeight:"bold",marginbottom:"4px"},children:"Ready to send to Jules?"}),e.jsx("div",{style:{fontSize:"11px",color:"#556655",letterSpacing:"1px"},children:"Copy the full prompt → paste into Jules → let it build the 5-sport expansion"})]}),e.jsx("button",{onClick:p,style:{background:n?"linear-gradient(135deg, #00cc66, #009944)":"linear-gradient(135deg, #00ff88, #00cc66)",border:"none",borderRadius:"8px",padding:"12px 28px",color:"#000",fontWeight:"bold",fontFamily:"'Courier New', monospace",fontSize:"13px",cursor:"pointer",letterSpacing:"1px",boxShadow:"0 4px 20px rgba(0,255,136,0.35)",whiteSpace:"nowrap"},children:n?"✓ PROMPT COPIED":"⎘ COPY FULL JULES PROMPT"})]})]})]})}export{f as default};
