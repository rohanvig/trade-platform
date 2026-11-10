class DeribitAdapterError(Exception):
    """Base exception for all Deribit adapter errors."""

    pass


class DeribitRateLimitError(DeribitAdapterError):
    """Raised when Deribit rate limits are exceeded and retries are exhausted (HTTP 429 / 503)."""

    pass


class DeribitTimeoutError(DeribitAdapterError):
    """Raised when an upstream request to Deribit times out."""

    pass


class DeribitDataError(DeribitAdapterError):
    """Raised when an upstream response is malformed, missing fields, or invalid."""

    pass


class UnsupportedAssetError(DeribitAdapterError):
    """Raised when an unsupported underlying asset is requested (only BTC and ETH supported)."""

    pass

