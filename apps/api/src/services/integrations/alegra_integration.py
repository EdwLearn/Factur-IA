"""
Alegra accounting platform integration.

Token storage strategy
──────────────────────
The raw API token is NEVER persisted in plain text.
It is encrypted with Fernet (AES-128-CBC + HMAC) using the key set in
ALEGRA_ENCRYPTION_KEY before being stored in tenant.integration_config (JSONB).

Alegra API auth
───────────────
Basic Auth header:  base64(email:token)
Base URL:           ALEGRA_BASE_URL  (default: sandbox)
Docs:               https://developer.alegra.com
"""

import base64
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken

from ...core.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------

def _get_fernet() -> Fernet:
    settings = get_settings()
    key = settings.alegra_encryption_key
    if not key:
        raise RuntimeError(
            "ALEGRA_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode())


def encrypt_token(raw_token: str) -> str:
    """Return a Fernet-encrypted, URL-safe base64 string."""
    return _get_fernet().encrypt(raw_token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a Fernet-encrypted token. Raises InvalidToken if tampered."""
    return _get_fernet().decrypt(encrypted_token.encode()).decode()


# ---------------------------------------------------------------------------
# Alegra API client
# ---------------------------------------------------------------------------

class AlegraClient:
    """Thin async wrapper around the Alegra REST API."""

    def __init__(self, email: str, token: str):
        self._auth_header = _build_auth_header(email, token)
        self._base_url = get_settings().alegra_base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _resolve_url(self, path: str) -> str:
        """
        Descubre la URL final tras seguir redirects SIN auth.
        Necesario porque el sandbox de Alegra redirige HTTP→HTTPS:26967
        y los redirects eliminan el header Authorization y el body.
        """
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=15) as client:
            probe = await client.get(url, follow_redirects=True)
            return str(probe.url)

    async def _get(self, path: str, params: dict | None = None) -> Any:
        final_url = await self._resolve_url(path)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(final_url, headers=self._headers(), params=params)
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str, body: dict) -> Any:
        final_url = await self._resolve_url(path)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(final_url, headers=self._headers(), json=body)
            resp.raise_for_status()
            return resp.json()

    async def _put(self, path: str, body: dict) -> Any:
        """Alegra usa PUT (no PATCH) para actualizar recursos."""
        final_url = await self._resolve_url(path)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(final_url, headers=self._headers(), json=body)
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Public endpoints
    # ------------------------------------------------------------------

    async def get_current_user(self) -> dict:
        """GET /users/self — validates the token and returns user info."""
        return await self._get("/users/self")

    async def get_items(self, limit: int = 30, start: int = 0) -> list[dict]:
        """GET /items — product catalog from Alegra."""
        data = await self._get("/items", params={"limit": limit, "start": start})
        return data if isinstance(data, list) else []

    async def create_item(self, item_data: dict) -> dict:
        """POST /items — create a product in Alegra."""
        return await self._post("/items", item_data)

    async def update_item(self, alegra_item_id: str, item_data: dict) -> dict:
        """PUT /items/{id} — update a product in Alegra (Alegra uses PUT, not PATCH)."""
        return await self._put(f"/items/{alegra_item_id}", item_data)

    async def get_contacts(self, limit: int = 30, start: int = 0) -> list[dict]:
        """GET /contacts — clients/suppliers from Alegra."""
        data = await self._get("/contacts", params={"limit": limit, "start": start})
        return data if isinstance(data, list) else []

    async def create_contact(self, contact_data: dict) -> dict:
        """POST /contacts — create a supplier/contact in Alegra."""
        return await self._post("/contacts", contact_data)

    async def update_contact(self, alegra_contact_id: str, contact_data: dict) -> dict:
        """PUT /contacts/{id} — update a contact in Alegra (Alegra uses PUT, not PATCH)."""
        return await self._put(f"/contacts/{alegra_contact_id}", contact_data)

    async def get_invoices(self, limit: int = 30) -> list[dict]:
        """GET /invoices — issued invoices from Alegra."""
        data = await self._get("/invoices", params={"limit": limit})
        return data if isinstance(data, list) else []

    async def post_bill(self, bill_data: dict) -> dict:
        """POST /bills — create a purchase bill (cuenta por pagar) in Alegra.

        Minimum payload:
            {
                "date": "YYYY-MM-DD",
                "contact": {"id": <int>},          # proveedor en Alegra
                "items": [
                    {"quantity": 12, "price": 5000, "name": "Producto X"}
                ]
            }
        """
        return await self._post("/bills", bill_data)


# ---------------------------------------------------------------------------
# Integration config helpers
# ---------------------------------------------------------------------------

def build_integration_config(email: str, raw_token: str, user_info: dict) -> dict:
    """
    Build the dict that gets stored in tenant.integration_config under
    the 'alegra' key.  The raw token is encrypted before storage.
    """
    return {
        "alegra": {
            "email": email,
            "token_encrypted": encrypt_token(raw_token),
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_info.get("id"),
            "user_email": user_info.get("email"),
            "user_role": user_info.get("role"),
            "status": "active",
        }
    }


def extract_alegra_config(integration_config: dict | None) -> dict | None:
    """Return the 'alegra' sub-dict from integration_config, or None."""
    if not integration_config:
        return None
    return integration_config.get("alegra")


def get_client_from_config(integration_config: dict | None) -> AlegraClient:
    """
    Build an AlegraClient from a tenant's stored integration_config.
    Raises ValueError if Alegra is not connected.
    """
    cfg = extract_alegra_config(integration_config)
    if not cfg or cfg.get("status") != "active":
        raise ValueError("Alegra integration is not connected for this tenant.")

    email = cfg["email"]
    try:
        raw_token = decrypt_token(cfg["token_encrypted"])
    except (InvalidToken, KeyError) as exc:
        raise ValueError("Stored Alegra token is invalid or corrupted.") from exc

    return AlegraClient(email=email, token=raw_token)


# ---------------------------------------------------------------------------
# Internal utils
# ---------------------------------------------------------------------------

def _build_auth_header(email: str, token: str) -> str:
    """Build the Basic Auth header value for Alegra (email:token → base64)."""
    credentials = f"{email}:{token}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"
