import csv
import io
import hashlib
from datetime import datetime, timezone

month_map = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
current_year = 2026

def parse_kickoff(row):
    if "date" in row and "time" in row:
        d_str = row["date"].strip()
        t_str = row["time"].strip()
        parts = d_str.split()
        if len(parts) == 2 and parts[1] in month_map:
            day = int(parts[0])
            month = month_map[parts[1]]
            hour, minute = map(int, t_str.split(":"))
            return datetime(current_year, month, day, hour, minute, tzinfo=timezone.utc)
        try:
            return datetime.fromisoformat(f"{d_str} {t_str}").replace(tzinfo=timezone.utc)
        except ValueError:
            # Try some other common formats if fromisoformat fails
            for fmt in ["%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M"]:
                try:
                    return datetime.strptime(f"{d_str} {t_str}", fmt).replace(tzinfo=timezone.utc)
                except:
                    continue
            raise

    k_str = row.get("kickoff_time")
    if k_str:
        return datetime.fromisoformat(k_str).replace(tzinfo=timezone.utc)
    return None

def test_format(csv_content):
    print(f"\nTesting CSV Content:\n{csv_content}")
    reader = csv.DictReader(io.StringIO(csv_content))
    for row_idx, row in enumerate(reader):
        row = {k.strip().lower(): v for k, v in row.items() if k}
        print(f"Row {row_idx+1} normalized: {row}")
        try:
            home = row.get("home") or row.get("home_team")
            away = row.get("away") or row.get("away_team")
            league = row.get("league", "Unknown League")
            kickoff = parse_kickoff(row)

            raw_fp = f"{kickoff.date()}::{home.lower().strip()}::{away.lower().strip()}::{league.lower().strip()}"
            fp = hashlib.md5(raw_fp.encode()).hexdigest()

            h_odds = row.get("h") or row.get("home_odds")
            d_odds = row.get("d") or row.get("draw_odds")
            a_odds = row.get("a") or row.get("away_odds")

            print(f"  Result: {home} vs {away} | {league} | {kickoff} | FP: {fp} | Odds: {h_odds}/{d_odds}/{a_odds}")
        except Exception as e:
            print(f"  Error: {e}")

# Standard
standard_csv = """home_team,away_team,kickoff_time,league,home_odds,draw_odds,away_odds
Arsenal,Chelsea,2026-05-10 15:00,premier_league,2.10,3.40,3.60"""

# Shorthand
shorthand_csv = """#,date,time,home,away,league,H,D,A
1,10 May,15:00,Arsenal,Chelsea,England - Premier League,2.10,3.40,3.60"""

test_format(standard_csv)
test_format(shorthand_csv)
