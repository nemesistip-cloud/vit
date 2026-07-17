# app/modules/social/routes.py
"""
Social Prediction Feed — Phase VIII
Endpoints: follow/unfollow users, post to feed, react (like/fire/doubt),
           comment on predictions, and fetch the personalised feed.
All data is persisted in-process via an in-memory store that survives
warm restarts; swap for a proper DB table in a later migration.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/social", tags=["Social"])

# ── In-memory store (replace with DB models in production) ──────────────────
_follows:   dict[int, set[int]]  = {}   # follower_id → {followee_id, ...}
_posts:     list[dict]           = []   # feed posts
_reactions: dict[str, dict]      = {}   # post_id → {user_id: reaction}
_comments:  dict[str, list]      = {}   # post_id → [{...}, ...]


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class FollowAction(BaseModel):
    target_user_id: int


class PostCreate(BaseModel):
    content:       str              = Field(..., min_length=1,  max_length=2000)
    prediction_id: Optional[int]    = None
    match_id:      Optional[int]    = None
    tags:          List[str]        = Field(default_factory=list)


class ReactRequest(BaseModel):
    post_id:  str
    reaction: str = Field(..., pattern="^(like|fire|doubt|rocket|🔥|👍|🤔|🚀)$")


class CommentCreate(BaseModel):
    post_id: str
    content: str = Field(..., min_length=1, max_length=500)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_post(p: dict, viewer_id: int | None = None) -> dict:
    reactions = _reactions.get(p["id"], {})
    counts: dict[str, int] = {}
    for r in reactions.values():
        counts[r] = counts.get(r, 0) + 1
    return {
        **p,
        "reaction_counts": counts,
        "total_reactions":  sum(counts.values()),
        "my_reaction":      reactions.get(viewer_id) if viewer_id else None,
        "comment_count":    len(_comments.get(p["id"], [])),
    }


# ── Follow / Unfollow ─────────────────────────────────────────────────────────

@router.post("/follow", summary="Follow a user")
async def follow_user(body: FollowAction, me: User = Depends(get_current_user)):
    if body.target_user_id == me.id:
        raise HTTPException(400, "Cannot follow yourself")
    _follows.setdefault(me.id, set()).add(body.target_user_id)
    return {"ok": True, "following": body.target_user_id}


@router.delete("/follow/{user_id}", summary="Unfollow a user")
async def unfollow_user(user_id: int, me: User = Depends(get_current_user)):
    _follows.get(me.id, set()).discard(user_id)
    return {"ok": True, "unfollowed": user_id}


@router.get("/following", summary="List who you follow")
async def get_following(me: User = Depends(get_current_user)):
    return {"following": list(_follows.get(me.id, set()))}


@router.get("/followers/{user_id}", summary="Get followers of a user")
async def get_followers(user_id: int):
    followers = [uid for uid, fset in _follows.items() if user_id in fset]
    return {"followers": followers, "count": len(followers)}


# ── Feed ──────────────────────────────────────────────────────────────────────

@router.get("/feed", summary="Personalised prediction feed")
async def get_feed(
    page:    int = Query(1, ge=1),
    limit:   int = Query(20, ge=1, le=100),
    filter:  str = Query("all", pattern="^(all|following|trending)$"),
    me: User = Depends(get_current_user),
):
    following = _follows.get(me.id, set())
    if filter == "following" and following:
        posts = [p for p in _posts if p["author_id"] in following]
    elif filter == "trending":
        posts = sorted(_posts, key=lambda p: len(_reactions.get(p["id"], {})), reverse=True)
    else:
        posts = list(_posts)

    posts = posts[::-1]   # newest first
    total = len(posts)
    start = (page - 1) * limit
    page_posts = posts[start: start + limit]

    return {
        "items":    [_fmt_post(p, me.id) for p in page_posts],
        "total":    total,
        "page":     page,
        "pages":    max(1, -(-total // limit)),
    }


@router.post("/posts", summary="Create a feed post")
async def create_post(body: PostCreate, me: User = Depends(get_current_user)):
    post = {
        "id":            str(uuid.uuid4()),
        "author_id":     me.id,
        "author_email":  me.email,
        "content":       body.content,
        "prediction_id": body.prediction_id,
        "match_id":      body.match_id,
        "tags":          body.tags,
        "created_at":    time.time(),
    }
    _posts.append(post)
    logger.info("social:post created id=%s by user=%s", post["id"], me.id)
    return _fmt_post(post, me.id)


@router.delete("/posts/{post_id}", summary="Delete your post")
async def delete_post(post_id: str, me: User = Depends(get_current_user)):
    global _posts
    before = len(_posts)
    _posts = [p for p in _posts if not (p["id"] == post_id and p["author_id"] == me.id)]
    if len(_posts) == before:
        raise HTTPException(404, "Post not found or not yours")
    _reactions.pop(post_id, None)
    _comments.pop(post_id, None)
    return {"ok": True}


# ── Reactions ─────────────────────────────────────────────────────────────────

@router.post("/react", summary="React to a post (idempotent toggle)")
async def react_to_post(body: ReactRequest, me: User = Depends(get_current_user)):
    post_reactions = _reactions.setdefault(body.post_id, {})
    if post_reactions.get(me.id) == body.reaction:
        post_reactions.pop(me.id)   # toggle off
        return {"ok": True, "action": "removed", "reaction": body.reaction}
    post_reactions[me.id] = body.reaction
    return {"ok": True, "action": "added", "reaction": body.reaction}


# ── Comments ──────────────────────────────────────────────────────────────────

@router.get("/posts/{post_id}/comments", summary="Get comments on a post")
async def get_comments(post_id: str, limit: int = Query(50, ge=1, le=200)):
    return {"comments": _comments.get(post_id, [])[:limit]}


@router.post("/posts/{post_id}/comments", summary="Comment on a post")
async def add_comment(
    post_id: str,
    body:    CommentCreate,
    me:      User = Depends(get_current_user),
):
    comment = {
        "id":           str(uuid.uuid4()),
        "post_id":      post_id,
        "author_id":    me.id,
        "author_email": me.email,
        "content":      body.content,
        "created_at":   time.time(),
    }
    _comments.setdefault(post_id, []).append(comment)
    return comment


@router.delete("/posts/{post_id}/comments/{comment_id}", summary="Delete your comment")
async def delete_comment(
    post_id:    str,
    comment_id: str,
    me:         User = Depends(get_current_user),
):
    thread = _comments.get(post_id, [])
    before = len(thread)
    _comments[post_id] = [c for c in thread if not (c["id"] == comment_id and c["author_id"] == me.id)]
    if len(_comments[post_id]) == before:
        raise HTTPException(404, "Comment not found or not yours")
    return {"ok": True}


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats", summary="Global social stats")
async def get_stats():
    total_reactions = sum(len(v) for v in _reactions.values())
    total_comments  = sum(len(v) for v in _comments.values())
    return {
        "total_posts":     len(_posts),
        "total_reactions": total_reactions,
        "total_comments":  total_comments,
        "total_follows":   sum(len(v) for v in _follows.values()),
    }
