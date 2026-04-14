"""
Script rápido para probar GET /items y GET /contacts contra el sandbox de Alegra.
No depende del paquete interno — llama httpx directamente.
"""
import asyncio
import base64
import os
import sys

import httpx

BASE_URL = os.getenv("ALEGRA_BASE_URL", "https://sandbox.alegra.com/api/v1")
EMAIL    = os.getenv("ALEGRA_EMAIL", "")
TOKEN    = os.getenv("ALEGRA_TOKEN", "")


def auth_header() -> str:
    encoded = base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
    return f"Basic {encoded}"


async def get(path: str, params: dict | None = None):
    url = f"{BASE_URL}{path}"
    headers = {
        "Authorization": auth_header(),
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        # Paso 1: descubrir URL final sin auth (evita que redirect borre el header)
        probe = await client.get(url, follow_redirects=True)
        final_url = str(probe.url)
        # Paso 2: petición real con auth a la URL final
        resp = await client.get(final_url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()


async def main():
    if not EMAIL or not TOKEN:
        print("ERROR: Define ALEGRA_EMAIL y ALEGRA_TOKEN")
        sys.exit(1)

    print(f"Base URL : {BASE_URL}")
    print(f"Usuario  : {EMAIL}\n")

    # /users/self
    print("=== GET /users/self ===")
    try:
        user = await get("/users/self")
        print(f"  OK — {user.get('name')} ({user.get('email')}), rol: {user.get('role')}")
    except httpx.HTTPStatusError as e:
        print(f"  HTTP {e.response.status_code}: {e.response.text[:300]}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # /items
    print("\n=== GET /items ===")
    try:
        items = await get("/items", params={"limit": 5})
        data = items if isinstance(items, list) else []
        print(f"  OK — {len(data)} items")
        for item in data[:5]:
            print(f"    · [{item.get('id')}] {item.get('name')} — precio: {item.get('price')}")
    except httpx.HTTPStatusError as e:
        print(f"  HTTP {e.response.status_code}: {e.response.text[:300]}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # /contacts
    print("\n=== GET /contacts ===")
    try:
        contacts = await get("/contacts", params={"limit": 5})
        data = contacts if isinstance(contacts, list) else []
        print(f"  OK — {len(data)} contactos")
        for c in data[:5]:
            print(f"    · [{c.get('id')}] {c.get('name')} — {c.get('email')}")
    except httpx.HTTPStatusError as e:
        print(f"  HTTP {e.response.status_code}: {e.response.text[:300]}")
    except Exception as e:
        print(f"  ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
