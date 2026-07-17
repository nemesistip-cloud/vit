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
            try:
                day = int(parts[0])
                month = month_map[parts[1]]
                hour, minute = map(int, t_str.split(":"))
                return datetime(current_year, month, day, hour, minute, tzinfo=timezone.utc)
            except:
                pass

        # Try common formats
        full_str = f"{d_str} {t_str}"
        for fmt in ["%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%d %b %H:%M"]:
            try:
                dt = datetime.strptime(full_str, fmt)
                if dt.year == 1900: # strptime default year
                    dt = dt.replace(year=current_year)
                return dt.replace(tzinfo=timezone.utc)
            except:
                continue

        try:
            return datetime.fromisoformat(full_str).replace(tzinfo=timezone.utc)
        except:
            raise ValueError(f"Could not parse date/time: {full_str}")

    k_str = row.get("kickoff_time")
    if k_str:
        try:
            return datetime.fromisoformat(k_str).replace(tzinfo=timezone.utc)
        except:
            # Try with space instead of T
            try:
                return datetime.strptime(k_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            except:
                raise ValueError(f"Could not parse kickoff_time: {k_str}")
    return None

def test():
    # Standard
    s1 = {"home_team": "Arsenal", "away_team": "Chelsea", "kickoff_time": "2026-05-10 15:00", "league": "PL"}
    print(f"S1: {parse_kickoff(s1)}")

    # Shorthand
    s2 = {"date": "10 May", "time": "15:00", "home": "Arsenal", "away": "Chelsea", "league": "PL"}
    print(f"S2: {parse_kickoff(s2)}")

    # Shorthand with year
    s3 = {"date": "2026-05-10", "time": "15:00"}
    print(f"S3: {parse_kickoff(s3)}")

    # Fingerprint check
    h1 = "Arsenal"
    a1 = "Chelsea"
    l1 = "PL"
    dt1 = parse_kickoff(s1)
    raw_fp = f"{dt1.date()}::{h1.lower().strip()}::{a1.lower().strip()}::{l1.lower().strip()}"
    fp1 = hashlib.md5(raw_fp.encode()).hexdigest()
    print(f"FP1: {fp1}")

test()
