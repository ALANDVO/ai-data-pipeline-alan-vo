"""OIDC/Keycloak token validation with issuer and audience verification."""
import logging
import httpx
from typing import Optional, Dict, Any
from functools import lru_cache
from jose import JWTError, jwt
from jose.utils import base64url_decode
import time

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Cache for JWKS keys
_jwks_cache: Optional[Dict[str, Any]] = None
_jwks_cache_time: float = 0
_JWKS_TTL = 3600  # 1 hour


async def fetch_jwks() -> Dict[str, Any]:
    """Fetch JWKS from Keycloak issuer."""
    global _jwks_cache, _jwks_cache_time
    now = time.time()
    if _jwks_cache and (now - _jwks_cache_time) < _JWKS_TTL:
        return _jwks_cache

    jwks_url = f"{settings.oidc_issuer_url}/protocol/openid-connect/certs"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_cache_time = now
            logger.info("Fetched JWKS from %s", jwks_url)
            return _jwks_cache
    except Exception as e:
        logger.error("Failed to fetch JWKS: %s", e)
        if _jwks_cache:
            return _jwks_cache
        raise


def get_signing_key(jwks: Dict[str, Any], kid: str) -> Optional[Dict[str, Any]]:
    """Extract signing key from JWKS by key ID."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


async def validate_oidc_token(token: str) -> Dict[str, Any]:
    """
    Validate OIDC token from Keycloak.
    Verifies signature, issuer, audience, and expiration.
    """
    try:
        # Get unverified header to find key ID
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise JWTError("Token missing key ID (kid)")

        # Fetch JWKS and get signing key
        jwks = await fetch_jwks()
        key = get_signing_key(jwks, kid)
        if not key:
            raise JWTError(f"Signing key not found for kid: {kid}")

        # Decode and verify token
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.oidc_client_id,
            issuer=settings.oidc_issuer_url,
            options={"verify_aud": True, "verify_iss": True, "verify_exp": True},
        )

        logger.debug("OIDC token validated for subject: %s", payload.get("sub"))
        return payload

    except JWTError as e:
        logger.warning("OIDC token validation failed: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error validating OIDC token: %s", e)
        raise JWTError(f"Token validation error: {e}")


async def get_userinfo(access_token: str) -> Dict[str, Any]:
    """Fetch user info from Keycloak userinfo endpoint."""
    userinfo_url = f"{settings.oidc_issuer_url}/protocol/openid-connect/userinfo"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("Failed to fetch userinfo: %s", e)
        return {}


@lru_cache(maxsize=1)
def get_oidc_config() -> Dict[str, Any]:
    """Get OIDC discovery configuration (cached)."""
    config_url = f"{settings.oidc_issuer_url}/.well-known/openid-configuration"
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(config_url)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Failed to fetch OIDC config: %s", e)
        return {}


def build_logout_url(id_token_hint: Optional[str] = None, post_logout_redirect_uri: Optional[str] = None) -> str:
    """Build Keycloak logout URL."""
    base = f"{settings.oidc_issuer_url}/protocol/openid-connect/logout"
    params = []
    if id_token_hint:
        params.append(f"id_token_hint={id_token_hint}")
    if post_logout_redirect_uri:
        params.append(f"post_logout_redirect_uri={post_logout_redirect_uri}")
    if params:
        return f"{base}?{'&'.join(params)}"
    return base
