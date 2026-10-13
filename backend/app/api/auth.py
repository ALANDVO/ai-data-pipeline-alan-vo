from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional
import time, os, uuid, hashlib

from backend.app.core.config import settings

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
    payload = {
        "sub": user.get("email", "unknown"),
        "name": user.get("name", ""),
        "role": user.get("role", "data_engineer"),
        "exp": time.time() + settings.jwt_expiry_minutes * 60,
        "iat": time.time(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

def verify_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError:
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

def get_current_user(request: Request, creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> User:
    if creds:
        payload = verify_jwt(creds.credentials)
        return User(email=payload.get("sub", ""), name=payload.get("name", ""), role=payload.get("role", "data_engineer"))
    api_key_email = _verify_api_key(request)
    if api_key_email:
        return User(email=api_key_email, name="API Client", role="data_engineer")
    raise HTTPException(status_code=401, detail="Missing authorization header or API key")

def oauth2_login(request: Request):
    from backend.app.api.oauth import OAuthHandler
    handler = OAuthHandler(
        client_id=settings.oauth_client_id,
        client_secret=settings.oauth_client_secret,
        redirect_uri=settings.oauth_redirect_uri,
    )
    return handler.exchange_code(request)

def list_api_keys(user: User = Depends(get_current_user)):
    return [k for k in _api_keys.values() if k["email"] == user.email]

def create_api_key(label: str, user: User = Depends(get_current_user)) -> APIKey:
    key_id = f"key-{uuid.uuid4().hex[:12]}"
    secret = f"dp_{uuid.uuid4().hex}"
    _api_keys[key_id] = {
        "id": key_id, "label": label, "secret": secret,
        "key_prefix": secret[:8], "created_at": time.time(),
        "last_used": None, "email": user.email,
    }
    return APIKey(id=key_id, label=label, key_prefix=secret[:8], created_at=time.time())
