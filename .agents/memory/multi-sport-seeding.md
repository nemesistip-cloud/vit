---
name: Multi-sport match seeding
description: How to seed non-football matches (basketball, tennis, etc.) into the DB
---

## Rule
`Match.sport` column (String(32), default "football") accepts: football, basketball, tennis, cricket, american_football, ice_hockey, mma, formula1, rugby.

`MatchRequest` schema now has an optional `sport` field (default "football") — pass it in the POST body to `/api/predict`.

The predict route saves `sport=getattr(match, "sport", "football") or "football"` on new Match creation.

**Why:** The 13-model ensemble operates the same way for any sport; only the league/team context differs. Non-football matches need to be seeded into the DB for the platform to show multi-sport predictions.

**How to apply:** Insert Match rows directly via SQLAlchemy with `sport=<type>` set, or pass `sport` in the predict API body. The ensemble will generate football-style probability distributions regardless of sport type.

## Sport-specific notes
- american_football / ice_hockey: draw_prob = 0 (NFL) or ~0.07 (NHL overtime). The ensemble doesn't automatically zero out draws — these were seeded manually for the 2 sports.
- recommended_stake CHECK constraint: `0 <= recommended_stake <= 0.20` (NOT 25 units — it's a fraction).
