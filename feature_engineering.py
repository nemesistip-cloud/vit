import pandas as pd
import json

# Load data
with open("training_data.json") as f:
    data = json.load(f)

df = pd.DataFrame(data)

# Sort chronologically
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

# Convert result to points
def get_points(row, team_type):
    if row["actual_outcome"] == "H":
        return 3 if team_type == "home" else 0
    elif row["actual_outcome"] == "A":
        return 3 if team_type == "away" else 0
    else:
        return 1

df["home_points"] = df.apply(lambda x: get_points(x, "home"), axis=1)
df["away_points"] = df.apply(lambda x: get_points(x, "away"), axis=1)

# Combine home & away into single team history table
home_df = df[["date","home_team","home_goals","away_goals","home_points"]].rename(
    columns={
        "home_team":"team",
        "home_goals":"goals_scored",
        "away_goals":"goals_conceded",
        "home_points":"points"
    }
)

away_df = df[["date","away_team","away_goals","home_goals","away_points"]].rename(
    columns={
        "away_team":"team",
        "away_goals":"goals_scored",
        "home_goals":"goals_conceded",
        "away_points":"points"
    }
)

team_df = pd.concat([home_df, away_df])
team_df = team_df.sort_values("date")

# Rolling features
team_df["points_last5"] = team_df.groupby("team")["points"].rolling(5).sum().shift(1).reset_index(0,drop=True)
team_df["goals_scored_last5"] = team_df.groupby("team")["goals_scored"].rolling(5).sum().shift(1).reset_index(0,drop=True)
team_df["goals_conceded_last5"] = team_df.groupby("team")["goals_conceded"].rolling(5).sum().shift(1).reset_index(0,drop=True)

# Merge back to main dataset
df = df.merge(
    team_df[["date","team","points_last5","goals_scored_last5","goals_conceded_last5"]],
    left_on=["date","home_team"],
    right_on=["date","team"],
    how="left"
).rename(columns={
    "points_last5":"home_form",
    "goals_scored_last5":"home_attack",
    "goals_conceded_last5":"home_defense"
}).drop("team", axis=1)

df = df.merge(
    team_df[["date","team","points_last5","goals_scored_last5","goals_conceded_last5"]],
    left_on=["date","away_team"],
    right_on=["date","team"],
    how="left"
).rename(columns={
    "points_last5":"away_form",
    "goals_scored_last5":"away_attack",
    "goals_conceded_last5":"away_defense"
}).drop("team", axis=1)

# Create difference features
df["form_diff"] = df["home_form"] - df["away_form"]
df["attack_diff"] = df["home_attack"] - df["away_attack"]
df["defense_diff"] = df["home_defense"] - df["away_defense"]

# Drop rows with missing history
df = df.dropna()

print("Final dataset:", df.shape)

# Save
df.to_csv("model_ready_data.csv", index=False)