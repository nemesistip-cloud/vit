import logging
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete

from app.modules.creator_studio.models import (
    CreatorBrand,
    BrandMemory,
    CreatorIdea,
    CreatorContentItem,
    XAccountConnection,
    CreatorUsageLog,
    ContentStatus,
    ContentType,
)
from app.modules.creator_studio.schemas import (
    BrandCreate,
    BrandUpdate,
    BrandMemoryCreate,
    IdeaCreate,
    ContentItemCreate,
    ContentItemUpdate,
)

logger = logging.getLogger(__name__)


class CreatorStudioService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Brand Management ───────────────────────────────────────────────────

    async def create_brand(self, user_id: int, data: BrandCreate) -> CreatorBrand:
        brand = CreatorBrand(
            user_id=user_id,
            handle=data.handle.lstrip("@"),
            display_name=data.display_name,
            niche=data.niche,
            bio=data.bio,
            target_audience=data.target_audience,
            tone_and_voice=data.tone_and_voice,
            writing_style=data.writing_style,
            preferred_topics=data.preferred_topics,
            topics_to_avoid=data.topics_to_avoid,
            vocabulary=data.vocabulary,
            goals=data.goals,
        )
        self.db.add(brand)
        await self.db.commit()
        await self.db.refresh(brand)
        return brand

    async def get_user_brands(self, user_id: int) -> List[CreatorBrand]:
        stmt = select(CreatorBrand).where(CreatorBrand.user_id == user_id, CreatorBrand.is_active == True)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_brand(self, brand_id: str, user_id: int) -> Optional[CreatorBrand]:
        stmt = select(CreatorBrand).where(CreatorBrand.id == brand_id, CreatorBrand.user_id == user_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def update_brand(self, brand_id: str, user_id: int, data: BrandUpdate) -> Optional[CreatorBrand]:
        brand = await self.get_brand(brand_id, user_id)
        if not brand:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "handle" in update_data and update_data["handle"]:
            update_data["handle"] = update_data["handle"].lstrip("@")

        for field, value in update_data.items():
            setattr(brand, field, value)

        await self.db.commit()
        await self.db.refresh(brand)
        return brand

    # ── Brand Memory ───────────────────────────────────────────────────────

    async def add_memory(self, brand_id: str, user_id: int, data: BrandMemoryCreate) -> Optional[BrandMemory]:
        brand = await self.get_brand(brand_id, user_id)
        if not brand:
            return None

        memory = BrandMemory(
            brand_id=brand_id,
            category=data.category,
            key=data.key,
            value=data.value,
            weight=data.weight,
            source=data.source,
        )
        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)
        return memory

    async def get_memories(self, brand_id: str, user_id: int) -> List[BrandMemory]:
        brand = await self.get_brand(brand_id, user_id)
        if not brand:
            return []
        stmt = select(BrandMemory).where(BrandMemory.brand_id == brand_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def delete_memory(self, memory_id: str, brand_id: str, user_id: int) -> bool:
        brand = await self.get_brand(brand_id, user_id)
        if not brand:
            return False
        stmt = select(BrandMemory).where(BrandMemory.id == memory_id, BrandMemory.brand_id == brand_id)
        res = await self.db.execute(stmt)
        memory = res.scalar_one_or_none()
        if not memory:
            return False
        await self.db.delete(memory)
        await self.db.commit()
        return True

    # ── Ideas Engine & AI Generation ───────────────────────────────────────

    async def generate_ideas(
        self, brand_id: str, user_id: int, topic: Optional[str] = None, count: int = 5
    ) -> List[CreatorIdea]:
        brand = await self.get_brand(brand_id, user_id)
        if not brand:
            return []

        memories = await self.get_memories(brand_id, user_id)
        memory_summary = ", ".join([f"{m.key}: {m.value}" for m in memories])

        niche = topic or brand.niche or "Tech & Web3"
        topics = brand.preferred_topics or [niche]
        pillars = topics[:3]

        idea_templates = [
            {
                "title": f"Why traditional approaches to {niche} are failing (and what to do instead)",
                "angle": f"A bold, contrarian breakdown tailored for {brand.target_audience or 'creators and builders'}.",
                "hook_templates": [
                    f"Most people get {niche} completely wrong. Here's why:",
                    f"I spent 3 years analyzing {niche}. Here are 5 uncomfortable truths:",
                ],
                "suggested_format": ContentType.THREAD.value,
            },
            {
                "title": f"5 Essential rules for mastering {niche} in 2025",
                "angle": "Actionable, step-by-step framework highlighting best practices and personal rules.",
                "hook_templates": [
                    f"If you want to win at {niche}, remember these 5 rules:",
                    f"Cheat code for {niche}:",
                ],
                "suggested_format": ContentType.SINGLE_POST.value,
            },
            {
                "title": f"Unpopular opinion about {niche}",
                "angle": f"Provocative take matching tone '{brand.tone_and_voice}' to spark high engagement.",
                "hook_templates": [
                    f"Unpopular opinion: {niche} is about to change forever.",
                    "Nobody is talking about this, but:",
                ],
                "suggested_format": ContentType.HOT_TAKE.value,
            },
            {
                "title": f"The step-by-step story of building in {niche}",
                "angle": "Authentic personal narrative sharing lessons learned, pitfalls, and breakthroughs.",
                "hook_templates": [
                    f"How we turned a simple idea into a system in {niche}:",
                    "The hardest lesson I learned this year:",
                ],
                "suggested_format": ContentType.STORY.value,
            },
            {
                "title": f"The future of {niche}: What happens next?",
                "angle": "Forward-looking strategic insights backed by brand memory and core principles.",
                "hook_templates": [
                    f"Where is {niche} heading next? 3 big predictions:",
                    "The next massive wave in technology:",
                ],
                "suggested_format": ContentType.LONG_FORM.value,
            },
        ]

        created_ideas = []
        for i in range(min(count, len(idea_templates))):
            tmpl = idea_templates[i]
            idea = CreatorIdea(
                brand_id=brand_id,
                title=tmpl["title"],
                angle=tmpl["angle"],
                hook_templates=tmpl["hook_templates"],
                suggested_format=tmpl["suggested_format"],
                pillars=pillars,
                source="AI_GEN",
                status="NEW",
            )
            self.db.add(idea)
            created_ideas.append(idea)

        # Log usage
        usage = CreatorUsageLog(
            user_id=user_id,
            brand_id=brand_id,
            action_type="GENERATE_IDEAS",
            tokens_used=150 * len(created_ideas),
            details={"count": len(created_ideas), "niche": niche},
        )
        self.db.add(usage)

        await self.db.commit()
        for idea in created_ideas:
            await self.db.refresh(idea)

        return created_ideas

    async def get_ideas(self, brand_id: str, user_id: int) -> List[CreatorIdea]:
        brand = await self.get_brand(brand_id, user_id)
        if not brand:
            return []
        stmt = select(CreatorIdea).where(CreatorIdea.brand_id == brand_id).order_by(CreatorIdea.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def generate_content(
        self,
        brand_id: str,
        user_id: int,
        content_type: ContentType,
        idea_id: Optional[str] = None,
        topic: Optional[str] = None,
        instructions: Optional[str] = None,
        include_hooks: bool = True,
    ) -> CreatorContentItem:
        brand = await self.get_brand(brand_id, user_id)
        if not brand:
            raise ValueError("Brand not found")

        idea = None
        if idea_id:
            stmt = select(CreatorIdea).where(CreatorIdea.id == idea_id, CreatorIdea.brand_id == brand_id)
            res = await self.db.execute(stmt)
            idea = res.scalar_one_or_none()

        subject = idea.title if idea else (topic or brand.niche or "Web3 Innovation")
        tone = brand.tone_and_voice or "Engaging & Analytical"
        audience = brand.target_audience or "Creators, developers, and builders"

        posts = []
        if content_type == ContentType.THREAD:
            posts = [
                f"1/ 🧵 {subject}\n\nHere is everything you need to know, distilled for {audience}:",
                "2/ The Core Problem:\nMost approaches overlook the main leverage point. When building in this space, clarity beats noise.",
                "3/ The Solution:\nFocus on 3 pillars:\n• Consistency\n• Deep research\n• Continuous feedback loops",
                f"4/ Key Takeaway:\nStick to what works, iterate fast, and build with conviction.\n\nTone & Style: {tone}.",
                f"5/ If you found this valuable:\n1. Follow @{brand.handle} for more insights.\n2. Repost the first post to share with your network! 🚀",
            ]
        elif content_type == ContentType.HOT_TAKE:
            posts = [
                f"Hot Take 🔥\n\n{subject}.\n\nMost people will disagree, but data and recent trends point directly to this outcome. What do you think?"
            ]
        elif content_type == ContentType.STORY:
            posts = [
                f"How it started vs How it's going: {subject}\n\nWhen we first launched, nobody believed it would scale. By focusing on relentless execution and user feedback, everything changed.\n\nLesson: Focus on building value."
            ]
        elif content_type == ContentType.LONG_FORM:
            posts = [
                f"Deep Dive: {subject}\n\n"
                f"In today's fast-moving environment, staying ahead requires understanding underlying fundamentals rather than chasing surface noise.\n\n"
                f"1. Strategic Positioning\nPositioning determines reach. By aligning your message with high-value audience goals, engagement scales organically.\n\n"
                f"2. Execution Principles\nConsistent output beats sporadic perfection. Maintain an uninterrupted cadence to compound trust.\n\n"
                f"Conclusion: Execution is the differentiator."
            ]
        else:
            posts = [
                f"{subject}.\n\nWhen you align clear execution with strong strategic goals, results follow naturally. Keep building. ⚡"
            ]

        content_item = CreatorContentItem(
            brand_id=brand_id,
            idea_id=idea_id,
            content_type=content_type.value,
            title=subject,
            posts=posts,
            media_urls=[],
            content_pillar=(brand.preferred_topics[0] if brand.preferred_topics else "General"),
            status=ContentStatus.DRAFT.value,
        )
        self.db.add(content_item)

        if idea:
            idea.status = "USED"

        usage = CreatorUsageLog(
            user_id=user_id,
            brand_id=brand_id,
            action_type="GENERATE_CONTENT",
            tokens_used=250,
            details={"content_type": content_type.value, "title": subject},
        )
        self.db.add(usage)

        await self.db.commit()
        await self.db.refresh(content_item)
        return content_item

    # ── Content & Calendar Pipeline ───────────────────────────────────────

    async def get_content_items(
        self,
        brand_id: str,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[CreatorContentItem]:
        brand = await self.get_brand(brand_id, user_id)
        if not brand:
            return []

        stmt = select(CreatorContentItem).where(CreatorContentItem.brand_id == brand_id)
        if status:
            stmt = stmt.where(CreatorContentItem.status == status)

        stmt = stmt.order_by(CreatorContentItem.created_at.desc()).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_content_item(
        self, item_id: str, brand_id: str, user_id: int, data: ContentItemUpdate
    ) -> Optional[CreatorContentItem]:
        brand = await self.get_brand(brand_id, user_id)
        if not brand:
            return None

        stmt = select(CreatorContentItem).where(
            CreatorContentItem.id == item_id, CreatorContentItem.brand_id == brand_id
        )
        res = await self.db.execute(stmt)
        item = res.scalar_one_or_none()
        if not item:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "status" and value:
                setattr(item, field, value.value if isinstance(value, ContentStatus) else value)
            else:
                setattr(item, field, value)

        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def schedule_content_item(
        self, item_id: str, brand_id: str, user_id: int, scheduled_for: datetime
    ) -> Optional[CreatorContentItem]:
        return await self.update_content_item(
            item_id,
            brand_id,
            user_id,
            ContentItemUpdate(scheduled_for=scheduled_for, status=ContentStatus.SCHEDULED),
        )

    # ── X Integration & Publishing ────────────────────────────────────────

    async def connect_x_account(
        self,
        brand_id: str,
        user_id: int,
        x_user_id: str,
        x_handle: str,
        access_token: str,
        refresh_token: Optional[str] = None,
    ) -> XAccountConnection:
        brand = await self.get_brand(brand_id, user_id)
        if not brand:
            raise ValueError("Brand not found")

        stmt = select(XAccountConnection).where(XAccountConnection.brand_id == brand_id)
        res = await self.db.execute(stmt)
        conn = res.scalar_one_or_none()

        if conn:
            conn.x_user_id = x_user_id
            conn.x_handle = x_handle.lstrip("@")
            conn.access_token_encrypted = f"enc:{access_token}"
            conn.refresh_token_encrypted = f"enc:{refresh_token}" if refresh_token else None
            conn.is_connected = True
            conn.token_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        else:
            conn = XAccountConnection(
                brand_id=brand_id,
                x_user_id=x_user_id,
                x_handle=x_handle.lstrip("@"),
                access_token_encrypted=f"enc:{access_token}",
                refresh_token_encrypted=f"enc:{refresh_token}" if refresh_token else None,
                scopes=["tweet.read", "tweet.write", "users.read", "offline.access"],
                is_connected=True,
                token_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
            self.db.add(conn)

        await self.db.commit()
        await self.db.refresh(conn)
        return conn

    async def publish_content_now(self, item_id: str, brand_id: str, user_id: int) -> CreatorContentItem:
        brand = await self.get_brand(brand_id, user_id)
        if not brand:
            raise ValueError("Brand not found")

        stmt = select(CreatorContentItem).where(
            CreatorContentItem.id == item_id, CreatorContentItem.brand_id == brand_id
        )
        res = await self.db.execute(stmt)
        item = res.scalar_one_or_none()
        if not item:
            raise ValueError("Content item not found")

        stmt_conn = select(XAccountConnection).where(
            XAccountConnection.brand_id == brand_id, XAccountConnection.is_connected == True
        )
        res_conn = await self.db.execute(stmt_conn)
        conn = res_conn.scalar_one_or_none()

        # Simulated X API publishing execution
        external_ids = [f"x_post_{random.randint(100000, 999999)}" for _ in item.posts]
        item.external_post_ids = external_ids
        item.status = ContentStatus.PUBLISHED.value
        item.published_at = datetime.now(timezone.utc)

        # Baseline performance metrics seed for analytics tracking
        item.impressions = random.randint(300, 2500)
        item.likes = random.randint(15, 180)
        item.reposts = random.randint(2, 35)
        item.replies = random.randint(1, 20)
        item.clicks = random.randint(5, 60)
        item.engagement_rate = round(
            ((item.likes + item.reposts + item.replies) / max(1, item.impressions)) * 100, 2
        )

        usage = CreatorUsageLog(
            user_id=user_id,
            brand_id=brand_id,
            action_type="PUBLISH_X",
            tokens_used=50,
            details={"item_id": item_id, "external_ids": external_ids},
        )
        self.db.add(usage)

        await self.db.commit()
        await self.db.refresh(item)
        return item

    # ── Growth Analytics & Intelligence ────────────────────────────────────

    async def get_analytics_summary(self, brand_id: str, user_id: int) -> Dict[str, Any]:
        brand = await self.get_brand(brand_id, user_id)
        if not brand:
            return {
                "total_posts_published": 0,
                "total_impressions": 0,
                "total_likes": 0,
                "total_reposts": 0,
                "total_replies": 0,
                "avg_engagement_rate": 0.0,
                "top_pillars": [],
                "performance_growth": [],
            }

        stmt = select(CreatorContentItem).where(
            CreatorContentItem.brand_id == brand_id,
            CreatorContentItem.status == ContentStatus.PUBLISHED.value,
        )
        res = await self.db.execute(stmt)
        items = list(res.scalars().all())

        total_posts = len(items)
        total_impressions = sum(i.impressions for i in items)
        total_likes = sum(i.likes for i in items)
        total_reposts = sum(i.reposts for i in items)
        total_replies = sum(i.replies for i in items)
        avg_engagement = (
            round(sum(i.engagement_rate for i in items) / max(1, total_posts), 2) if total_posts > 0 else 0.0
        )

        # Top pillars aggregation
        pillars_map: Dict[str, int] = {}
        for i in items:
            p = i.content_pillar or "General"
            pillars_map[p] = pillars_map.get(p, 0) + i.impressions

        top_pillars = [
            {"pillar": k, "impressions": v}
            for k, v in sorted(pillars_map.items(), key=lambda x: x[1], reverse=True)
        ]

        # Performance growth over last 7 days mock timeline
        now = datetime.now(timezone.utc)
        performance_growth = [
            {
                "date": (now - timedelta(days=d)).strftime("%Y-%m-%d"),
                "impressions": random.randint(1500, 5000),
                "engagements": random.randint(100, 450),
            }
            for d in range(6, -1, -1)
        ]

        return {
            "total_posts_published": total_posts,
            "total_impressions": total_impressions,
            "total_likes": total_likes,
            "total_reposts": total_reposts,
            "total_replies": total_replies,
            "avg_engagement_rate": avg_engagement,
            "top_pillars": top_pillars,
            "performance_growth": performance_growth,
        }
