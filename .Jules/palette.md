## 2026-06-23 - [CSV Import & Wallet Robustness]
**Learning:** Parsing CSV dates from external sources (like bookmakers) often requires handling shorthand formats (e.g., "10 May") which lack years. Using a "year-wrapping" logic based on the current month prevents fixtures from being assigned to the wrong year during year-end transitions.
**Action:** Always implement a naive datetime fallback for database compatibility in SQLite/Postgres when dealing with mixed timezone inputs from user uploads.

**Learning:** Blank screens in React pages (like the Wallet page) are often caused by strict null checks on data that hasn't loaded yet.
**Action:** Provide a robust "Protection Layer" or fallback UI that keeps the main layout/navigation visible while explaining why data is missing (e.g., "Unable to load wallet data").

## 2026-06-24 - [UI Consistency & Tabbed Discovery]
**Learning:** Discrepancies between UI counters and displayed lists (e.g., "Matches (208)" vs "0 matches found") are frequently caused by decoupled state where a global count is fetched but the display list is overly filtered or uses a different data source.
**Action:** Always synchronize summary counts ("Found: X") with the actual length of the filtered/sorted array used for rendering, and provide a "Clear Filters" mechanism to help users recover from empty states.

**Learning:** UX gaps often manifest as missing discovery layers for secondary entities. Users expecting a "Matches" page to show both events and teams/players benefit from a tabbed interface that contextualizes the data differently.
**Action:** Use Radix Tabs to segment high-density data views, ensuring that counters in tab triggers reflect the total pool while the body summary reflects the active view's specific filter state.
