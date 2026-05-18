# Prophecy Chain - Gap Analysis (v7.0.0)

This document lists the technical and functional gaps identified in the Prophecy Chain module after debugging the initial implementation.

## 1. Technical Gaps (Backend & Protocol)
- [ ] **Real-time Synchronization:** Progression currently re-evaluates on API request or settlement. There is no WebSocket emission when a user crosses a merit threshold or unlocks a new chapter.
- [ ] **Entropy Scoring Implementation:** The `ProgressionEngine` references "Entropy Scoring" (penalizing repetitive behavior) in the UI documentation, but the actual logic is currently a simple 1.35 odds filter and volume cap.
- [ ] **Multi-Sig Governance:** The "Validator" tier (Tier 5) implies access to governance, but the link between prophecy completion and on-chain multi-sig permissioning is not yet cryptographically enforced.
- [ ] **Snapshot Persistence:** Merit snapshots are stored but not yet used for historical performance "look-back" during AI model training (E1 module integration).

## 2. Functional Gaps (User Experience)
- [ ] **Narrative Feedback:** The transition from "Active" to "Sealed" (completed) is purely a UI state change. There are no visual rewards or "unboxing" experiences for earning a new Title or Badge.
- [ ] **Requirement Tooltips:** Users may not understand why a prediction wasn't "Qualified." The UI needs tooltips explaining the 1.35 odds and league diversity rules directly on the checklist.
- [ ] **Prestige Levels:** Once the "High Validator" chapter is sealed, there is no "Infinite Progression" or seasonal reset mechanism.
- [ ] **Social Proof:** Users cannot share their "Prophecy Timeline" or Merit snapshots to social platforms or the internal Leaderboard.

## 3. UI/UX Bugs (Resolved but noteworthy)
- [X] **Routing Conflict:** Component was using `react-router-dom` in a `wouter` ecosystem, causing navigation failures.
- [X] **Data Perception:** Seeded "Canonical" data felt hardcoded because initial requirements (5 predictions) were too high for immediate feedback.
- [ ] **Mobile Layout:** The chapter timeline line (`absolute left-8`) occasionally overlaps with text on ultra-small screens (< 320px).

## 4. Security Gaps
- [ ] **Sybil Resistance:** While volume caps exist, there is no check if multiple accounts are "farming" merit from the same IP/Device for the Prophecy rewards.
- [ ] **Oracle Dependency:** Progression depends on match settlement. If the Oracle relayers are offline, the Prophecy Chain freezes.
