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
logging.getLogger("httpx").setLevel(logging.WARNING)

# IVA rate (%) → Alegra tax id — confirmed against sandbox GET /taxes
# id=1 IVA Exento (0%, EXEMPT)  id=2 IVA Excluido (0%, EXCLUDED)
# id=3 IVA 5%                   id=4 IVA 19%
IVA_RATE_TO_ALEGRA_ID: dict[int, str] = {
    0:  "1",   # IVA Exento — EXEMPT
    5:  "3",   # IVA 5%
    19: "4",   # IVA 19%
}
_DEFAULT_TAX_ID = "1"  # Exento — safe fallback when rate is unknown


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
            logger.info(f"ALEGRA response status: {resp.status_code}")
            logger.info(f"ALEGRA response body: {resp.text}")
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

    async def find_item_by_reference(self, reference: str) -> dict | None:
        """GET /items?reference=X — busca un ítem por su referencia/código."""
        data = await self._get("/items", params={"reference": reference})
        items = data if isinstance(data, list) else []
        return items[0] if items else None

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

    async def get_invoices(
        self,
        date_start: str = None,
        date_end: str = None,
        limit: int = 30,
        start: int = 0,
    ) -> list[dict]:
        """GET /invoices — facturas de venta de Alegra.

        date_start / date_end en formato YYYY-MM-DD.
        """
        params: dict = {"limit": limit, "start": start}
        if date_start:
            params["date-start"] = date_start
        if date_end:
            params["date-end"] = date_end

        data = await self._get("/invoices", params=params)
        return data if isinstance(data, list) else []

    async def get_item_stock(self, item_id: str) -> dict:
        """GET /items/{id} — stock actual de un producto en Alegra."""
        data = await self._get(f"/items/{item_id}")
        inventory = data.get("inventory", {}) if isinstance(data, dict) else {}
        return {
            "id": item_id,
            "available_quantity": inventory.get("availableQuantity", 0),
            "warehouses": inventory.get("warehouses", []),
        }

    async def get_taxes(self) -> list[dict]:
        """GET /taxes — list of taxes configured in Alegra."""
        data = await self._get("/taxes")
        return data if isinstance(data, list) else []

    async def get_or_create_contact(self, nit: str, name: str) -> str:
        """
        Busca el proveedor por NIT en Alegra; si no existe lo crea.
        Retorna el id como string.
        """
        # Limpiar NIT: quitar dígito verificador si viene "XXXXXXXXX-X"
        nit_clean = nit.split("-")[0].strip() if nit else nit

        logger.info(f"Buscando contacto por NIT: {nit_clean}")
        contacts = await self._get(
            "/contacts",
            params={"identification": nit_clean, "type": "provider"},
        )
        logger.info(f"Contactos encontrados: {contacts}")
        if contacts and isinstance(contacts, list) and len(contacts) > 0:
            return str(contacts[0]["id"])

        new_contact = await self._post("/contacts", {
            "name": name,
            "identification": nit_clean,
            "kindOfPerson": "LEGAL_ENTITY",
            "identificationObject": {
                "type": "NIT",
                "number": nit_clean,
            },
            "type": [{"id": "vendor"}],
            "term": {"id": 1},
        })
        return str(new_contact["id"])

    async def post_bill(self, bill_data: dict) -> dict:
        """POST /bills — create a purchase bill (cuenta por pagar) in Alegra.

        Correct payload schema (confirmed with Alegra support):
            {
                "date": "YYYY-MM-DD",
                "dueDate": "YYYY-MM-DD",           # 30 días después de date
                "provider": {"id": "2"},            # str, NO "contact"
                "purchases": {
                    "items": [
                        {
                            "id": "1",             # str
                            "name": "Producto X",
                            "price": 10000,
                            "quantity": 1,
                            "tax": [{"id": "4"}]   # str
                        }
                    ]
                }
            }
        Note: numberTemplate is NOT needed for purchase bills.
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

    token_preview = raw_token[:8] + "..." if raw_token else "NONE"
    logger.info(f"ALEGRA auth: email={email}, token={token_preview}")

    return AlegraClient(email=email, token=raw_token)


# ---------------------------------------------------------------------------
# Internal utils
# ---------------------------------------------------------------------------

def _build_auth_header(email: str, token: str) -> str:
    """Build the Basic Auth header value for Alegra (email:token → base64)."""
    credentials = f"{email}:{token}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"
