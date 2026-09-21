# app/modules/elections/simulator.py
"""Electoral & Policy Simulator logic (TRACK-015)."""

import math
import statistics
import random
from datetime import date
from typing import Optional


class PollAggregator:
    """Weighted poll aggregation with sample-size and recency weighting."""

    _LAMBDA = math.log(2) / 30  # 30-day half-life

    def aggregate(self, polls: list[dict]) -> dict:
        """
        Aggregate a list of polls into a weighted average per candidate.

        Each poll dict should have:
            - conducted_date: date | str (ISO)
            - sample_size: int
            - margin_of_error: float
            - results: list of {candidate_id, percentage}
            - weight: float (optional poll-level override, default 1.0)

        Returns dict[candidate_id -> float] (weighted average %).
        """
        today = date.today()
        weighted_sums: dict[str, float] = {}
        weight_totals: dict[str, float] = {}

        for poll in polls:
            conducted = poll.get("conducted_date")
            if isinstance(conducted, str):
                conducted = date.fromisoformat(conducted)
            days_ago = max(0, (today - conducted).days) if conducted else 0

            sample_size = int(poll.get("sample_size", 1000))
            sample_weight = min(1.0, sample_size / 1000)
            recency_weight = math.exp(-self._LAMBDA * days_ago)
            poll_weight = sample_weight * recency_weight * float(poll.get("weight", 1.0))

            for entry in poll.get("results", []):
                cid = str(entry["candidate_id"])
                pct = float(entry["percentage"])
                weighted_sums[cid] = weighted_sums.get(cid, 0.0) + pct * poll_weight
                weight_totals[cid] = weight_totals.get(cid, 0.0) + poll_weight

        return {
            cid: round(weighted_sums[cid] / weight_totals[cid], 4)
            for cid in weighted_sums
            if weight_totals[cid] > 0
        }


class SeatProjector:
    """D'Hondt proportional seat allocation."""

    def project(self, vote_shares: dict[str, float], total_seats: int) -> dict[str, int]:
        """
        Allocate `total_seats` using the D'Hondt method.

        vote_shares: dict[party_name -> vote_share_float (0-100)]
        Returns dict[party_name -> seats_won]
        """
        if total_seats <= 0 or not vote_shares:
            return {}

        seats: dict[str, int] = {p: 0 for p in vote_shares}
        for _ in range(total_seats):
            quotients = {
                p: share / (seats[p] + 1)
                for p, share in vote_shares.items()
                if share > 0
            }
            if not quotients:
                break
            winner = max(quotients, key=lambda p: quotients[p])
            seats[winner] += 1

        return seats

    def swing_scenario(
        self,
        base_shares: dict[str, float],
        swing_party: str,
        swing_delta: float,
        total_seats: int,
    ) -> dict[str, int]:
        """
        Apply a swing of `swing_delta` percentage points to `swing_party`,
        redistributing the change proportionally from/to other parties.
        """
        if swing_party not in base_shares:
            return self.project(base_shares, total_seats)

        adjusted = dict(base_shares)
        current = adjusted[swing_party]
        new_val = max(0.0, min(100.0, current + swing_delta))
        actual_delta = new_val - current
        adjusted[swing_party] = new_val

        others = {p: v for p, v in adjusted.items() if p != swing_party and v > 0}
        total_others = sum(others.values())

        if total_others > 0 and actual_delta != 0:
            for p in others:
                adjusted[p] = max(0.0, adjusted[p] - actual_delta * (others[p] / total_others))

        return self.project(adjusted, total_seats)


class OutcomeSimulator:
    """Monte Carlo simulation for win probabilities."""

    def monte_carlo(
        self,
        candidates: list[dict],
        n_sims: int = 5000,
    ) -> list[dict]:
        """
        Run `n_sims` simulations, each perturbing each candidate's poll_pct
        by N(0, margin_of_error), then picking the argmax.

        candidates: list of dicts with:
            - candidate_id: str
            - poll_pct: float
            - margin_of_error: float (default 3.0)

        Returns list of {candidate_id, win_prob}.
        """
        if not candidates:
            return []

        wins: dict[str, int] = {str(c["candidate_id"]): 0 for c in candidates}

        for _ in range(n_sims):
            best_id = None
            best_val = float("-inf")
            for c in candidates:
                cid = str(c["candidate_id"])
                moe = float(c.get("margin_of_error", 3.0))
                perturbed = float(c.get("poll_pct", 0.0)) + random.gauss(0, moe)
                if perturbed > best_val:
                    best_val = perturbed
                    best_id = cid
            if best_id is not None:
                wins[best_id] += 1

        return [
            {"candidate_id": cid, "win_prob": round(count / n_sims, 4)}
            for cid, count in wins.items()
        ]


class PolicyScorer:
    """Keyword-based policy impact scoring across domains."""

    DOMAINS = [
        "economy",
        "employment",
        "social_equity",
        "environment",
        "security",
        "trade",
        "healthcare",
    ]

    # (keyword -> {domain: delta}) per category
    _KEYWORD_MAP: dict[str, dict[str, dict[str, float]]] = {
        "fiscal": {
            "tax cut":        {"economy": 0.6, "employment": 0.3, "social_equity": -0.3},
            "tax increase":   {"economy": -0.4, "social_equity": 0.4},
            "austerity":      {"economy": -0.3, "employment": -0.5, "social_equity": -0.4},
            "stimulus":       {"economy": 0.5, "employment": 0.5},
            "deficit":        {"economy": -0.4},
            "surplus":        {"economy": 0.4},
            "spending cut":   {"employment": -0.4, "social_equity": -0.3},
            "investment":     {"economy": 0.4, "employment": 0.4},
            "subsidy":        {"economy": 0.2, "employment": 0.2},
            "debt":           {"economy": -0.3},
        },
        "social": {
            "welfare":        {"social_equity": 0.6, "economy": -0.2},
            "inequality":     {"social_equity": -0.5},
            "equality":       {"social_equity": 0.6},
            "poverty":        {"social_equity": -0.5, "employment": -0.3},
            "housing":        {"social_equity": 0.4},
            "education":      {"social_equity": 0.4, "employment": 0.3},
            "pension":        {"social_equity": 0.3, "economy": -0.2},
            "discrimination": {"social_equity": -0.6},
            "rights":         {"social_equity": 0.5},
        },
        "trade": {
            "tariff":         {"trade": -0.5, "economy": -0.3},
            "free trade":     {"trade": 0.6, "economy": 0.4},
            "protectionism":  {"trade": -0.5, "economy": -0.2},
            "export":         {"trade": 0.4, "economy": 0.4},
            "import":         {"trade": 0.3},
            "sanction":       {"trade": -0.6, "economy": -0.4, "security": 0.2},
            "embargo":        {"trade": -0.7, "economy": -0.4},
            "wto":            {"trade": 0.4},
            "bilateral":      {"trade": 0.3},
        },
        "security": {
            "defense":        {"security": 0.5, "economy": -0.2},
            "military":       {"security": 0.5, "economy": -0.3},
            "police":         {"security": 0.4},
            "crime":          {"security": -0.4},
            "terror":         {"security": -0.5},
            "cyber":          {"security": 0.3},
            "nato":           {"security": 0.4, "trade": 0.2},
            "border":         {"security": 0.3, "trade": -0.2},
            "intelligence":   {"security": 0.4},
        },
        "environment": {
            "carbon":         {"environment": -0.5, "economy": -0.2},
            "emission":       {"environment": -0.4},
            "renewable":      {"environment": 0.7, "economy": 0.2, "employment": 0.2},
            "solar":          {"environment": 0.6, "employment": 0.2},
            "wind":           {"environment": 0.6, "employment": 0.2},
            "fossil":         {"environment": -0.6, "economy": 0.2},
            "green":          {"environment": 0.5, "economy": 0.2},
            "climate":        {"environment": -0.4},
            "pollution":      {"environment": -0.5},
            "conservation":   {"environment": 0.5},
        },
        "healthcare": {
            "universal":      {"healthcare": 0.7, "social_equity": 0.5, "economy": -0.3},
            "privatize":      {"healthcare": -0.4, "economy": 0.2},
            "insurance":      {"healthcare": 0.3},
            "hospital":       {"healthcare": 0.4, "employment": 0.2},
            "mental health":  {"healthcare": 0.5, "social_equity": 0.3},
            "drug":           {"healthcare": -0.2},
            "vaccine":        {"healthcare": 0.5},
            "access":         {"healthcare": 0.4, "social_equity": 0.3},
            "cost":           {"healthcare": -0.3},
            "pharmaceutical": {"healthcare": 0.2, "economy": 0.1},
        },
        "education": {
            "free":           {"social_equity": 0.5, "economy": 0.2},
            "university":     {"social_equity": 0.3, "employment": 0.3},
            "school":         {"social_equity": 0.4},
            "student loan":   {"social_equity": -0.3, "economy": -0.2},
            "voucher":        {"social_equity": -0.2},
            "teacher":        {"social_equity": 0.3, "employment": 0.3},
            "curriculum":     {"social_equity": 0.2},
            "stem":           {"employment": 0.4, "economy": 0.3},
            "private":        {"social_equity": -0.3},
            "funding":        {"social_equity": 0.4, "economy": -0.1},
        },
    }

    def score(self, category: str, description_keywords: list[str]) -> dict[str, float]:
        """
        Score a policy across all domains based on keyword matching.
        Returns dict[domain -> float (-1.0 to +1.0)].
        """
        scores: dict[str, float] = {d: 0.0 for d in self.DOMAINS}
        kw_map = self._KEYWORD_MAP.get(category, {})
        text = " ".join(description_keywords).lower()

        for keyword, domain_deltas in kw_map.items():
            if keyword in text:
                for domain, delta in domain_deltas.items():
                    scores[domain] = scores.get(domain, 0.0) + delta

        # Clamp to [-1, +1]
        return {d: max(-1.0, min(1.0, round(v, 3))) for d, v in scores.items()}
