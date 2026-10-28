from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.modules.creator_studio.models import ContentStatus, ContentType


class BrandBase(BaseModel):
    handle: str = Field(..., max_length=100)
    display_name: str = Field(..., max_length=150)
    niche: str = Field("Tech & Web3", max_length=100)
    bio: Optional[str] = None
    target_audience: Optional[str] = None
    tone_and_voice: str = Field("Professional, Engaging, Analytical", max_length=200)
    writing_style: Optional[str] = None
    preferred_topics: List[str] = Field(default_factory=list)
    topics_to_avoid: List[str] = Field(default_factory=list)
    vocabulary: Dict[str, Any] = Field(default_factory=dict)
    goals: List[str] = Field(default_factory=list)


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    handle: Optional[str] = None
    display_name: Optional[str] = None
    niche: Optional[str] = None
    bio: Optional[str] = None
    target_audience: Optional[str] = None
    tone_and_voice: Optional[str] = None
    writing_style: Optional[str] = None
    preferred_topics: Optional[List[str]] = None
    topics_to_avoid: Optional[List[str]] = None
    vocabulary: Optional[Dict[str, Any]] = None
    goals: Optional[List[str]] = None
    is_active: Optional[bool] = None


class BrandResponse(BrandBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class BrandMemoryCreate(BaseModel):
    category: str = Field("THEME", max_length=50)
    key: str = Field(..., max_length=150)
    value: str
    weight: float = Field(1.0, ge=0.0, le=5.0)
    source: str = Field("USER_DEFINED", max_length=100)


class BrandMemoryResponse(BrandMemoryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    brand_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class IdeaGenerateRequest(BaseModel):
    brand_id: str
    topic: Optional[str] = None
    count: int = Field(5, ge=1, le=20)


class IdeaCreate(BaseModel):
    title: str
    angle: Optional[str] = None
    hook_templates: List[str] = Field(default_factory=list)
    suggested_format: str = ContentType.SINGLE_POST.value
    pillars: List[str] = Field(default_factory=list)
    source: str = "AI_GEN"


class IdeaResponse(IdeaCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    brand_id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class ContentGenerateRequest(BaseModel):
    brand_id: str
    idea_id: Optional[str] = None
    topic: Optional[str] = None
    content_type: ContentType = ContentType.SINGLE_POST
    instructions: Optional[str] = None
    include_hooks: bool = True


class ContentItemCreate(BaseModel):
    content_type: ContentType = ContentType.SINGLE_POST
    title: Optional[str] = None
    posts: List[str] = Field(..., min_length=1)
    media_urls: List[str] = Field(default_factory=list)
    content_pillar: Optional[str] = None
    scheduled_for: Optional[datetime] = None


class ContentItemUpdate(BaseModel):
    title: Optional[str] = None
    posts: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
    content_pillar: Optional[str] = None
    status: Optional[ContentStatus] = None
    scheduled_for: Optional[datetime] = None


class ContentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    brand_id: str
    idea_id: Optional[str] = None
    content_type: str
    title: Optional[str] = None
    posts: List[str]
    media_urls: List[str]
    content_pillar: Optional[str] = None
    status: str
    scheduled_for: Optional[datetime] = None
    published_at: Optional[datetime] = None
    external_post_ids: List[str] = Field(default_factory=list)
    impressions: int = 0
    likes: int = 0
    reposts: int = 0
    replies: int = 0
    clicks: int = 0
    engagement_rate: float = 0.0
    created_at: datetime
    updated_at: Optional[datetime] = None


class XAccountConnectRequest(BaseModel):
    x_user_id: str
    x_handle: str
    access_token: str
    refresh_token: Optional[str] = None


class XAccountStatusResponse(BaseModel):
    is_connected: bool
    x_handle: Optional[str] = None
    x_user_id: Optional[str] = None
    connected_at: Optional[datetime] = None


class AnalyticsSummaryResponse(BaseModel):
    total_posts_published: int
    total_impressions: int
    total_likes: int
    total_reposts: int
    total_replies: int
    avg_engagement_rate: float
    top_pillars: List[Dict[str, Any]]
    performance_growth: List[Dict[str, Any]]
