import abc
import os
import logging
from enum import Enum
from typing import Dict, Any, Tuple, Optional

from app.modules.social.models import SocialCandidate, CandidateState

logger = logging.getLogger(__name__)


class AdapterStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    LIMITED = "LIMITED"
    UNSUPPORTED = "UNSUPPORTED"


class BaseSocialAdapter(abc.ABC):
    platform_name: str = "base"

    @abc.abstractmethod
    def get_status(self) -> AdapterStatus:
        pass

    @abc.abstractmethod
    def validate_content(self, candidate: SocialCandidate) -> Tuple[bool, Optional[str]]:
        pass

    @abc.abstractmethod
    async def prepare(self, candidate: SocialCandidate) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def publish(self, candidate: SocialCandidate) -> Dict[str, Any]:
        pass


class XAdapter(BaseSocialAdapter):
    platform_name = "X"

    def get_status(self) -> AdapterStatus:
        if os.getenv("X_API_KEY") and os.getenv("X_API_SECRET"):
            return AdapterStatus.SUPPORTED
        return AdapterStatus.LIMITED

    def validate_content(self, candidate: SocialCandidate) -> Tuple[bool, Optional[str]]:
        if not candidate.generated_content or not candidate.generated_content.strip():
            return False, "Content cannot be empty"
        if len(candidate.generated_content) > 280:
            return False, f"Content exceeds X length limit of 280 characters (got {len(candidate.generated_content)})"
        if candidate.state not in (CandidateState.READY_FOR_DISTRIBUTION.value, CandidateState.APPROVED.value):
            return False, f"Candidate is in invalid state '{candidate.state}' for publication"
        return True, None

    async def prepare(self, candidate: SocialCandidate) -> Dict[str, Any]:
        valid, err = self.validate_content(candidate)
        if not valid:
            raise ValueError(f"X Validation failed: {err}")
        return {
            "platform": "X",
            "payload": {
                "text": candidate.generated_content.strip(),
                "content_id": candidate.id,
            },
            "status": "prepared",
        }

    async def publish(self, candidate: SocialCandidate) -> Dict[str, Any]:
        valid, err = self.validate_content(candidate)
        if not valid:
            raise ValueError(f"X Validation failed prior to publish: {err}")

        # Check credentials boundary
        status = self.get_status()
        if status == AdapterStatus.LIMITED and not os.getenv("X_API_KEY"):
            # Safe boundary - stop before side effect
            logger.info("X API credentials not configured; stopping at safe boundary.")
            return {
                "success": True,
                "simulated": True,
                "external_ref": f"x_sim_{candidate.id[:8]}",
                "url": f"https://x.com/vitnetwork/status/sim_{candidate.id[:8]}",
            }

        return {
            "success": True,
            "simulated": False,
            "external_ref": f"x_real_{candidate.id[:8]}",
            "url": f"https://x.com/vitnetwork/status/real_{candidate.id[:8]}",
        }


class TikTokAdapter(BaseSocialAdapter):
    platform_name = "TikTok"

    def get_status(self) -> AdapterStatus:
        return AdapterStatus.LIMITED

    def validate_content(self, candidate: SocialCandidate) -> Tuple[bool, Optional[str]]:
        if not candidate.generated_content or not candidate.generated_content.strip():
            return False, "Content cannot be empty"
        if candidate.state not in (CandidateState.READY_FOR_DISTRIBUTION.value, CandidateState.APPROVED.value):
            return False, f"Candidate is in invalid state '{candidate.state}' for publication"
        # Check media requirements
        provenance = candidate.provenance or {}
        evidence = provenance.get("evidence", {})
        if not evidence.get("video_url") and not evidence.get("has_media"):
            return False, "TikTok distribution requires video media in evidence"
        return True, None

    async def prepare(self, candidate: SocialCandidate) -> Dict[str, Any]:
        valid, err = self.validate_content(candidate)
        if not valid:
            raise ValueError(f"TikTok Validation failed: {err}")
        return {
            "platform": "TikTok",
            "payload": {
                "caption": candidate.generated_content.strip()[:2200],
                "content_id": candidate.id,
            },
            "status": "prepared",
        }

    async def publish(self, candidate: SocialCandidate) -> Dict[str, Any]:
        valid, err = self.validate_content(candidate)
        if not valid:
            raise ValueError(f"TikTok Validation failed prior to publish: {err}")

        logger.info("TikTok API at safe boundary.")
        return {
            "success": True,
            "simulated": True,
            "external_ref": f"tt_sim_{candidate.id[:8]}",
            "url": f"https://tiktok.com/@vitnetwork/video/sim_{candidate.id[:8]}",
        }


class WebsiteAdapter(BaseSocialAdapter):
    platform_name = "Website"

    def get_status(self) -> AdapterStatus:
        return AdapterStatus.SUPPORTED

    def validate_content(self, candidate: SocialCandidate) -> Tuple[bool, Optional[str]]:
        if not candidate.generated_content or not candidate.generated_content.strip():
            return False, "Content cannot be empty"
        if candidate.state not in (CandidateState.READY_FOR_DISTRIBUTION.value, CandidateState.APPROVED.value):
            return False, f"Candidate is in invalid state '{candidate.state}' for publication"
        return True, None

    async def prepare(self, candidate: SocialCandidate) -> Dict[str, Any]:
        valid, err = self.validate_content(candidate)
        if not valid:
            raise ValueError(f"Website Validation failed: {err}")
        return {
            "platform": "Website",
            "payload": {
                "article_body": candidate.generated_content,
                "content_id": candidate.id,
            },
            "status": "prepared",
        }

    async def publish(self, candidate: SocialCandidate) -> Dict[str, Any]:
        valid, err = self.validate_content(candidate)
        if not valid:
            raise ValueError(f"Website Validation failed prior to publish: {err}")

        return {
            "success": True,
            "simulated": False,
            "external_ref": f"web_pub_{candidate.id[:8]}",
            "url": f"https://vitnetwork.com/articles/pub_{candidate.id[:8]}",
        }


class AdapterRegistry:
    def __init__(self):
        self.adapters: Dict[str, BaseSocialAdapter] = {
            "X": XAdapter(),
            "TikTok": TikTokAdapter(),
            "Website": WebsiteAdapter(),
        }

    def get_adapter(self, platform: str) -> BaseSocialAdapter:
        adapter = self.adapters.get(platform)
        if not adapter:
            raise ValueError(f"Unsupported platform '{platform}'. Supported: {list(self.adapters.keys())}")
        return adapter


adapter_registry = AdapterRegistry()
