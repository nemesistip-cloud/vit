from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from .models import ElectionEvent, PollingData
from app.services.web_search import _ddg_search
from app.services.ai_client import call_ai
import random
import json

class ElectionService:
    @staticmethod
    async def run_sentiment_analysis(db: AsyncSession, election_id: int):
        """
        Runs sentiment analysis for an election using web search and native AI.
        """
        # 1. Fetch Election Data
        result = await db.execute(select(ElectionEvent).where(ElectionEvent.id == election_id))
        election = result.scalar_one_or_none()
        if not election:
            return None

        # 2. Gather External Intelligence (DuckDuckGo Lite)
        candidates_str = ", ".join(election.candidates.keys()) if isinstance(election.candidates, dict) else str(election.candidates)
        query = f"election sentiment {election.title} {election.country} {candidates_str}"
        news_snippets = await _ddg_search(query, max_results=8)

        # 3. Construct AI Prompt
        news_context = "\n".join([f"- {s}" for s in news_snippets])
        prompt = f"""Analyze the electoral sentiment for the following election event.
Event: {election.title}
Country: {election.country}
Candidates: {candidates_str}

Recent News Context:
{news_context}

Based on this context, estimate the current sentiment scores for each candidate and provide a brief rationale.
Return ONLY a JSON object (no markdown):
{{
  "scores": {{ "candidate_name": 0.XX, ... }},
  "rationale": "short explanation",
  "data_points_analyzed": {len(news_snippets)}
}}"""

        # 4. Invoke Native AI Orchestrator
        ai_response = await call_ai(prompt)

        try:
            # Clean possible markdown fences if AI returns them despite instructions
            clean_response = ai_response.strip().replace("```json", "").replace("```", "").strip()
            sentiment_data = json.loads(clean_response)
        except Exception:
            # Fallback to simulated data if AI fails or returns invalid JSON
            sentiment_data = {
                "scores": {k: round(random.uniform(0.3, 0.5), 2) for k in election.candidates.keys()},
                "rationale": "Simulated fallback due to AI response error.",
                "data_points_analyzed": len(news_snippets)
            }

        # 5. Persist Results
        from datetime import datetime, timezone
        await db.execute(
            update(ElectionEvent)
            .where(ElectionEvent.id == election_id)
            .values(sentiment_data={
                **sentiment_data,
                "last_updated": datetime.now(timezone.utc).isoformat()
            })
        )
        await db.commit()
        return sentiment_data
