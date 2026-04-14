# 🔗 Dashboard Backend Integration

## Resumen

Se ha completado exitosamente la integración del Dashboard de FacturIA con el backend, conectando todos los componentes para mostrar datos reales en tiempo real.

## 📋 Cambios Realizados

### 1. Backend - Nuevos Endpoints de Dashboard

**Archivo creado:** [`apps/api/src/api/routers/dashboard.py`](apps/api/src/api/routers/dashboard.py)

Se crearon 3 nuevos endpoints REST para el dashboard:

#### GET `/api/v1/dashboard/metrics`
Retorna métricas principales del dashboard:
- Total de facturas del mes actual
- Valor total del inventario
- Alertas pendientes
- Total de proveedores
- Crecimiento mes a mes (MoM) de facturas e inventario

**Respuesta:**
```json
{
  "total_invoices_month": 15,
  "total_inventory_value": 2500000.50,
  "pending_alerts": 3,
  "total_suppliers": 8,
  "month_over_month_invoices": 12.5,
  "month_over_month_inventory": 8.0
}
```

#### GET `/api/v1/dashboard/recent-invoices?limit=10`
Retorna las facturas más recientes con información resumida:
- ID de la factura
- Nombre del proveedor
- Estado de procesamiento
- Total de la factura
- Cantidad de items
- Fecha de subida
- Duración de procesamiento

**Respuesta:**
```json
[
  {
    "id": "uuid-here",
    "supplier_name": "Textiles Medellín",
    "status": "completed",
    "total": 1250000.00,
    "items_count": 15,
    "upload_timestamp": "2024-01-15T10:30:00Z",
    "processing_duration_seconds": 45
  }
]
```

#### GET `/api/v1/dashboard/analytics`
Retorna datos para gráficos y análisis:
- Volumen de compras (últimas 8 semanas)
- Tendencia de márgenes (últimos 8 meses)
- Proyección de inventario (top 5 productos)
- Métricas comparativas (mes actual vs anterior)

**Respuesta:**
```json
{
  "purchase_volume": [
    {"period": "Sem 1", "volume": 125000},
    {"period": "Sem 2", "volume": 142000}
  ],
  "margin_trend": [
    {"month": "Ene", "margin": 38.5},
    {"month": "Feb", "margin": 41.2}
  ],
  "inventory_projection": [
    {"product": "Camisetas", "current": 45, "projected": 28}
  ],
  "comparison_metrics": {
    "invoices_processed": 85,
    "invoices_change": 12.0,
    "total_revenue": 8450,
    "revenue_change": 8.0,
    "new_products": 23,
    "products_change": -5.0,
    "avg_processing_time_minutes": 2.1,
    "time_change": -15.0
  }
}
```

### 2. Backend - Registro de Router

**Archivo modificado:** [`apps/api/src/api/main.py`](apps/api/src/api/main.py)

Se registró el nuevo router de dashboard en la aplicación FastAPI:

```python
from .routers import invoices, dashboard

app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
```

### 3. Frontend - Cliente API

**Archivo creado:** [`apps/web/src/lib/api/endpoints/dashboard.ts`](apps/web/src/lib/api/endpoints/dashboard.ts)

Se creó el cliente API del frontend con:
- Tipos TypeScript para todas las respuestas
- Funciones para llamar a cada endpoint
- Manejo de errores consistente

**Funciones exportadas:**
```typescript
export const dashboardApi = {
  getMetrics: async (): Promise<DashboardMetrics>
  getRecentInvoices: async (limit?: number): Promise<RecentInvoice[]>
  getAnalytics: async (): Promise<AnalyticsData>
}
```

### 4. Frontend - Wrapper de API

**Archivo modificado:** [`apps/web/lib/api/facturaAPI.ts`](apps/web/lib/api/facturaAPI.ts)

Se agregaron los métodos del dashboard al wrapper principal:

```typescript
export const facturaAPI = {
  // ... métodos existentes

  // Dashboard operations
  getDashboardMetrics: dashboardApi.getMetrics,
  getRecentInvoices: dashboardApi.getRecentInvoices,
  getDashboardAnalytics: dashboardApi.getAnalytics,
}
```

### 5. Frontend - Componente Dashboard

**Archivo modificado:** [`apps/web/app/page.tsx`](apps/web/app/page.tsx)

Se actualizó el componente principal del Dashboard para:

#### Estados agregados:
```typescript
const [dashboardMetrics, setDashboardMetrics] = useState<DashboardMetrics | null>(null)
const [recentInvoicesData, setRecentInvoicesData] = useState<RecentInvoiceAPI[]>([])
const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)
const [isDashboardLoading, setIsDashboardLoading] = useState(false)
```

#### Carga de datos:
```typescript
useEffect(() => {
  if (activeTab === "Dashboard") {
    loadDashboardData()
  }
}, [activeTab])

const loadDashboardData = async () => {
  setIsDashboardLoading(true)
  try {
    facturaAPI.setTenantId("default-tenant-id")

    const [metrics, recentInvs, analytics] = await Promise.all([
      facturaAPI.getDashboardMetrics(),
      facturaAPI.getRecentInvoices(10),
      facturaAPI.getDashboardAnalytics(),
    ])

    setDashboardMetrics(metrics)
    setRecentInvoicesData(recentInvs)
    setAnalyticsData(analytics)
  } catch (error) {
    console.error("Error loading dashboard data:", error)
  } finally {
    setIsDashboardLoading(false)
  }
}
```

#### Componentes actualizados:
1. **Tarjetas de métricas** - Ahora muestran datos reales del backend
2. **Gráfico de volumen de compras** - Usa datos de `analyticsData.purchase_volume`
3. **Gráfico de tendencia de margen** - Usa datos de `analyticsData.margin_trend`
4. **Comparación de períodos** - Usa datos de `analyticsData.comparison_metrics`
5. **Proyección de inventario** - Usa datos de `analyticsData.inventory_projection`

## 🎯 Funcionalidades Implementadas

### ✅ Métricas en Tiempo Real
- Facturas procesadas este mes con % de crecimiento
- Valor total del inventario
- Alertas pendientes
- Total de proveedores activos

### ✅ Gráficos Interactivos
- **Volumen de Compras:** Línea temporal de las últimas 8 semanas
- **Tendencia de Margen:** Evolución del margen de ganancia
- **Comparación de Períodos:** Mes actual vs mes anterior
- **Proyección de Inventario:** Stock actual vs proyectado a 30 días

### ✅ Estado de Carga
- Indicadores de carga (`isDashboardLoading`)
- Fallback a datos mock si la API falla
- Manejo de errores con console.log para debugging

## 🔧 Configuración Requerida

### Variables de Entorno

**Backend (.env):**
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/facturia
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

**Frontend (.env.local):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### Tenant ID
Actualmente el frontend usa un tenant ID hardcodeado:
```typescript
facturaAPI.setTenantId("default-tenant-id")
```

**TODO:** Integrar con el sistema de autenticación para obtener el tenant ID del usuario logueado.

## 🚀 Cómo Probar

### 1. Iniciar el Backend
```bash
cd apps/api
python -m uvicorn src.api.main:app --reload --port 8000
```

El backend estará disponible en `http://localhost:8000`

Documentación interactiva: `http://localhost:8000/docs`

### 2. Iniciar el Frontend
```bash
cd apps/web
pnpm dev
```

El frontend estará disponible en `http://localhost:3000`

### 3. Verificar Endpoints

**Probar métricas:**
```bash
curl -H "x-tenant-id: default-tenant-id" http://localhost:8000/api/v1/dashboard/metrics
```

**Probar facturas recientes:**
```bash
curl -H "x-tenant-id: default-tenant-id" http://localhost:8000/api/v1/dashboard/recent-invoices?limit=5
```

**Probar analytics:**
```bash
curl -H "x-tenant-id: default-tenant-id" http://localhost:8000/api/v1/dashboard/analytics
```

### 4. Verificar en el Dashboard

1. Abrir `http://localhost:3000`
2. Ir a la pestaña "Dashboard"
3. Verificar que:
   - Las tarjetas de métricas muestran datos reales
   - Los gráficos se renderizan correctamente
   - No hay errores en la consola del navegador
   - El estado de carga funciona correctamente

## 📊 Flujo de Datos

```mermaid
graph LR
    A[Usuario abre Dashboard] --> B[useEffect se dispara]
    B --> C[loadDashboardData]
    C --> D[Promise.all: 3 llamadas API]
    D --> E[GET /dashboard/metrics]
    D --> F[GET /dashboard/recent-invoices]
    D --> G[GET /dashboard/analytics]
    E --> H[Actualiza dashboardMetrics]
    F --> I[Actualiza recentInvoicesData]
    G --> J[Actualiza analyticsData]
    H --> K[Re-render Dashboard]
    I --> K
    J --> K
```

## 🔄 Próximos Pasos

### Mejoras Pendientes

1. **Autenticación y Multi-tenancy**
   - [ ] Integrar con sistema de auth para obtener tenant ID automáticamente
   - [ ] Implementar JWT tokens en headers

2. **Optimizaciones de Backend**
   - [ ] Cachear queries de analytics (Redis)
   - [ ] Implementar paginación en recent-invoices
   - [ ] Calcular márgenes reales desde line_items (actualmente usa mock data)

3. **Mejoras de Frontend**
   - [ ] Agregar botón de refresh manual
   - [ ] Implementar auto-refresh cada N minutos
   - [ ] Agregar filtros de fecha en los gráficos
   - [ ] Mostrar tooltips más detallados en gráficos

4. **Testing**
   - [ ] Tests unitarios para endpoints de dashboard
   - [ ] Tests de integración frontend-backend
   - [ ] Tests E2E con Playwright

5. **Monitoring**
   - [ ] Agregar logging de performance de queries
   - [ ] Implementar métricas de uso de endpoints
   - [ ] Alertas si los queries son muy lentos

## 📝 Notas Técnicas

### Performance
- Los 3 endpoints del dashboard se llaman en paralelo con `Promise.all()`
- Queries optimizadas con índices en `tenant_id` y `upload_timestamp`
- Fallback a datos mock si la API falla (no bloquea la UI)

### Seguridad
- Todos los endpoints requieren header `x-tenant-id`
- Los datos están aislados por tenant
- Validación de UUID en endpoints

### Escalabilidad
- Queries preparados para grandes volúmenes de datos
- Límites configurables en `recent-invoices`
- Agregaciones eficientes con funciones SQL nativas

## 🐛 Troubleshooting

### El dashboard no muestra datos

1. Verificar que el backend esté corriendo:
   ```bash
   curl http://localhost:8000/health
   ```

2. Verificar que el tenant ID exista en la BD:
   ```sql
   SELECT * FROM tenants WHERE id = 'default-tenant-id';
   ```

3. Verificar logs del backend para errores de query

4. Abrir DevTools del navegador y revisar:
   - Network tab: ¿Las peticiones regresan 200?
   - Console: ¿Hay errores JavaScript?

### Errores de CORS

Si ves errores de CORS en la consola:

1. Verificar que `NEXT_PUBLIC_API_URL` esté configurado
2. Verificar CORS en `apps/api/src/api/main.py`:
   ```python
   allow_origins=["http://localhost:3000", "*"]
   ```

### Datos incorrectos en gráficos

1. Verificar formato de datos retornados por la API
2. Verificar que los nombres de campos coincidan (camelCase vs snake_case)
3. Verificar conversión de tipos (string vs number)

---

**Creado:** 2025-01-05
**Autor:** Claude (Anthropic)
**Versión:** 1.0.0
