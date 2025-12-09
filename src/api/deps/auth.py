"""Authentication dependency providers."""

from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from ...core.config import get_settings

# API key header security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(api_key_header)
) -> str:
    """
    Verify API key from request header.

    For MVP, this does simple string comparison against SECRET_KEY.
    In production, this should:
    - Look up keys in database
    - Support multiple keys with different permissions
    - Track key usage and rate limits
    - Support key rotation

    Args:
        api_key: API key from X-API-Key header

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is missing or invalid

    Usage:
        @router.get("/endpoint")
        async def endpoint(api_key: str = Depends(verify_api_key)):
            ...
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    settings = get_settings()

    # MVP: Simple comparison with SECRET_KEY
    # Production: Database lookup with hashed keys
    if api_key != settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


# Type alias for cleaner dependency injection
APIKeyDep = Annotated[str, Security(verify_api_key)]
