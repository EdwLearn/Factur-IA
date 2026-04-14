"""
Script to seed the database with realistic Colombian invoices.
Features:
- IVA por línea: 0% (alimentos básicos), 5%, 19%
- Retenciones DIAN (rete_renta, rete_ica)
- Distintos estados: completed, processing, failed
- 7 proveedores, 20 productos, 12 facturas
- Opción --clean para limpiar datos previos
"""
import sys
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

root_dir = Path(__file__).parent.parent.parent.parent
env_path = root_dir / ".env"
load_dotenv(env_path)
print(f"Loaded environment from: {env_path}")

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, date
from decimal import Decimal
import random

from src.database.models import Base, Tenant, ProcessedInvoice, InvoiceLineItem, Supplier, Product

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "facturia_dev")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
print(f"Connecting to: {DB_NAME} at {DB_HOST}:{DB_PORT}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── Proveedores ──────────────────────────────────────────────────────────────
SUPPLIERS = [
    {
        "nit": "900123456-1",
        "name": "Distribuidora El Sol S.A.S",
        "city": "Bogotá", "department": "Cundinamarca",
        "address": "Calle 45 # 23-12", "phone": "601-2345678",
        "category": "abarrotes",
    },
    {
        "nit": "890234567-2",
        "name": "Comercializadora Luna Ltda",
        "city": "Medellín", "department": "Antioquia",
        "address": "Carrera 70 # 50-30", "phone": "604-3456789",
        "category": "abarrotes",
    },
    {
        "nit": "800345678-3",
        "name": "Productos Estrella S.A",
        "city": "Cali", "department": "Valle del Cauca",
        "address": "Avenida 5N # 23-45", "phone": "602-4567890",
        "category": "aseo",
    },
    {
        "nit": "890456789-4",
        "name": "Suministros Andinos SAS",
        "city": "Bucaramanga", "department": "Santander",
        "address": "Calle 36 # 19-25", "phone": "607-5678901",
        "category": "mixto",
    },
    {
        "nit": "900567890-5",
        "name": "Importadora Norte S.A.S",
        "city": "Barranquilla", "department": "Atlántico",
        "address": "Carrera 43 # 85-12", "phone": "605-6789012",
        "category": "mixto",
    },
    {
        "nit": "800678901-6",
        "name": "Almacén Central Ltda",
        "city": "Cartagena", "department": "Bolívar",
        "address": "Calle 30 # 15-40", "phone": "605-7890123",
        "category": "abarrotes",
    },
    {
        "nit": "890789012-7",
        "name": "Proveedora del Caribe S.A",
        "city": "Santa Marta", "department": "Magdalena",
        "address": "Avenida El Libertador # 12-34", "phone": "605-8901234",
        "category": "aseo",
    },
]

# ── Productos — iva_rate: 0=exento, 5=tarifa reducida, 19=general ──────────
# stock: unidades actuales | min_stock: mínimo para alerta | sale_price: precio venta
PRODUCTS = [
    # Alimentos básicos — IVA 0% (excluidos en Colombia)
    {"code": "ALI-001", "description": "Arroz Diana x 500g",          "unit": "UNIDAD",  "base_price": 2500,  "iva_rate": 0,  "category": "Alimentos Básicos",    "supplier": "Distribuidora El Sol S.A.S",  "stock": 120, "min_stock": 30,  "sale_price": 3500},
    {"code": "ALI-002", "description": "Aceite Gourmet x 900ml",       "unit": "UNIDAD",  "base_price": 8500,  "iva_rate": 0,  "category": "Alimentos Básicos",    "supplier": "Distribuidora El Sol S.A.S",  "stock": 65,  "min_stock": 20,  "sale_price": 11900},
    {"code": "ALI-003", "description": "Azúcar Manuelita x 1kg",       "unit": "UNIDAD",  "base_price": 3200,  "iva_rate": 0,  "category": "Alimentos Básicos",    "supplier": "Comercializadora Luna Ltda",  "stock": 80,  "min_stock": 25,  "sale_price": 4500},
    {"code": "ALI-004", "description": "Leche Alpina x 1L",            "unit": "UNIDAD",  "base_price": 3800,  "iva_rate": 0,  "category": "Lácteos",              "supplier": "Comercializadora Luna Ltda",  "stock": 8,   "min_stock": 30,  "sale_price": 5200},
    {"code": "ALI-005", "description": "Pan Bimbo Tajado",             "unit": "UNIDAD",  "base_price": 5200,  "iva_rate": 0,  "category": "Panadería",            "supplier": "Distribuidora El Sol S.A.S",  "stock": 0,   "min_stock": 15,  "sale_price": 7200},
    {"code": "ALI-006", "description": "Pasta Doria x 500g",           "unit": "UNIDAD",  "base_price": 2800,  "iva_rate": 0,  "category": "Alimentos Básicos",    "supplier": "Almacén Central Ltda",        "stock": 55,  "min_stock": 20,  "sale_price": 3900},
    {"code": "ALI-007", "description": "Sal Marina x 1kg",             "unit": "UNIDAD",  "base_price": 1800,  "iva_rate": 0,  "category": "Alimentos Básicos",    "supplier": "Almacén Central Ltda",        "stock": 90,  "min_stock": 15,  "sale_price": 2500},
    {"code": "ALI-008", "description": "Harina Pan x 1kg",             "unit": "UNIDAD",  "base_price": 4200,  "iva_rate": 0,  "category": "Alimentos Básicos",    "supplier": "Distribuidora El Sol S.A.S",  "stock": 42,  "min_stock": 20,  "sale_price": 5800},
    # Alimentos procesados — IVA 5%
    {"code": "ALI-009", "description": "Café Juan Valdez x 250g",      "unit": "UNIDAD",  "base_price": 12500, "iva_rate": 5,  "category": "Bebidas",              "supplier": "Suministros Andinos SAS",     "stock": 30,  "min_stock": 10,  "sale_price": 17500},
    {"code": "ALI-010", "description": "Salsa de tomate Fruco x 400g", "unit": "UNIDAD",  "base_price": 4500,  "iva_rate": 5,  "category": "Alimentos Procesados", "supplier": "Almacén Central Ltda",        "stock": 7,   "min_stock": 15,  "sale_price": 6200},
    {"code": "ALI-011", "description": "Atún Van Camps x 170g",        "unit": "UNIDAD",  "base_price": 6800,  "iva_rate": 5,  "category": "Alimentos Procesados", "supplier": "Importadora Norte S.A.S",     "stock": 45,  "min_stock": 20,  "sale_price": 9500},
    {"code": "ALI-012", "description": "Galletas Oreo x 432g",         "unit": "UNIDAD",  "base_price": 8900,  "iva_rate": 5,  "category": "Snacks",               "supplier": "Importadora Norte S.A.S",     "stock": 0,   "min_stock": 12,  "sale_price": 12500},
    # Aseo — IVA 19%
    {"code": "ASE-001", "description": "Jabón Fab x 1kg",              "unit": "UNIDAD",  "base_price": 7200,  "iva_rate": 19, "category": "Aseo del Hogar",       "supplier": "Productos Estrella S.A",      "stock": 60,  "min_stock": 15,  "sale_price": 9900},
    {"code": "ASE-002", "description": "Papel Higiénico Scott x 4und", "unit": "PAQUETE", "base_price": 9500,  "iva_rate": 19, "category": "Aseo Personal",        "supplier": "Productos Estrella S.A",      "stock": 35,  "min_stock": 20,  "sale_price": 13200},
    {"code": "ASE-003", "description": "Shampoo Sedal x 400ml",        "unit": "UNIDAD",  "base_price": 11200, "iva_rate": 19, "category": "Aseo Personal",        "supplier": "Proveedora del Caribe S.A",   "stock": 22,  "min_stock": 10,  "sale_price": 15500},
    {"code": "ASE-004", "description": "Desodorante Rexona x 150ml",   "unit": "UNIDAD",  "base_price": 13500, "iva_rate": 19, "category": "Aseo Personal",        "supplier": "Proveedora del Caribe S.A",   "stock": 9,   "min_stock": 12,  "sale_price": 18900},
    {"code": "ASE-005", "description": "Detergente Ariel x 500g",      "unit": "UNIDAD",  "base_price": 8700,  "iva_rate": 19, "category": "Aseo del Hogar",       "supplier": "Productos Estrella S.A",      "stock": 48,  "min_stock": 15,  "sale_price": 12000},
    {"code": "ASE-006", "description": "Suavizante Ariel x 1L",        "unit": "UNIDAD",  "base_price": 14900, "iva_rate": 19, "category": "Aseo del Hogar",       "supplier": "Productos Estrella S.A",      "stock": 0,   "min_stock": 8,   "sale_price": 20500},
    {"code": "ASE-007", "description": "Crema dental Colgate x 75ml",  "unit": "UNIDAD",  "base_price": 6500,  "iva_rate": 19, "category": "Aseo Personal",        "supplier": "Proveedora del Caribe S.A",   "stock": 75,  "min_stock": 20,  "sale_price": 8900},
    {"code": "ASE-008", "description": "Jabón de baño Dove x 3und",    "unit": "PAQUETE", "base_price": 12300, "iva_rate": 19, "category": "Aseo Personal",        "supplier": "Proveedora del Caribe S.A",   "stock": 14,  "min_stock": 10,  "sale_price": 17000},
]

SALESPERSONS = ["Carlos Ramírez", "María Torres", "Andrés Gómez", "Luisa Fernández", "Juan Pérez"]


def clean_invoices(db, tenant_id: str):
    """Elimina facturas e items existentes del tenant"""
    db.execute(text(
        "DELETE FROM invoice_line_items WHERE invoice_id IN "
        "(SELECT id FROM processed_invoices WHERE tenant_id = :tid)"
    ), {"tid": tenant_id})
    db.execute(text("DELETE FROM processed_invoices WHERE tenant_id = :tid"), {"tid": tenant_id})
    db.commit()
    print("🗑  Facturas anteriores eliminadas")


def create_tenant(db):
    tenant = db.query(Tenant).filter(Tenant.tenant_id == "demo-company").first()
    if not tenant:
        tenant = Tenant(
            tenant_id="demo-company",
            company_name="Tienda Demo S.A.S",
            nit="900999999-9",
            email="demo@tiendademo.com",
            phone="601-9999999",
            plan="pro",
            max_invoices_month=1000,
            is_active=True,
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        print(f"✓ Tenant creado: {tenant.company_name}")
    else:
        print(f"✓ Tenant ya existe: {tenant.company_name}")
    return tenant


def upsert_suppliers(db, tenant_id: str):
    for s in SUPPLIERS:
        exists = db.query(Supplier).filter(
            Supplier.tenant_id == tenant_id,
            Supplier.nit == s["nit"]
        ).first()
        if not exists:
            db.add(Supplier(
                tenant_id=tenant_id,
                nit=s["nit"],
                company_name=s["name"],
                city=s["city"],
                department=s["department"],
                address=s["address"],
                phone=s["phone"],
            ))
    db.commit()
    print(f"✓ {len(SUPPLIERS)} proveedores listos")


def migrate_product_columns(db):
    """Agrega columnas nuevas a products si no existen (idempotente)."""
    migrations = [
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS category VARCHAR(100)",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(255)",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS supplier_id UUID REFERENCES suppliers(id)",
    ]
    for sql in migrations:
        db.execute(text(sql))
    db.commit()

    # Poblar supplier_id desde supplier_name (para registros existentes)
    db.execute(text("""
        UPDATE products p
        SET supplier_id = s.id
        FROM suppliers s
        WHERE p.supplier_name = s.company_name
          AND p.tenant_id = s.tenant_id
          AND p.supplier_id IS NULL
    """))
    db.commit()
    updated = db.execute(text("SELECT COUNT(*) FROM products WHERE supplier_id IS NOT NULL")).scalar()
    print(f"  → supplier_id poblado en {updated} productos")


def upsert_products(db, tenant_id: str):
    migrate_product_columns(db)

    # Precargar mapa supplier_name → supplier_id para este tenant
    supplier_rows = db.query(Supplier.company_name, Supplier.id).filter(
        Supplier.tenant_id == tenant_id
    ).all()
    supplier_map = {name: sid for name, sid in supplier_rows}

    for p in PRODUCTS:
        sup_id = supplier_map.get(p["supplier"])
        existing = db.query(Product).filter(
            Product.tenant_id == tenant_id,
            Product.product_code == p["code"]
        ).first()
        if existing:
            existing.category = p["category"]
            existing.supplier_name = p["supplier"]
            existing.supplier_id = sup_id
            existing.current_stock = Decimal(str(p["stock"]))
            existing.min_stock = Decimal(str(p["min_stock"]))
            existing.sale_price = Decimal(str(p["sale_price"]))
            existing.last_purchase_price = Decimal(str(p["base_price"]))
            existing.quantity = p["stock"]
        else:
            db.add(Product(
                tenant_id=tenant_id,
                product_code=p["code"],
                description=p["description"],
                unit_measure=p["unit"],
                category=p["category"],
                supplier_name=p["supplier"],
                supplier_id=sup_id,
                current_stock=Decimal(str(p["stock"])),
                min_stock=Decimal(str(p["min_stock"])),
                sale_price=Decimal(str(p["sale_price"])),
                last_purchase_price=Decimal(str(p["base_price"])),
                quantity=p["stock"],
            ))
    db.commit()
    linked = sum(1 for p in PRODUCTS if supplier_map.get(p["supplier"]))
    print(f"✓ {len(PRODUCTS)} productos en catálogo ({linked} con supplier_id vinculado)")


def _build_line_items(products_sample):
    """Genera items con IVA por línea y calcula totales."""
    items = []
    subtotal_total = Decimal("0")
    iva_total = Decimal("0")

    for idx, p in enumerate(products_sample, 1):
        qty = Decimal(str(random.randint(6, 60)))
        # Pequeña variación de precio (+/- 5%)
        price_var = Decimal(str(random.uniform(0.95, 1.05)))
        unit_price = (Decimal(str(p["base_price"])) * price_var).quantize(Decimal("1"))
        line_subtotal = qty * unit_price
        iva_rate = Decimal(str(p["iva_rate"]))
        line_iva = (line_subtotal * iva_rate / Decimal("100")).quantize(Decimal("0.01"))

        subtotal_total += line_subtotal
        iva_total += line_iva

        items.append({
            "line_number": idx,
            "product_code": p["code"],
            "description": p["description"],
            "unit_measure": p["unit"],
            "quantity": qty,
            "unit_price": unit_price,
            "subtotal": line_subtotal,
            "iva_rate": iva_rate,
        })

    return items, subtotal_total, iva_total


def _calc_retenciones(subtotal: Decimal, supplier: dict) -> dict:
    """
    Calcula retenciones DIAN realistas.
    - Rete Renta: 3.5% sobre base (aplica cuando subtotal > 877.000)
    - Rete ICA: 0.414% (Bogotá abarrotes) o 0.966% (aseo/mixto)
    - ReteIVA: 15% del IVA (solo si es gran contribuyente — no siempre)
    """
    threshold = Decimal("877000")
    rete_renta = Decimal("0")
    rete_ica = Decimal("0")

    if subtotal >= threshold:
        rete_renta = (subtotal * Decimal("0.035")).quantize(Decimal("0.01"))

    ica_rate = Decimal("0.00414") if supplier["category"] == "abarrotes" else Decimal("0.00966")
    rete_ica = (subtotal * ica_rate).quantize(Decimal("0.01"))

    return {
        "rete_renta": rete_renta,
        "rete_ica": rete_ica,
        "rete_iva": Decimal("0"),  # simplificado — solo aplica gran contribuyente
    }


# ── Escenarios fijos para reproducibilidad ───────────────────────────────────
INVOICE_SCENARIOS = [
    # (status, supplier_idx, n_products, days_ago, note)
    ("completed",   0, 7, 2,  "Factura reciente completa"),
    ("completed",   1, 5, 5,  "Factura abarrotes Medellín"),
    ("completed",   2, 8, 8,  "Factura aseo Cali grande"),
    ("completed",   3, 4, 12, "Factura mixta Bucaramanga"),
    ("completed",   0, 6, 15, "Factura El Sol segunda compra"),
    ("completed",   4, 5, 20, "Factura Importadora Norte"),
    ("completed",   5, 7, 25, "Factura Almacén Central"),
    ("completed",   1, 3, 30, "Factura Luna pequeña"),
    ("processing",  6, 5, 1,  "Factura procesándose hoy"),
    ("completed",   2, 9, 35, "Factura Estrella grande"),
    ("failed",      3, 0, 3,  "Factura con error de procesamiento"),
    ("completed",   0, 6, 40, "Factura El Sol tercera compra"),
]


def seed_invoices(db, tenant_id: str):
    base_date = datetime.now()
    created = []

    for i, (status, sup_idx, n_prods, days_ago, note) in enumerate(INVOICE_SCENARIOS, 1):
        supplier = SUPPLIERS[sup_idx]
        issue_dt = base_date - timedelta(days=days_ago)
        invoice_num = f"FV-{i:06d}"

        if status == "failed":
            # Factura con error — sin line items, sin totales
            inv = ProcessedInvoice(
                tenant_id=tenant_id,
                original_filename=f"factura_error_{i:03d}.pdf",
                file_size=random.randint(20000, 80000),
                status="failed",
                error_message="Error de lectura: PDF dañado o protegido con contraseña",
                upload_timestamp=issue_dt,
                processing_timestamp=issue_dt + timedelta(seconds=2),
                invoice_number=invoice_num,
                supplier_name=supplier["name"],
                supplier_nit=supplier["nit"],
                supplier_city=supplier["city"],
                supplier_department=supplier["department"],
                issue_date=issue_dt.date(),
                pricing_status="not_required",
            )
            db.add(inv)
            db.flush()
            print(f"  ✗ [{i:02d}] {invoice_num} — {supplier['name']} — FAILED ({note})")
            created.append(inv)
            continue

        if status == "processing":
            # Factura en proceso — solo metadatos básicos
            inv = ProcessedInvoice(
                tenant_id=tenant_id,
                original_filename=f"factura_procesando_{i:03d}.pdf",
                file_size=random.randint(100000, 400000),
                status="processing",
                upload_timestamp=issue_dt,
                processing_timestamp=issue_dt + timedelta(seconds=3),
                invoice_number=invoice_num,
                supplier_name=supplier["name"],
                supplier_nit=supplier["nit"],
                issue_date=issue_dt.date(),
                pricing_status="not_required",
            )
            db.add(inv)
            db.flush()
            print(f"  ⏳ [{i:02d}] {invoice_num} — {supplier['name']} — PROCESSING ({note})")
            created.append(inv)
            continue

        # Factura completada
        sample = random.sample(PRODUCTS, n_prods)
        items, subtotal, iva_amount = _build_line_items(sample)
        retenciones = _calc_retenciones(subtotal, supplier)

        total_retenciones = retenciones["rete_renta"] + retenciones["rete_ica"] + retenciones["rete_iva"]
        total_amount = subtotal + iva_amount - total_retenciones

        # IVA efectivo global (para el campo invoice-level)
        iva_rate_efectiva = (iva_amount / subtotal * 100).quantize(Decimal("0.01")) if subtotal else Decimal("0")

        inv = ProcessedInvoice(
            tenant_id=tenant_id,
            original_filename=f"factura_{i:03d}.pdf",
            file_size=random.randint(50000, 500000),
            status="completed",
            confidence_score=Decimal(str(round(random.uniform(0.86, 0.99), 4))),
            processing_time_seconds=Decimal(str(round(random.uniform(2.5, 8.5), 3))),
            upload_timestamp=issue_dt,
            processing_timestamp=issue_dt + timedelta(seconds=random.randint(2, 8)),
            completion_timestamp=issue_dt + timedelta(seconds=random.randint(10, 30)),

            invoice_number=invoice_num,
            invoice_type="factura_venta",
            issue_date=issue_dt.date(),
            due_date=(issue_dt + timedelta(days=30)).date(),

            supplier_name=supplier["name"],
            supplier_nit=supplier["nit"],
            supplier_address=supplier["address"],
            supplier_city=supplier["city"],
            supplier_department=supplier["department"],
            supplier_phone=supplier["phone"],

            customer_name="Tienda Demo S.A.S",
            customer_id="900999999-9",
            customer_address="Calle 100 # 20-30",
            customer_city="Bogotá",
            customer_department="Cundinamarca",

            salesperson=random.choice(SALESPERSONS),

            subtotal=subtotal,
            iva_rate=iva_rate_efectiva,
            iva_amount=iva_amount,
            rete_renta=retenciones["rete_renta"],
            rete_iva=retenciones["rete_iva"],
            rete_ica=retenciones["rete_ica"],
            total_retenciones=total_retenciones,
            total_amount=total_amount,
            total_items=len(items),

            payment_method=random.choice(["Contado", "Crédito 30 días", "Crédito 15 días"]),
            credit_days=random.choice([0, 15, 30]),

            pricing_status="not_required",
        )
        db.add(inv)
        db.flush()

        for item_data in items:
            db.add(InvoiceLineItem(invoice_id=inv.id, **item_data))

        print(
            f"  ✓ [{i:02d}] {invoice_num} — {supplier['name']:<30} "
            f"{len(items)} ítems — subtotal ${subtotal:>12,.0f} "
            f"IVA ${iva_amount:>9,.0f} — TOTAL ${total_amount:>12,.0f} COP"
        )
        created.append(inv)

    db.commit()
    return created


def main():
    parser = argparse.ArgumentParser(description="Seed FacturIA database")
    parser.add_argument("--clean", action="store_true", help="Elimina facturas existentes antes de sembrar")
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("  SEED DATABASE — FACTURAS COLOMBIANAS REALISTAS")
    print("=" * 65 + "\n")

    Base.metadata.create_all(bind=engine)
    print("✓ Tablas listas\n")

    db = SessionLocal()
    try:
        print("1. Tenant...")
        tenant = create_tenant(db)

        if args.clean:
            print("\n   Limpiando datos anteriores...")
            clean_invoices(db, tenant.tenant_id)

        print("\n2. Proveedores...")
        upsert_suppliers(db, tenant.tenant_id)

        print("\n3. Catálogo de productos...")
        upsert_products(db, tenant.tenant_id)

        print("\n4. Facturas...")
        invoices = seed_invoices(db, tenant.tenant_id)

        completed = [inv for inv in invoices if inv.status == "completed"]
        total_cop = sum(inv.total_amount for inv in completed if inv.total_amount)

        print("\n" + "=" * 65)
        print("  RESUMEN")
        print("=" * 65)
        print(f"  Tenant     : {tenant.company_name} ({tenant.tenant_id})")
        print(f"  Proveedores: {len(SUPPLIERS)}")
        print(f"  Productos  : {len(PRODUCTS)}")
        print(f"  Facturas   : {len(invoices)}  "
              f"({len(completed)} completadas, "
              f"{sum(1 for i in invoices if i.status == 'processing')} procesando, "
              f"{sum(1 for i in invoices if i.status == 'failed')} fallidas)")
        print(f"  Total COP  : ${total_cop:,.0f}")
        print("\n  SEED COMPLETADO EXITOSAMENTE ✓")
        print("=" * 65 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback; traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
