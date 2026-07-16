from __future__ import annotations
import logging
from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.passport import PassportService
from app.modules.wallet.services import WalletService
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)

class AIWalletAssistant:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_service = WalletService(db)

    async def get_financial_recommendations(self, user_id: int) -> Dict[str, Any]:
        """
        Analyze user's VIT 2.0 passport and balances to provide personalized
        yield suggestions and security alerts.
        """
        # 1. Gather context
        passport = await PassportService.get_passport(self.db, user_id)
        wallet = await self.wallet_service.get_or_create_wallet(user_id)

        balances = {
            "VIT": float(wallet.vitcoin_balance),
            "Staked_VIT": float(wallet.staked_vitcoin_balance),
            "USD": float(wallet.usd_balance),
            "USDT": float(wallet.usdt_balance),
            "NGN": float(wallet.ngn_balance)
        }

        # 2. Build AI Prompt
        prompt = f"""You are the VIT AI Wallet Assistant.
Analyze the user's financial profile and provide 3 punchy recommendations.

User Profile:
- Trust Score: {passport.trust_score}/100
- Merit Tier: {passport.merit_tier}
- KYC Verified: {passport.is_kyc_verified}

Current Balances:
{balances}

Context:
- Sovereign Tier gets 5.0x governance multiplier.
- Staking VIT yield is currently approx 8% APY.
- Trust Score < 50 triggers manual withdrawal reviews.

Return ONLY a JSON object with:
{{
  "summary": "1-sentence financial health summary",
  "recommendations": [
    {{"title": "Yield Strategy", "description": "e.g. Stake X VIT for Y yield"}},
    {{"title": "Security Alert", "description": "e.g. Unusual pattern or trust score warning"}},
    {{"title": "Merit Growth", "description": "How to reach next tier"}}
  ],
  "projected_monthly_yield_vit": 0.0
}}"""

        # 3. Call VIT Brain (via call_ai)
        try:
            response_text = await call_ai(prompt, max_tokens=512, temperature=0.3)
            if not response_text:
                return self._fallback_recommendation(balances, passport)

            import json
            # Basic cleanup of AI response
            clean_json = response_text.strip()
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0].strip()

            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"AI Assistant failed: {e}")
            return self._fallback_recommendation(balances, passport)

    def _fallback_recommendation(self, balances: dict, passport: Any) -> Dict[str, Any]:
        """Hardcoded rules if AI is unavailable."""
        liquid_vit = balances.get("VIT", 0.0)
        staked_vit = balances.get("Staked_VIT", 0.0)

        recs = []
        if liquid_vit > 100:
            recs.append({
                "title": "Staking Opportunity",
                "description": f"You have {liquid_vit} liquid VIT. Stake 50% to earn ~8% APY."
            })

        if passport.trust_score < 60:
            recs.append({
                "title": "Security Status",
                "description": "Your Trust Score is below average. Complete more predictions to improve limits."
            })
        else:
            recs.append({
                "title": "Account Secure",
                "description": "High Trust Score detected. You qualify for instant withdrawals."
            })

        recs.append({
            "title": "Merit Progress",
            "description": f"Currently in {passport.merit_tier} tier. Participate in governance to earn XP."
        })

        return {
            "summary": "Stable financial standing with growth potential.",
            "recommendations": recs[:3],
            "projected_monthly_yield_vit": round((staked_vit * 0.08) / 12, 2)
        }
