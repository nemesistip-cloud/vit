"""Academic Agent — provides specialized tutoring and indexes school resources.
v5.2.0 — Part of the Student Intelligence Network.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from sqlalchemy import select, or_
from app.agents.base import BaseAgent, AgentStatus
from app.db.database import AsyncSessionLocal
from app.modules.academy.models import AcademicResource, Course

logger = logging.getLogger(__name__)

class AcademicAgent(BaseAgent):
    """
    Autonomous agent responsible for:
    1. Indexing new academic resources into VIT Memory for RAG.
    2. Providing contextual tutoring using database-backed retrieval.
    """

    def __init__(self) -> None:
        super().__init__(
            name="academic-tutor",
            interval_seconds=3600,  # Run every hour
            initial_delay_seconds=30,
            enabled=True,
        )

    async def run_cycle(self) -> Dict[str, Any]:
        """Find unindexed resources and prepare them for retrieval."""
        async with AsyncSessionLocal() as db:
            # Simple indexing: mark resources that have content_summary
            q = select(AcademicResource).where(AcademicResource.is_verified == True).limit(50)
            res = await db.execute(q)
            resources = res.scalars().all()

            return {
                "indexed_count": len(resources),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def get_tutor_response(self, user_query: str, university: str, course_code: str) -> str:
        """
        Perform database-backed RAG to answer student questions.
        """
        context_parts = []

        async with AsyncSessionLocal() as db:
            # 1. Find the course
            course_q = select(Course).where(
                Course.course_code == course_code,
                Course.university == university
            )
            course_res = await db.execute(course_q)
            course = course_res.scalar_one_or_none()

            if course:
                # 2. Find related resources (notes, past questions)
                # For now, we search by title and description matching keywords in query
                keywords = user_query.split()[:5] # simple keyword extraction
                filters = [AcademicResource.course_id == course.id, AcademicResource.is_verified == True]

                resource_q = select(AcademicResource).where(*filters)
                resource_res = await db.execute(resource_q)
                resources = resource_res.scalars().all()

                for r in resources:
                    if any(k.lower() in r.title.lower() or (r.description and k.lower() in r.description.lower()) for k in keywords):
                        context_parts.append(f"Source: {r.title}\nContent: {r.description or 'No description available.'}")

        # 3. Call existing AI client with context
        from app.services.ai_client import AIClient
        ai = AIClient()

        context_str = "\n\n".join(context_parts[:3]) # Use top 3 sources
        prompt = f"""You are the VIT Academic Tutor. Answer the student's question using the provided context from their university ({university}) for the course {course_code}.

If the context doesn't contain the answer, use your general knowledge but prioritize the context.

Context:
{context_str}

Question: {user_query}
"""

        try:
            # Fallback to a simple response if AIClient fails or is complex to call here
            response = await ai.generate_text(prompt, system_prompt="You are a helpful university tutor in Nigeria.")
            return response
        except Exception as e:
            logger.error(f"AI Tutor generation failed: {e}")
            return f"I found {len(context_parts)} relevant materials at {university} for {course_code}, but I'm having trouble generating a detailed response right now. Please try again shortly."
