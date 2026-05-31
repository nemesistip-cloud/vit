from abc import ABC, abstractmethod

class CloudProvider(ABC):
    """
    Base class for Multi-Provider API Normalizer.
    """

    @abstractmethod
    async def upload_fragment(self, data: bytes, name: str) -> bool:
        pass

    @abstractmethod
    async def download_fragment(self, name: str) -> bytes:
        pass

    @abstractmethod
    async def get_quota(self) -> dict:
        pass

    @abstractmethod
    async def get_latency(self) -> float:
        pass
