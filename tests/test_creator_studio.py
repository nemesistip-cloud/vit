import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.modules.creator_studio.models import CreatorBrand, ContentType, ContentStatus
from app.modules.creator_studio.schemas import (
    BrandCreate,
    BrandUpdate,
    BrandMemoryCreate,
    ContentItemUpdate,
)
from app.modules.creator_studio.service import CreatorStudioService


@pytest.mark.asyncio
async def test_creator_studio_brand_lifecycle():
    mock_db = AsyncMock()
    service = CreatorStudioService(mock_db)

    brand_data = BrandCreate(
        handle="@anselemcrizyx",
        display_name="Anselem Crizyx",
        niche="AI & Web3",
        bio="Building autonomous creator tools",
        tone_and_voice="Authoritative & Direct",
        preferred_topics=["AI Agents", "Solana", "VIT Network"],
        topics_to_avoid=["Low effort crypto shills"],
        goals=["Reach 50k followers", "Drive newsletter subscriptions"],
    )

    brand = await service.create_brand(user_id=1, data=brand_data)
    assert brand.handle == "anselemcrizyx"
    assert brand.display_name == "Anselem Crizyx"
    assert brand.user_id == 1
    assert mock_db.add.called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_generate_ideas_and_content():
    mock_db = AsyncMock()
    service = CreatorStudioService(mock_db)

    # Mock brand retrieval
    mock_brand = CreatorBrand(
        id="brand-123",
        user_id=1,
        handle="testcreator",
        display_name="Test Creator",
        niche="Tech",
        target_audience="Developers",
        tone_and_voice="Professional",
        preferred_topics=["AI", "Startups"],
    )
    service.get_brand = AsyncMock(return_value=mock_brand)
    service.get_memories = AsyncMock(return_value=[])

    ideas = await service.generate_ideas(brand_id="brand-123", user_id=1, count=3)
    assert len(ideas) == 3

    content_item = await service.generate_content(
        brand_id="brand-123",
        user_id=1,
        content_type=ContentType.THREAD,
        topic="Future of AI Agents",
    )
    assert content_item.content_type == ContentType.THREAD.value
    assert len(content_item.posts) > 1
    assert "🧵" in content_item.posts[0]
