"""Authentication with OIDC/Keycloak token validation and local JWT fallback."""
import logging
import time
import uuid
import hashlib
from typing import Optional
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.api.oidc import validate_oidc_token, get_userinfo

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


class User(BaseModel):
    email: str
    name: str = ""
    role: str = "data_engineer"


class APIKey(BaseModel):
    id: str
    label: str
    key_prefix: str
    created_at: float
    last_used: Optional[float] = None


# In-memory API key store (production would use a database)
_api_keys: dict = {}


def create_jwt(user: dict) -> str:
    """Create local JWT token (for service-to-service or fallback)."""
    payload = {
        "sub": user.get("email", "unknown"),
        "name": user.get("name", ""),
        "role": user.get("role", "data_engineer"),
        "exp": time.time() + settings.jwt_expiry_minutes * 60,
        "iat": time.time(),
        "iss": "ai-data-pipeline-local",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_local_jwt(token: str) -> dict:
    """Verify locally-issued JWT token."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], issuer="ai-data-pipeline-local")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired local token")


async def verify_token(token: str) -> dict:
    """
    Verify token - tries OIDC validation first, falls back to local JWT.
    Returns the token payload.
    """
    # Try OIDC validation first (Keycloak-issued tokens are RS256)
    try:
        return await validate_oidc_token(token)
    except JWTError:
        pass

    # Fall back to local JWT validation (HS256)
    try:
        return verify_local_jwt(token)
    except JWTError:
        pass

    raise HTTPException(status_code=401, detail="Invalid or expired token")


def _verify_api_key(request: Request) -> Optional[str]:
    key = request.headers.get("X-API-Key")
    if not key:
        return None
    for ak in _api_keys.values():
        if hashlib.sha256(ak["secret"].encode()).hexdigest() == hashlib.sha256(key.encode()).hexdigest():
            ak["last_used"] = time.time()
            return ak["email"]
    return None


async def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    """Get current authenticated user from OIDC token or local JWT or API key."""
    if creds:
        payload = await verify_token(creds.credentials)
        return User(
            email=payload.get("email") or payload.get("sub", ""),
            name=payload.get("name", ""),
            role=payload.get("role", "data_engineer"),
        )

    api_key_email = _verify_api_key(request)
    if api_key_email:
        return User(email=api_key_email, name="API Client", role="data_engineer")

    raise HTTPException(status_code=401, detail="Missing authorization header or API key")


async def oidc_callback(request: Request) -> dict:
    """Handle OIDC authorization code callback from Keycloak."""
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    error_description = request.query_params.get("error_description")

    if error:
        raise HTTPException(
            status_code=400,
            detail=f"OIDC authorization failed: {error} - {error_description}",
        )

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Exchange code for tokens
    token_url = f"{settings.oidc_issuer_url}/protocol/openid-connect/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.oidc_client_id,
        "client_secret": settings.oidc_client_secret,
        "redirect_uri": settings.oidc_redirect_uri,
    }

    import httpx
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(token_url, data=data)
        if resp.status_code != 200:
            logger.error("Token exchange failed: %s", resp.text)
            raise HTTPException(status_code=400, detail="Failed to exchange authorization code")
        token_data = resp.json()

    access_token = token_data.get("access_token", "")
    id_token = token_data.get("id_token", "")
    refresh_token = token_data.get("refresh_token", "")

    # Fetch user info
    userinfo = await get_userinfo(access_token)

    # Create local session JWT for frontend
    local_token = create_jwt({
        "email": userinfo.get("email", "unknown"),
        "name": userinfo.get("name", userinfo.get("preferred_username", "")),
        "role": "data_engineer",  # Could map from Keycloak roles
    })

    return {
        "access_token": local_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expiry_minutes * 60,
        "user": userinfo,
        "id_token": id_token,  # Store for logout
        "refresh_token": refresh_token,
    }


def list_api_keys(user: User = Depends(get_current_user)):
    return [k for k in _api_keys.values() if k["email"] == user.email]


def create_api_key(label: str, user: User = Depends(get_current_user)) -> APIKey:
    key_id = f"key-{uuid.uuid4().hex[:12]}"
    secret = f"dp_{uuid.uuid4().hex}"
    _api_keys[key_id] = {
        "id": key_id,
        "label": label,
        "secret": secret,
        "key_prefix": secret[:8],
        "created_at": time.time(),
        "last_used": None,
        "email": user.email,
    }
    return APIKey(id=key_id, label=label, key_prefix=secret[:8], created_at=time.time())


# For backward compatibility
def oauth2_login(request: Request):
    from backend.app.api.oauth import OAuthHandler
    handler = OAuthHandler(
        client_id=settings.oauth_client_id,
        client_secret=settings.oauth_client_secret,
        redirect_uri=settings.oauth_redirect_uri,
    )
    return handler.exchange_code(request)
