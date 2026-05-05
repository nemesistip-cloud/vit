import hashlib
import hmac
import json
import os
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.modules.rewards.models import OfferCompletion, PostbackAuditLog
from app.modules.wallet.services import WalletService


class RewardService:
    """Reward event and postback handling service."""

    # Provider-specific payload parsers
    PROVIDER_PARSERS = {
        "ayet_studios": "_parse_ayet_studios_payload",
        "tapjoy": "_parse_tapjoy_payload", 
        "revu": "_parse_revu_payload",
        "bitlabs": "_parse_bitlabs_payload",
        "cpx_research": "_parse_cpx_research_payload",
    }

    @staticmethod
    def _parse_ayet_studios_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Ayet Studios postback payload."""
        return {
            "user_id": payload.get("user_id") or payload.get("uid"),
            "amount": payload.get("amount") or payload.get("reward"),
            "currency": payload.get("currency", "VITCoin"),
            "provider_offer_id": payload.get("offer_id") or payload.get("campaign_id"),
            "provider_event_id": payload.get("event_id") or payload.get("transaction_id"),
            "reward_type": payload.get("reward_type", "offer"),
            "reward_margin": payload.get("margin", 0.30),
            "raw_payload": payload,
        }

    @staticmethod
    def _parse_tapjoy_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Tapjoy postback payload."""
        return {
            "user_id": payload.get("user_id") or payload.get("snuid"),
            "amount": payload.get("amount") or payload.get("currency_amount"),
            "currency": payload.get("currency_name", "VITCoin"),
            "provider_offer_id": payload.get("campaign_id") or payload.get("offer_id"),
            "provider_event_id": payload.get("click_id") or payload.get("transaction_id"),
            "reward_type": payload.get("reward_type", "offer"),
            "reward_margin": payload.get("margin", 0.30),
            "raw_payload": payload,
        }

    @staticmethod
    def _parse_revu_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse RevU postback payload."""
        return {
            "user_id": payload.get("user_id") or payload.get("userId"),
            "amount": payload.get("amount") or payload.get("reward_amount"),
            "currency": payload.get("currency", "VITCoin"),
            "provider_offer_id": payload.get("offer_id") or payload.get("campaignId"),
            "provider_event_id": payload.get("event_id") or payload.get("transactionId"),
            "reward_type": payload.get("reward_type", "offer"),
            "reward_margin": payload.get("margin", 0.30),
            "raw_payload": payload,
        }

    @staticmethod
    def _parse_bitlabs_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse BitLabs postback payload."""
        return {
            "user_id": payload.get("user_id") or payload.get("userid"),
            "amount": payload.get("amount") or payload.get("reward"),
            "currency": payload.get("currency", "VITCoin"),
            "provider_offer_id": payload.get("offer_id") or payload.get("campaign_id"),
            "provider_event_id": payload.get("event_id") or payload.get("transaction_id"),
            "reward_type": payload.get("reward_type", "survey"),
            "reward_margin": payload.get("margin", 0.30),
            "raw_payload": payload,
        }

    @staticmethod
    def _parse_cpx_research_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse CPX Research postback payload."""
        return {
            "user_id": payload.get("user_id") or payload.get("userId"),
            "amount": payload.get("amount") or payload.get("reward_amount"),
            "currency": payload.get("currency", "VITCoin"),
            "provider_offer_id": payload.get("offer_id") or payload.get("survey_id"),
            "provider_event_id": payload.get("event_id") or payload.get("transaction_id"),
            "reward_type": payload.get("reward_type", "survey"),
            "reward_margin": payload.get("margin", 0.30),
            "raw_payload": payload,
        }

    @staticmethod
    def _parse_provider_payload(provider: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse payload using provider-specific parser or fallback to generic."""
        parser_method = RewardService.PROVIDER_PARSERS.get(provider.lower())
        if parser_method:
            return getattr(RewardService, parser_method)(payload)
        
        # Fallback to generic parsing
        return {
            "user_id": payload.get("user_id"),
            "amount": payload.get("amount") or payload.get("reward"),
            "currency": payload.get("currency", "VITCoin"),
            "provider_offer_id": payload.get("provider_offer_id") or payload.get("offer_id"),
            "provider_event_id": payload.get("provider_event_id") or payload.get("event_id"),
            "reward_type": payload.get("reward_type", "offer"),
            "reward_margin": payload.get("reward_margin", 0.30),
            "raw_payload": payload,
        }

    @staticmethod
    def _canonical_payload_hash(payload: Dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _signature_header(provider: str) -> str:
        return os.getenv(f"POSTBACK_SIGNATURE_HEADER_{provider.upper()}", "X-Signature")

    @staticmethod
    def _provider_secret(provider: str) -> Optional[str]:
        return os.getenv(f"POSTBACK_SECRET_{provider.upper()}")

    @staticmethod
    def _validate_signature(provider: str, signature: Optional[str], body: bytes) -> Dict[str, Any]:
        secret = RewardService._provider_secret(provider)
        if not secret:
            return {"valid": False, "reason": "missing_secret"}

        if not signature:
            return {"valid": False, "reason": "missing_signature"}

        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, signature):
            return {"valid": True, "method": "hmac_sha256"}

        return {"valid": False, "reason": "signature_mismatch", "expected": expected}

    @staticmethod
    async def _ensure_user(db: AsyncSession, payload: Dict[str, Any]) -> User:
        user_id = payload.get("user_id")
        if not user_id:
            raise ValueError("Missing required user_id in postback payload")

        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found for provided user_id")
        return user

    @staticmethod
    async def process_postback(
        db: AsyncSession,
        provider: str,
        body: bytes,
        headers: Dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> OfferCompletion:
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON payload: {exc}")

        payload_hash = RewardService._canonical_payload_hash(payload)
        signature_header = RewardService._signature_header(provider)
        signature = headers.get(signature_header) or headers.get(signature_header.lower())

        audit_log = PostbackAuditLog(
            provider=provider,
            ip_address=ip_address,
            headers=headers,
            payload=payload,
            payload_hash=payload_hash,
            signature=signature,
            validation_status="pending",
        )
        db.add(audit_log)
        await db.flush()

        existing = await db.execute(
            select(OfferCompletion)
            .where(OfferCompletion.provider == provider)
            .where(OfferCompletion.provider_payload_hash == payload_hash)
        )
        existing_event = existing.scalar_one_or_none()
        if existing_event:
            audit_log.offer_completion_id = existing_event.id
            audit_log.validation_status = "duplicate"
            audit_log.validation_details = {"status": existing_event.status}
            await db.commit()
            await db.refresh(existing_event)
            return existing_event

        validation = RewardService._validate_signature(provider, signature, body)
        audit_log.validation_status = "passed" if validation["valid"] else "failed"
        audit_log.validation_details = validation

        if not validation["valid"]:
            audit_log.error_message = validation.get("reason")
            await db.commit()
            raise ValueError(f"Postback validation failed: {validation.get('reason')}")

        # Parse provider-specific payload
        parsed_data = RewardService._parse_provider_payload(provider, payload)
        
        user = await RewardService._ensure_user(db, parsed_data)
        amount = Decimal(str(parsed_data["amount"]))
        if amount <= 0:
            raise ValueError("Reward amount must be greater than zero")

        currency = parsed_data["currency"]
        provider_offer_id = parsed_data["provider_offer_id"]
        provider_event_id = parsed_data["provider_event_id"]
        reward_type = parsed_data["reward_type"]
        reward_margin = parsed_data["reward_margin"]

        event = OfferCompletion(
            user_id=user.id,
            provider=provider,
            provider_offer_id=provider_offer_id,
            provider_event_id=provider_event_id,
            status="pending",
            amount=amount,
            currency=currency,
            reward_type=reward_type,
            reward_margin=reward_margin,
            provider_payload=parsed_data["raw_payload"],  # Store original payload
            provider_payload_hash=payload_hash,
            provider_signature=signature,
            event_metadata={
                "validated_by": "postback_api",
                "signature_header": signature_header,
                "parsed_data": parsed_data,  # Store parsed data for reference
            },
        )
        db.add(event)
        await db.flush()

        audit_log.offer_completion_id = event.id
        await db.flush()

        try:
            wallet_service = WalletService(db)
            tx = await wallet_service.deposit_vitcoin(
                user_id=user.id,
                amount=amount,
                description=f"Reward from {provider}",
                tx_type="reward",
                metadata={
                    "offer_completion_id": event.id,
                    "provider": provider,
                    "provider_event_id": provider_event_id,
                },
            )
            event.wallet_tx_id = tx.id
            event.status = "paid"
        except Exception as exc:
            event.status = "failed"
            event.event_metadata["credit_error"] = str(exc)
            audit_log.error_message = str(exc)

        await db.commit()
        await db.refresh(event)
        return event
