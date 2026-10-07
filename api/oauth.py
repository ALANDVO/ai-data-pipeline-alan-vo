import logging, json, base64
import httpx
from typing import Optional, Dict

from config import settings
from api.auth import create_jwt

logger = logging.getLogger(__name__)

class OAuthHandler:

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self) -> str:
        base = settings.oauth_redirect_uri.rstrip("/")
        return f"{base}/oauth/authorize?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code"

    async def exchange_code(self, request) -> Dict:
        code = request.query_params.get("code", "")
        if not code:
            raise ValueError("Missing authorization code")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.redirect_uri}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                },
            )
            resp.raise_for_status()
            token_data = resp.json()
        access_token = token_data.get("access_token", "")
        resp2 = await self._fetch_user(access_token)
        user = resp2.get("user", {})
        jwt_token = create_jwt({
            "email": user.get("email", "unknown"),
            "name": user.get("name", ""),
            "role": "data_engineer",
        })
        return {"token": jwt_token, "user": user}

    async def _fetch_user(self, access_token: str) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.redirect_uri}/oauth/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning("OAuth user fetch failed: %s", e)
            return {"user": {"email": "unknown", "name": "OAuth User"}}
