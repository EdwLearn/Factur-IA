"""
Script para crear un tenant de prueba en la base de datos.
Uso: python apps/api/scripts/create_test_tenant.py
"""
import sys
import os
from pathlib import Path

# Add project root to path
root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root))

import bcrypt
import psycopg2
from dotenv import load_dotenv

load_dotenv(root / ".env")

TENANT_ID    = "test"
PASSWORD     = "test123"
COMPANY_NAME = "Empresa de Prueba"
EMAIL        = "test@facturia.co"

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 5432)),
    dbname=os.getenv("DB_NAME", "facturia_dev"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "postgres"),
)
cur = conn.cursor()

# Check if already exists
cur.execute("SELECT tenant_id FROM tenants WHERE tenant_id = %s", (TENANT_ID,))
if cur.fetchone():
    print(f"✓ Tenant '{TENANT_ID}' ya existe — no se creó de nuevo.")
else:
    hashed = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()
    cur.execute("""
        INSERT INTO tenants
            (id, tenant_id, company_name, email, password_hash, plan,
             max_invoices_month, invoices_processed_month, is_active)
        VALUES
            (gen_random_uuid(), %s, %s, %s, %s, 'freemium', 10, 0, true)
    """, (TENANT_ID, COMPANY_NAME, EMAIL, hashed))
    conn.commit()
    print(f"✓ Tenant creado.")

cur.close()
conn.close()

print(f"\n  ID de empresa : {TENANT_ID}")
print(f"  Contraseña    : {PASSWORD}\n")
