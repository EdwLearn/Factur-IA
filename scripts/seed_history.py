"""
Seed de historial de 5 meses para el motor de recomendaciones.

Crea facturas e ítems con fechas reales en el pasado para que:
  - Algunos productos muestren ALTA velocidad (reabastecimiento urgente)
  - Otros muestren CAPITAL MUERTO (sin movimiento en 45+ días)
  - Algunos tengan tendencia de agotamiento proyectable

Uso: python scripts/seed_history.py
"""

import asyncio
import uuid
from datetime import datetime, timedelta, date
import random
import sys
import os

# Hacer visible el paquete apps.api desde la raíz del proyecto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

# ── Config ────────────────────────────────────────────────────────────────────
DB_URL = (
    f"postgresql+asyncpg://"
    f"{os.getenv('DB_USER','postgres')}:{os.getenv('DB_PASSWORD','postgres')}"
    f"@{os.getenv('DB_HOST','localhost')}:{os.getenv('DB_PORT','5432')}"
    f"/{os.getenv('DB_NAME','facturia_dev')}"
)
TENANT_ID  = "demo-company"
NOW        = datetime.utcnow()
MONTHS_AGO = 5   # historial de 5 meses

engine  = create_async_engine(DB_URL, echo=False)
Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ── Datos de productos con patrones definidos ─────────────────────────────────
#
# frequency_days = cada cuántos días se compra este producto
# qty_per_order  = unidades por factura
# last_purchase_offset = días desde hoy de la ÚLTIMA compra
#   → offset pequeño  = compra reciente  (producto activo, posible restock alert)
#   → offset grande   = compra lejana    (candidato capital muerto)
#
PRODUCTS = [
    # ── Alta rotación: Arroz ──────────────────────── restock alert esperado
    dict(code="ALI-001", freq=14,  qty=60,  last=10,  supplier="Distribuidora El Sol S.A.S",  nit="900123456-1"),
    # ── Alta rotación: Pan Bimbo ─────────────────── agotado + alta velocidad
    dict(code="ALI-005", freq=7,   qty=30,  last=3,   supplier="Distribuidora El Sol S.A.S",  nit="900123456-1"),
    # ── Alta rotación: Galletas Oreo ─────────────── agotado + alta velocidad
    dict(code="ALI-012", freq=10,  qty=24,  last=5,   supplier="Importadora Norte S.A.S",     nit="900567890-5"),
    # ── Rotación media: Azúcar ───────────────────── ok por ahora
    dict(code="ALI-003", freq=21,  qty=80,  last=18,  supplier="Comercializadora Luna Ltda",  nit="890234567-2"),
    # ── Rotación media: Leche ────────────────────── bajo mínimo + historial
    dict(code="ALI-004", freq=10,  qty=50,  last=8,   supplier="Comercializadora Luna Ltda",  nit="890234567-2"),
    # ── Rotación media: Suavizante ───────────────── agotado
    dict(code="ASE-006", freq=15,  qty=20,  last=6,   supplier="Productos Estrella S.A",      nit="800345678-3"),
    # ── Capital muerto: Shampoo Sedal ────────────── última compra hace 68 días
    dict(code="ASE-003", freq=30,  qty=25,  last=68,  supplier="Productos Estrella S.A",      nit="800345678-3"),
    # ── Capital muerto: Café Juan Valdez ─────────── última compra hace 72 días
    dict(code="ALI-009", freq=30,  qty=20,  last=72,  supplier="Almacén Central Ltda",        nit="800678901-6"),
    # ── Capital muerto: Crema dental ─────────────── última compra hace 55 días
    dict(code="ASE-007", freq=25,  qty=30,  last=55,  supplier="Almacén Central Ltda",        nit="800678901-6"),
    # ── Baja rotación: Detergente Ariel ──────────── compra reciente, stock ok
    dict(code="ASE-005", freq=20,  qty=40,  last=12,  supplier="Productos Estrella S.A",      nit="800345678-3"),
    # ── Baja rotación: Jabón Fab ─────────────────── compra reciente
    dict(code="ASE-001", freq=18,  qty=35,  last=14,  supplier="Productos Estrella S.A",      nit="800345678-3"),
    # ── Salsa de tomate ──────────────────────────── bajo mínimo
    dict(code="ALI-010", freq=12,  qty=30,  last=9,   supplier="Distribuidora El Sol S.A.S",  nit="900123456-1"),
]

# Precio base por producto (cost_price para las facturas)
PRICES = {
    "ALI-001": 2500,  "ALI-003": 3200,  "ALI-004": 3800,
    "ALI-005": 5200,  "ALI-009": 12500, "ALI-010": 4500,
    "ALI-012": 8900,  "ASE-001": 7200,  "ASE-003": 11200,
    "ASE-005": 8700,  "ASE-006": 14900, "ASE-007": 6500,
}

DESCRIPTIONS = {
    "ALI-001": "Arroz Diana x 500g",        "ALI-003": "Azúcar Manuelita x 1kg",
    "ALI-004": "Leche Alpina x 1L",          "ALI-005": "Pan Bimbo Tajado",
    "ALI-009": "Café Juan Valdez x 250g",    "ALI-010": "Salsa de tomate Fruco x 400g",
    "ALI-012": "Galletas Oreo x 432g",       "ASE-001": "Jabón Fab x 1kg",
    "ASE-003": "Shampoo Sedal x 400ml",      "ASE-005": "Detergente Ariel x 500g",
    "ASE-006": "Suavizante Ariel x 1L",      "ASE-007": "Crema dental Colgate x 75ml",
}


def build_purchase_dates(freq_days: int, last_offset: int) -> list[datetime]:
    """
    Genera fechas de compra espaciadas freq_days días hacia atrás
    desde (NOW - last_offset), cubriendo MONTHS_AGO meses.
    """
    oldest  = NOW - timedelta(days=MONTHS_AGO * 30)
    last_dt = NOW - timedelta(days=last_offset)
    dates   = []
    current = last_dt
    while current >= oldest:
        # Pequeña variación ±2 días para que no sea robótico
        jitter = timedelta(days=random.randint(-2, 2))
        dates.append(current + jitter)
        current -= timedelta(days=freq_days)
    return dates


async def get_product_ids(session: AsyncSession) -> dict[str, str]:
    rows = (await session.execute(
        text("SELECT product_code, id::text FROM products WHERE tenant_id = :tid"),
        {"tid": TENANT_ID},
    )).all()
    return {r[0]: r[1] for r in rows}


async def seed(session: AsyncSession):
    product_ids = await get_product_ids(session)
    total_invoices = 0
    total_items    = 0

    for product in PRODUCTS:
        code     = product["code"]
        prod_id  = product_ids.get(code)
        if not prod_id:
            print(f"  ⚠  Producto {code} no encontrado — saltando")
            continue

        dates = build_purchase_dates(product["freq"], product["last"])
        price = PRICES.get(code, 5000)
        desc  = DESCRIPTIONS.get(code, code)

        for dt in dates:
            inv_id = str(uuid.uuid4())
            qty    = product["qty"] + random.randint(-5, 5)  # variación ±5 u
            subtot = qty * price

            # ── Factura ──────────────────────────────────────────────────────
            await session.execute(text("""
                INSERT INTO processed_invoices (
                    id, tenant_id, supplier_name, supplier_nit,
                    status, total_amount, total_items,
                    upload_timestamp, completion_timestamp, issue_date,
                    pricing_status, original_filename
                ) VALUES (
                    :id, :tid, :supplier, :nit,
                    'completed', :total, 1,
                    :ts, :ts, :issue,
                    'not_required', :filename
                )
            """), {
                "id":       inv_id,
                "tid":      TENANT_ID,
                "supplier": product["supplier"],
                "nit":      product["nit"],
                "total":    subtot,
                "ts":       dt,
                "issue":    dt.date(),
                "filename": f"seed_{code}_{dt.strftime('%Y%m%d')}.pdf",
            })

            # ── Línea de factura ─────────────────────────────────────────────
            await session.execute(text("""
                INSERT INTO invoice_line_items (
                    id, invoice_id, product_code, description,
                    quantity, unit_price, subtotal,
                    product_id, is_priced, line_number
                ) VALUES (
                    :id, :inv_id, :code, :desc,
                    :qty, :price, :subtotal,
                    :prod_id, false, 1
                )
            """), {
                "id":       str(uuid.uuid4()),
                "inv_id":   inv_id,
                "code":     code,
                "desc":     desc,
                "qty":      qty,
                "price":    price,
                "subtotal": subtot,
                "prod_id":  prod_id,
            })

            total_invoices += 1
            total_items    += 1

        print(f"  ✓  {code} ({desc[:30]}) — {len(dates)} facturas creadas")

    await session.commit()
    print(f"\n  Total: {total_invoices} facturas · {total_items} ítems")


async def main():
    print(f"\n🌱 Seeding historial de {MONTHS_AGO} meses para tenant '{TENANT_ID}'...\n")
    async with Session() as session:
        await seed(session)
    await engine.dispose()
    print("\n✅ Seed completado.\n")


if __name__ == "__main__":
    asyncio.run(main())
