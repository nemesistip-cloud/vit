import uuid
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class ContentStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class ContentType(str, Enum):
    SINGLE_POST = "SINGLE_POST"
    LONG_FORM = "LONG_FORM"
    THREAD = "THREAD"
    HOT_TAKE = "HOT_TAKE"
    STORY = "STORY"
    PROMOTIONAL = "PROMOTIONAL"


class CreatorBrand(Base):
    __tablename__ = "creator_brands"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    handle = Column(String(100), nullable=False)
    display_name = Column(String(150), nullable=False)
    niche = Column(String(100), nullable=False, default="Tech & Web3")
    bio = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    tone_and_voice = Column(String(200), nullable=False, default="Professional, Engaging, Analytical")
    writing_style = Column(Text, nullable=True)
    preferred_topics = Column(JSON, default=list) # List[str]
    topics_to_avoid = Column(JSON, default=list)  # List[str]
    vocabulary = Column(JSON, default=dict)        # e.g. {"preferred_words": [...], "banned_words": [...]}
    goals = Column(JSON, default=list)             # e.g. ["Grow followers", "Drive newsletter signups"]
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    brand_memories = relationship("BrandMemory", back_populates="brand", cascade="all, delete-orphan")
    ideas = relationship("CreatorIdea", back_populates="brand", cascade="all, delete-orphan")
    content_items = relationship("CreatorContentItem", back_populates="brand", cascade="all, delete-orphan")
    x_connection = relationship("XAccountConnection", back_populates="brand", uselist=False, cascade="all, delete-orphan")


class BrandMemory(Base):
    __tablename__ = "creator_brand_memories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    brand_id = Column(String(36), ForeignKey("creator_brands.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False, default="THEME") # THEME, OPINION, STYLE_GUIDE, PERFORMANCE_INSIGHT
    key = Column(String(150), nullable=False)
    value = Column(Text, nullable=False)
    weight = Column(Float, default=1.0)
    source = Column(String(100), default="USER_DEFINED") # USER_DEFINED, AI_EXTRACTED, PERFORMANCE_LEARNED

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    brand = relationship("CreatorBrand", back_populates="brand_memories")


class CreatorIdea(Base):
    __tablename__ = "creator_ideas"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    brand_id = Column(String(36), ForeignKey("creator_brands.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    angle = Column(Text, nullable=True)
    hook_templates = Column(JSON, default=list)
    suggested_format = Column(String(50), default="SINGLE_POST")
    pillars = Column(JSON, default=list) # e.g. ["Tech", "Leadership"]
    source = Column(String(100), default="AI_GEN") # AI_GEN, USER_SUBMITTED, TRENDING
    status = Column(String(50), default="NEW") # NEW, IN_PROGRESS, ARCHIVED, USED

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    brand = relationship("CreatorBrand", back_populates="ideas")


class CreatorContentItem(Base):
    __tablename__ = "creator_content_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    brand_id = Column(String(36), ForeignKey("creator_brands.id", ondelete="CASCADE"), nullable=False, index=True)
    idea_id = Column(String(36), ForeignKey("creator_ideas.id", ondelete="SET NULL"), nullable=True)
    content_type = Column(String(50), default=ContentType.SINGLE_POST.value)
    title = Column(String(255), nullable=True)
    posts = Column(JSON, default=list) # List of strings or post dicts representing single post or thread items
    media_urls = Column(JSON, default=list)
    content_pillar = Column(String(100), nullable=True)
    status = Column(String(50), default=ContentStatus.DRAFT.value, index=True)

    # Scheduling details
    scheduled_for = Column(DateTime(timezone=True), nullable=True, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    external_post_ids = Column(JSON, default=list) # X post IDs after publication

    # Performance metrics
    impressions = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    reposts = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    brand = relationship("CreatorBrand", back_populates="content_items")


class XAccountConnection(Base):
    __tablename__ = "creator_x_accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    brand_id = Column(String(36), ForeignKey("creator_brands.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    x_user_id = Column(String(100), nullable=False)
    x_handle = Column(String(100), nullable=False)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=True)
    scopes = Column(JSON, default=list)
    is_connected = Column(Boolean, default=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    brand = relationship("CreatorBrand", back_populates="x_connection")


class CreatorUsageLog(Base):
    __tablename__ = "creator_usage_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_id = Column(String(36), nullable=True, index=True)
    action_type = Column(String(100), nullable=False) # e.g., GENERATE_IDEAS, GENERATE_POST, PUBLISH_X
    tokens_used = Column(Integer, default=0)
    details = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
