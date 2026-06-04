from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from typing import Optional

from app.db.database import get_db
from app.db.models import Match
from app.modules.sports.models import MarketMapping, AffiliateClick
from app.services.affiliate_service import AffiliateService
from app.api.deps import get_optional_user
from starlette.requests import Request

router = APIRouter(prefix="/predictions", tags=["affiliate"])
logger = logging.getLogger(__name__)

@router.get("/generate-slip")
async def generate_betting_slip(
    request: Request,
    match_id: int = Query(...),
    provider: str = Query("betway", description="Bookmaker provider: betway, sportybet, bet9ja"),
    market: str = Query("1x2"),
    selection: str = Query("home"),
    utm_source: str = Query("vit_app"),
    utm_medium: str = Query("app"),
    utm_campaign: str = Query("prediction_redirect"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_optional_user)
):
    """
    Generates an affiliate deep-link for a given match and prediction selection.
    """
    # 1. Internal Market Lookup
    stmt = select(Match).where(Match.id == match_id)
    match = (await db.execute(stmt)).scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # 2. Market Mapping Lookup
    # This assumes we have previously synced and stored mappings for the provider
    mapping_stmt = select(MarketMapping).where(
        MarketMapping.match_id == match_id,
        MarketMapping.provider_name == provider.lower(),
        MarketMapping.market_type == market,
        MarketMapping.selection_name == selection
    )
    mapping = (await db.execute(mapping_stmt)).scalar_one_or_none()

    # Fallback to external_id if mapping not found (best effort)
    ext_match_id = mapping.external_match_id if mapping else match.external_id
    ext_selection_id = mapping.external_selection_id if mapping else selection

    # 3. Affiliate URL Generation
    url = AffiliateService.generate_deep_link(
        provider=provider,
        match_id=ext_match_id or "unknown",
        selection_id=ext_selection_id,
        utm_source=utm_source
    )

    if not url:
        raise HTTPException(status_code=400, detail=f"Unsupported bookmaker: {provider}")

    # 4. Analytics Tracking
    click = AffiliateClick(
        user_id=current_user.id if current_user else None,
        match_id=match_id,
        provider_name=provider,
        market_type=market,
        selection_name=selection,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent")
    )
    db.add(click)
    await db.commit()

    return {
        "match": f"{match.home_team} vs {match.away_team}",
        "redirect_url": url,
        "provider": provider,
        "market": market,
        "selection": selection
    }
