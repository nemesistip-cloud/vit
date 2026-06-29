class VITSDKError(Exception):
    """Base exception class for the VIT Network SDK."""
    pass

class VITAPIError(VITSDKError):
    """Raised when the VIT API returns an error."""
    def __init__(self, message: str, status_code: int = None, response: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class VITRPCError(VITSDKError):
    """Raised when the VIT Chain RPC returns an error."""
    pass

class VITAuthError(VITSDKError):
    """Raised for authentication or authorization failures."""
    pass
