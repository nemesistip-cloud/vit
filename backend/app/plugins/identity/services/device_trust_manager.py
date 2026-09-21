import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.plugins.identity.models import TrustedDevice, GlobalIdentity
from app.core.event_bus import event_bus

logger = logging.getLogger(__name__)

class DeviceTrustManager:
    """Enterprise Device Trust and Risk Management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_device(self,
                              identity: GlobalIdentity,
                              device_id: str,
                              platform: Optional[str] = None,
                              browser: Optional[str] = None,
                              ip_address: Optional[str] = None) -> TrustedDevice:
        """Register or update a device for an identity."""

        result = await self.session.execute(
            select(TrustedDevice).where(
                TrustedDevice.identity_id == identity.id,
                TrustedDevice.device_id == device_id
            )
        )
        device = result.scalar_one_or_none()

        if not device:
            device = TrustedDevice(
                identity_id=identity.id,
                device_id=device_id,
                platform=platform,
                browser=browser,
                last_ip=ip_address,
                is_trusted=False,
                risk_score=50 # Default moderate risk for new devices
            )
            self.session.add(device)

            await event_bus.publish("DeviceRegistered", {
                "gid": identity.gid,
                "device_id": device_id
            }, sender="device_trust_manager")
        else:
            device.last_active = datetime.now(timezone.utc)
            device.last_ip = ip_address
            if platform: device.platform = platform
            if browser: device.browser = browser

        await self.session.commit()
        await self.session.refresh(device)
        return device

    async def trust_device(self, identity_id: int, device_id: str):
        result = await self.session.execute(
            select(TrustedDevice).where(
                TrustedDevice.identity_id == identity_id,
                TrustedDevice.device_id == device_id
            )
        )
        device = result.scalar_one_or_none()
        if device:
            device.is_trusted = True
            device.risk_score = 0
            await self.session.commit()

            await event_bus.publish("DeviceTrusted", {
                "device_id": device_id
            }, sender="device_trust_manager")

    async def get_device_risk_score(self, identity_id: int, device_id: str) -> int:
        result = await self.session.execute(
            select(TrustedDevice).where(
                TrustedDevice.identity_id == identity_id,
                TrustedDevice.device_id == device_id
            )
        )
        device = result.scalar_one_or_none()
        return device.risk_score if device else 100 # Unknown device is high risk
