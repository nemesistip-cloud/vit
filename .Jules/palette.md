## 2026-06-23 - [CSV Import & Wallet Robustness]
**Learning:** Parsing CSV dates from external sources (like bookmakers) often requires handling shorthand formats (e.g., "10 May") which lack years. Using a "year-wrapping" logic based on the current month prevents fixtures from being assigned to the wrong year during year-end transitions.
**Action:** Always implement a naive datetime fallback for database compatibility in SQLite/Postgres when dealing with mixed timezone inputs from user uploads.

**Learning:** Blank screens in React pages (like the Wallet page) are often caused by strict null checks on data that hasn't loaded yet.
**Action:** Provide a robust "Protection Layer" or fallback UI that keeps the main layout/navigation visible while explaining why data is missing (e.g., "Unable to load wallet data").
