"""
Crea 4 productos nuevos con historial de capital muerto real:
solo facturas viejas (55-80 días atrás), sin aparición en facturas recientes.
"""

import asyncio, uuid, random, sys, os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DB_URL = (
    f"postgresql+asyncpg://"
    f"{os.getenv('DB_USER','postgres')}:{os.getenv('DB_PASSWORD','postgres')}"
    f"@{os.getenv('DB_HOST','localhost')}:{os.getenv('DB_PORT','5432')}"
    f"/{os.getenv('DB_NAME','facturia_dev')}"
)
TENANT_ID = "demo-company"
NOW       = datetime.utcnow()

engine  = create_async_engine(DB_URL, echo=False)
Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ── Productos muertos nuevos ──────────────────────────────────────────────────
DEAD_PRODUCTS = [
    dict(
        code="ALI-020", description="Aceite Oleocali x 3L",
        category="Alimentos Básicos", supplier="Distribuidora El Sol S.A.S", nit="900123456-1",
        stock=45, min_stock=10, cost=18500, sale=25000,
        # Comprado hace 67 días y antes — nunca en facturas recientes
        purchase_dates_offset=[67, 97, 127, 157],
        qty_per_order=50,
    ),
    dict(
        code="ALI-021", description="Mermelada Fruco Fresa x 450g",
        category="Alimentos Básicos", supplier="Comercializadora Luna Ltda", nit="890234567-2",
        stock=30, min_stock=8, cost=6800, sale=9400,
        purchase_dates_offset=[59, 89, 119, 149],
        qty_per_order=35,
    ),
    dict(
        code="ASE-010", description="Talco Jonhson x 200g",
        category="Aseo Personal", supplier="Productos Estrella S.A", nit="800345678-3",
        stock=60, min_stock=12, cost=9200, sale=12800,
        purchase_dates_offset=[72, 102, 132],
        qty_per_order=40,
    ),
    dict(
        code="ALI-022", description="Mayonesa Fruco x 400g",
        category="Alimentos Básicos", supplier="Almacén Central Ltda", nit="800678901-6",
        stock=55, min_stock=15, cost=7500, sale=10200,
        purchase_dates_offset=[81, 111, 141],
        qty_per_order=60,
    ),
]


async def seed(session: AsyncSession):
    # Buscar un supplier_id válido para el FK (no es requerido, usamos NULL)
    for p in DEAD_PRODUCTS:
        prod_id = str(uuid.uuid4())
        capital = p["stock"] * p["cost"]

        # ── Insertar producto ────────────────────────────────────────────────
        await session.execute(text("""
            INSERT INTO products (
                id, tenant_id, product_code, description, category,
                supplier_name, current_stock, min_stock,
                last_purchase_price, sale_price,
                quantity, total_purchased, total_amount,
                created_at, updated_at
            ) VALUES (
                :id, :tid, :code, :desc, :cat,
                :supplier, :stock, :min_stock,
                :cost, :sale,
                :stock, :stock, :total,
                :old_date, :old_date
            )
        """), {
            "id":        prod_id,
            "tid":       TENANT_ID,
            "code":      p["code"],
            "desc":      p["description"],
            "cat":       p["category"],
            "supplier":  p["supplier"],
            "stock":     p["stock"],
            "min_stock": p["min_stock"],
            "cost":      p["cost"],
            "sale":      p["sale"],
            "total":     p["stock"] * p["cost"],
            "old_date":  NOW - timedelta(days=p["purchase_dates_offset"][0]),
        })

        # ── Insertar facturas históricas (solo fechas viejas) ────────────────
        for offset in p["purchase_dates_offset"]:
            dt     = NOW - timedelta(days=offset + random.randint(-2, 2))
            inv_id = str(uuid.uuid4())
            qty    = p["qty_per_order"] + random.randint(-5, 5)
            subtot = qty * p["cost"]

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
                "supplier": p["supplier"],
                "nit":      p["nit"],
                "total":    subtot,
                "ts":       dt,
                "issue":    dt.date(),
                "filename": f"seed_{p['code']}_{dt.strftime('%Y%m%d')}.pdf",
            })

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
                "code":     p["code"],
                "desc":     p["description"],
                "qty":      qty,
                "price":    p["cost"],
                "subtotal": subtot,
                "prod_id":  prod_id,
            })

        await session.commit()
        print(
            f"  ✓  {p['code']} {p['description'][:35]} | "
            f"stock:{p['stock']} | capital:${p['stock']*p['cost']:,.0f} | "
            f"último mvto: {p['purchase_dates_offset'][0]} días atrás"
        )


async def main():
    print(f"\n🌱 Creando {len(DEAD_PRODUCTS)} productos de capital muerto...\n")
    async with Session() as session:
        await seed(session)
    await engine.dispose()
    print("\n✅ Seed completado.\n")

if __name__ == "__main__":
    asyncio.run(main())
