## 2024-05-22 - [Optimized Leaderboard N+1]
**Learning:** The leaderboard endpoint was scanning all users and performing 2 database queries per user. This is a classic N+1 bottleneck. In an async environment with SQLAlchemy, this can lead to significant latency and database connection exhaustion.
**Action:** Use bulk aggregation and fetching for top-N users. Fetch top users first, then use `.in_(user_ids)` to bulk-fetch related stats in constant time.
