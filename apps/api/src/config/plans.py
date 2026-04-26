"""
Plan definitions for FacturIA subscription tiers.

Each plan is a frozen dataclass so values can never be mutated at runtime.
Use get_plan(tenant.plan) anywhere you need to enforce limits.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PlanConfig:
    name: str
    display_name: str
    price_cop: int
    invoice_limit: Optional[int]   # None = unlimited
    supplier_limit: Optional[int]  # None = unlimited
    history_days: Optional[int]    # None = unlimited
    max_users: int
    can_export: bool
    can_inventory: bool
    can_alerts: bool
    support_level: str             # "email" | "email_priority" | "chat_email"


PLANS: dict[str, PlanConfig] = {
    "freemium": PlanConfig(
        name="freemium",
        display_name="Freemium",
        price_cop=0,
        invoice_limit=15,
        supplier_limit=5,
        history_days=30,
        max_users=1,
        can_export=False,
        can_inventory=False,
        can_alerts=False,
        support_level="email",
    ),
    "basic": PlanConfig(
        name="basic",
        display_name="Básico",
        price_cop=79_900,
        invoice_limit=100,
        supplier_limit=50,
        history_days=180,
        max_users=1,
        can_export=False,
        can_inventory=True,
        can_alerts=True,
        support_level="email_priority",
    ),
    "founders": PlanConfig(
        name="founders",
        display_name="Founders",
        price_cop=149_900,
        invoice_limit=None,
        supplier_limit=None,
        history_days=None,
        max_users=3,
        can_export=True,
        can_inventory=True,
        can_alerts=True,
        support_level="chat_email",
    ),
    "pro": PlanConfig(
        name="pro",
        display_name="Pro",
        price_cop=299_900,
        invoice_limit=None,
        supplier_limit=None,
        history_days=None,
        max_users=5,
        can_export=True,
        can_inventory=True,
        can_alerts=True,
        support_level="chat_email",
    ),
}


def get_plan(plan_name: str) -> PlanConfig:
    """Return PlanConfig for plan_name, falling back to freemium for unknown values."""
    return PLANS.get(plan_name, PLANS["freemium"])


# Flat dict for runtime limit checks (e.g. cleanup service, history guards).
# None = unlimited (Pro plan).
PLAN_LIMITS: dict[str, dict] = {
    "freemium": {
        "facturas_mes": 15,
        "proveedores": 5,
        "historial_dias": 30,
        "usuarios": 1,
        "inventario": False,
        "alertas_stock": False,
        "exportar_reportes": False,
        "storage_days": 30,
    },
    "basic": {
        "facturas_mes": 100,
        "proveedores": 50,
        "historial_dias": 180,
        "usuarios": 1,
        "inventario": True,
        "alertas_stock": True,
        "exportar_reportes": False,
        "storage_days": 180,
    },
    "founders": {
        "facturas_mes": None,
        "proveedores": None,
        "historial_dias": None,
        "usuarios": 3,
        "inventario": True,
        "alertas_stock": True,
        "exportar_reportes": True,
        "storage_days": None,
        "precio": 149_900,
        "precio_congelado": True,
        "cupos_maximos": 30,
    },
    "pro": {
        "facturas_mes": None,
        "proveedores": None,
        "historial_dias": None,
        "usuarios": 5,
        "inventario": True,
        "alertas_stock": True,
        "exportar_reportes": True,
        "storage_days": None,
    },
}
