# 📋 Resumen Completo del Proyecto - FacturIA

## 🎯 ¿De qué trata?

**FacturIA** es un **SaaS B2B** que automatiza el procesamiento de facturas para tiendas minoristas en Colombia (especialmente liquidadoras y pequeños comercios). El sistema procesa facturas usando **inteligencia artificial de AWS** y recomienda precios de venta con **Machine Learning**.

### Propuesta de Valor
- ⚡ **Velocidad:** Reduce el tiempo de procesamiento de 15 min a 2 min por factura
- 🎯 **Precisión:** >95% de exactitud con facturas colombianas
- 💰 **ROI:** 300%+ documentado
- 🤖 **Automatización:** ML para clasificación de productos y sugerencias de precio

---

## 🏗️ Arquitectura del Sistema

### **Stack Técnico**

**Backend:**
- **FastAPI** (Python 3.11) - API REST moderna y rápida
- **PostgreSQL** - Base de datos relacional con SQLAlchemy async
- **AWS Textract** - IA para extracción de texto de documentos
- **OpenCV** - Mejora de calidad de fotos móviles
- **Hugging Face Transformers** - Clasificación ML de productos

**Frontend:**
- **Next.js 15** - Framework React con SSR
- **TypeScript** - Tipado fuerte
- **Tailwind CSS** - Estilo moderno
- **Radix UI / shadcn/ui** - Componentes accesibles
- **Recharts** - Gráficos y analytics

**Infraestructura:**
- **Monorepo** con pnpm workspaces y Turborepo
- **Docker Compose** para desarrollo local
- **AWS S3** para almacenamiento de documentos
- **Alembic** para migraciones de DB

---

## 🔄 Pipeline de Procesamiento

```
📱 Foto/PDF → 🔧 OpenCV Enhancement → 📄 PDF →
🤖 AWS Textract → 📊 Datos Estructurados →
🧮 ML Pricing → 💰 Precio Manual → 🗄️ PostgreSQL
```

### Flujo Paso a Paso:

1. **Upload**: Usuario sube PDF o foto desde móvil
2. **Enhancement**: Si es foto, OpenCV mejora contraste/nitidez
3. **Conversión**: Foto mejorada → PDF optimizado
4. **S3 Storage**: Archivo se guarda en bucket AWS
5. **Textract**: AWS extrae campos estructurados (NIT, fecha, productos, totales)
6. **Normalización**: Sistema procesa datos colombianos específicos (IVA, CUFE, retenciones)
7. **ML Categorización**: Clasifica productos (zapatos, ropa, electrónicos, etc.)
8. **Precio Sugerido**: ML recomienda precio de venta según categoría + historial
9. **Pricing Manual**: Usuario ajusta precios con calculadora de margen
10. **Confirmación**: Actualiza inventario y productos en DB

---

## 📂 Estructura del Proyecto

```
aws-document-processing/
├── apps/
│   ├── api/                    # Backend Python
│   │   ├── src/
│   │   │   ├── api/           # FastAPI routes
│   │   │   ├── database/      # Modelos SQLAlchemy
│   │   │   ├── services/      # Lógica de negocio
│   │   │   │   ├── document_processing/  # Textract + OpenCV
│   │   │   │   ├── ml_services/           # Pricing ML
│   │   │   │   ├── duplicate_detection/   # Anti-duplicados
│   │   │   │   └── integrations/          # POS systems
│   │   │   └── core/          # Config, security, logging
│   │   └── tests/             # Tests pytest
│   └── web/                   # Frontend Next.js
│       ├── app/               # Pages (Next.js 13+)
│       ├── components/        # React components
│       └── lib/               # Utilidades + API client
├── packages/
│   ├── shared-types/          # TypeScript types compartidos
│   ├── python-utils/          # Utilidades Python compartidas
│   └── eslint-config/         # Config ESLint
├── infrastructure/            # Docker, Terraform
└── .github/workflows/         # CI/CD pipelines
```

---

## 🗄️ Base de Datos (PostgreSQL)

### Tablas Principales:

1. **`tenants`** - Multi-tenant
   - `tenant_id`, `company_name`, `nit`, `plan` (freemium/básico/premium)
   - `integration_config` (JSON) - Configuración POS

2. **`processed_invoices`** - Facturas procesadas
   - `invoice_id`, `tenant_id`, `status` (uploaded/processing/completed/failed)
   - Datos de factura: `invoice_number`, `issue_date`, `total_amount`
   - Info proveedor: `supplier_name`, `supplier_nit`
   - `textract_raw_response` (JSONB) - Respuesta completa de AWS
   - `pricing_status` - Estado del proceso de precio

3. **`invoice_line_items`** - Productos de facturas
   - `product_code`, `description`, `quantity`, `unit_price` (costo)
   - `sale_price` (precio de venta manual)
   - `markup_percentage` - Margen calculado
   - `is_priced` - ¿Ya tiene precio asignado?

4. **`products`** - Catálogo de productos
   - `tenant_id`, `product_code`, `description`
   - `current_stock`, `last_purchase_price`
   - Analytics: `total_purchased`, `total_amount`

5. **`suppliers`** - Directorio de proveedores

6. **`inventory_movement`** - Auditoría de movimientos

### Relaciones:

```
Tenant (1) ──→ (N) ProcessedInvoice
            ──→ (N) BillingRecord
            ──→ (N) Supplier
            ──→ (N) Product

ProcessedInvoice (1) ──→ (N) InvoiceLineItem
                    ──→ (N) BillingRecord
                    ──→ (N) InventoryMovement

Product (1) ──→ (N) InventoryMovement
           ──→ (N) DefectiveProduct
```

---

## 🤖 Características de ML

### 1. **Clasificación de Productos**
Usa **zero-shot learning** para categorizar productos automáticamente:

```python
"Zapatos Nike Air Max talla 42" → {
    'category': 'shoes',
    'confidence': 0.94,
    'margin_percentage': 55.0
}
```

**Categorías soportadas:**
- Electrónicos
- Ropa
- Calzado
- Alimentos
- Accesorios
- Juguetes
- Hogar
- Belleza
- Deportes
- Libros

### 2. **Precio Inteligente**
Recomienda precios considerando:
- Categoría del producto
- Margen típico de categoría
- Historial de pricing del tenant
- Patrones del proveedor
- Redondeo colombiano

```python
Costo: $28,000 COP → {
    'recommended_price': $43,000,  # Redondeado colombiano
    'confidence': 0.89,
    'margin_percentage': 53.6%,
    'reasoning': 'Categoría calzado + patrón proveedor'
}
```

**Reglas de margen:**
- Mínimo: 20%
- Máximo: 200%
- Por defecto: 30-35% según categoría

### 3. **Redondeo Colombiano**
Redondeo inteligente según cultura de precio local:

| Rango de Precio | Redondeo | Ejemplo |
|-----------------|----------|---------|
| > 10,000 COP | Mil más cercano (↑) | 10,800 → 11,000 |
| 1,000 - 10,000 | 500 más cercano | 1,250 → 1,500 |
| 100 - 1,000 | 100 más cercano | 450 → 500 |
| < 100 | 50 más cercano | 35 → 50 |

### 4. **Anti-Duplicados**
Detección de productos similares con fuzzy matching (90% umbral):

```python
"Nike AirMax 42" vs "Nike Air Max shoes size 42" → {
    'similarity_score': 0.92,
    'is_duplicate': True,
    'price_difference': -7000,  # Nuevo proveedor 15% más barato
    'recommendation': 'Mejor proveedor encontrado'
}
```

**Algoritmo:**
- Normalización de texto (lowercase, quitar acentos)
- Fuzzy string matching (RapidFuzz)
- Threshold configurable (default: 90%)
- Considera: descripción, código de producto, proveedor

---

## 📡 API Principal

Base URL: `http://localhost:8000/api/v1`

### Endpoints Clave:

#### **Procesamiento de Facturas**
```
POST   /invoices/upload              # Subir PDF directo
POST   /invoices/upload-photo        # Subir foto móvil con enhancement
GET    /invoices/{id}/status         # Estado de procesamiento
GET    /invoices/{id}/data           # Datos extraídos estructurados
GET    /invoices                     # Listar facturas del tenant
```

#### **Pricing Manual**
```
GET    /invoices/{id}/pricing        # Obtener datos para interfaz de precio
POST   /invoices/{id}/pricing        # Guardar precios de venta
POST   /invoices/{id}/confirm-pricing # Confirmar y actualizar inventario
```

#### **Anti-Duplicados**
```
POST   /invoices/{id}/check-duplicates    # Detectar productos similares
POST   /invoices/{id}/resolve-duplicates  # Resolver conflictos
```

#### **Integraciones POS**
```
GET    /invoices/{id}/export-mayasis      # Exportar CSV para Mayasis
POST   /invoices/{id}/export-to-pos       # Exportar a POS genérico
POST   /integrations/sync-inventory       # Sincronizar inventario
```

#### **ML Testing (Development)**
```
POST   /invoices/test-ml-classification   # Probar clasificación ML
POST   /invoices/test-price-rounding      # Probar redondeo colombiano
```

### Headers Requeridos:
```
x-tenant-id: {tenant_id}
Content-Type: application/json
```

---

## 🎨 Frontend (Next.js)

### Stack Técnico Frontend
**Ubicación:** `apps/web/`

**Framework & Core:**
- **Next.js 15.2.4** - React framework con App Router
- **React 18.3** - UI library
- **TypeScript 5.9** - Type safety
- **Tailwind CSS 3.4** - Utility-first CSS

**UI Components:**
- **Radix UI** - Headless components accesibles (40+ componentes)
- **shadcn/ui** - Componentes pre-styled sobre Radix
- **Lucide React** - Iconos (Search, Upload, FileText, Package, etc.)
- **Recharts** - Gráficos y visualizaciones

**Forms & Validation:**
- **React Hook Form 7.69** - Form state management
- **Zod 3.24** - Schema validation
- **@hookform/resolvers** - Integration RHF + Zod

**Theming:**
- **next-themes 0.4** - Dark/light mode
- **tailwindcss-animate** - Animaciones

**Estado & Data Fetching:**
- Custom API client (Axios-based)
- React hooks para state management
- Polling automático para status updates

### Arquitectura de Páginas

#### 1. **Dashboard Principal** (`apps/web/app/page.tsx` - 1,320 líneas)

**Sistema de Tabs:**
El dashboard usa un sistema de navegación por tabs con 6 secciones principales:

```tsx
const sidebarItems = [
  { name: "Dashboard", icon: BarChart3 },
  { name: "Facturas", icon: FileText },
  { name: "Inventario", icon: Package },
  { name: "Proveedores", icon: Users },
  { name: "Reportes", icon: BarChart3 },
  { name: "Configuración", icon: Settings }
]
```

**Tab 1: Dashboard Overview**
- **KPI Cards:**
  ```tsx
  - Total Facturas Procesadas
  - Monto Total Procesado (COP)
  - Tasa de Éxito (%)
  - Proveedores Activos
  ```

- **Gráficos Recharts:**
  - **LineChart:** Volumen de compras (últimos 12 meses)
  - **BarChart:** Tendencia de márgenes por categoría
  - **AreaChart:** Proyección de inventario

- **Facturas Recientes:**
  - Lista de últimas 5 facturas
  - Status badges (pending/completed/failed)
  - Quick actions (Ver, Pricing, Export)

**Tab 2: Facturas** (Componente: `InvoiceManagementPage`)
- **Upload Zone:**
  ```tsx
  // Drag & Drop implementation
  const handleDrop = (e) => {
    const files = e.dataTransfer.files
    // Acepta PDF y fotos (jpg, png)
    // Upload a backend via facturaAPI
  }
  ```

- **Lista de Facturas:**
  - Fetch desde API: `facturaAPI.listInvoices(limit, offset)`
  - Paginación: 9 facturas por página
  - Filtros:
    - **Búsqueda:** Por número de factura o proveedor
    - **Estado:** all/uploaded/processing/completed/failed
    - **Proveedor:** Dropdown con proveedores únicos
    - **Fecha:** 7 días/mes/trimestre/año

- **Detalles de Factura:**
  - Modal con información completa
  - Datos del proveedor (NIT, nombre, dirección)
  - Line items extraídos
  - Totales (subtotal, IVA, total)

- **Modal de Pricing:**
  ```tsx
  // Calculadora de margen en tiempo real
  const calculateMargin = (cost, salePrice) => {
    return ((salePrice - cost) / cost) * 100
  }

  // Validación
  const validatePrice = (cost, salePrice) => {
    if (salePrice <= cost) {
      return "Precio de venta debe ser mayor al costo"
    }
  }
  ```

  **Features del modal:**
  - Tabla editable con todos los line items
  - Input para precio de venta por producto
  - Cálculo automático de margen (%)
  - Sugerencias de precio (ML)
  - Aplicar margen global a todos los productos
  - Validación en tiempo real
  - Preview de cambios

- **Polling de Estado:**
  ```tsx
  useEffect(() => {
    const interval = setInterval(async () => {
      const status = await facturaAPI.getInvoiceStatus(invoiceId)
      setInvoiceStatus(status)
      if (status === 'completed') {
        clearInterval(interval)
        // Enable pricing
      }
    }, 2000) // Poll cada 2 segundos
  }, [invoiceId])
  ```

**Tab 3: Inventario** (Componente: `InventoryPage`)
- **Tabla de Productos:**
  - Código, Descripción, Categoría
  - Stock actual vs mínimo
  - Precio de compra y venta
  - Margen (%)
  - Status (normal/low/out)

- **Alertas de Stock:**
  - Badge rojo para stock agotado
  - Badge amarillo para stock bajo
  - Contador de productos con stock crítico

- **Filtros:**
  - Búsqueda por descripción/código
  - Categoría (Textiles, Calzado, Accesorios)
  - Estado de stock (normal/bajo/agotado)

- **Acciones:**
  - Editar producto
  - Ver historial de movimientos
  - Exportar a CSV

**Tab 4: Proveedores** (Componente: `SupplierManagementPage`)
- **Directorio de Proveedores:**
  - Nombre comercial, NIT
  - Contacto (teléfono, email)
  - Dirección, ciudad
  - Total comprado (COP)
  - Número de facturas

- **Analytics por Proveedor:**
  - Volumen de compras (últimos 6 meses)
  - Productos más comprados
  - Margen promedio obtenido
  - Productos activos

- **Gestión:**
  - Agregar nuevo proveedor
  - Editar información
  - Ver todas las facturas del proveedor

**Tab 5: Reportes** (Componente: `ReportsAnalyticsPage`)
- **KPIs Principales:**
  - Total de facturas procesadas
  - Valor total de compras
  - Margen promedio
  - Top categorías

- **Gráficos Avanzados:**
  - **Monthly Invoices Chart:** Facturas y valor por mes
  - **Top Suppliers Chart:** Proveedores con más volumen
  - **Best Selling Products:** Productos más vendidos con margen

- **Tabla de Mejores Productos:**
  - Nombre, Categoría
  - Unidades vendidas
  - Revenue generado
  - Margen (%)
  - Proveedor

- **Exportar Reportes:**
  - PDF/Excel con datos seleccionados
  - Filtros por fecha personalizado

**Tab 6: Configuración** (Componente: `ConfigurationPage`)
- **Configuración de Tenant:**
  - Información de la empresa
  - Logo y branding
  - Plan actual (Freemium/Básico/Premium)

- **Integraciones POS:**
  - Mayasis (activo/inactivo)
  - Square (en desarrollo)
  - Configuración de credenciales
  - Auto-sync settings

- **Preferencias de Usuario:**
  - Theme (dark/light/auto)
  - Idioma (español)
  - Notificaciones

- **Configuración de Pricing:**
  - Margen por defecto (%)
  - Márgenes por categoría
  - Reglas de redondeo colombiano
  - ML pricing (activar/desactivar)

#### 2. **Landing Page** (`apps/web/app/landing/page.tsx`)

**Estructura de Marketing:**

**Hero Section:**
```tsx
<h1>Procesa Facturas en Segundos con IA</h1>
<p>De 15 minutos a 2 minutos por factura</p>
<Button>Comenzar Gratis</Button>
<Badge>95%+ Precisión</Badge>
```

**Features Section:**
- Procesamiento Inteligente (AWS Textract + CV)
- Actualización Automática de Inventario
- Integración POS (Mayasis, Siigo, etc.)

**Proceso en 3 Pasos:**
1. Sube tu factura (foto o PDF)
2. IA extrae los datos
3. Inventario actualizado

**Testimonios:**
- 3 testimonials con rating ⭐⭐⭐⭐⭐
- Clientes reales (Almacén Medellín JA, Melos Paisas)

**Pricing Plans:**
```tsx
const pricing = [
  {
    name: "Founders Plan",
    price: "$285,000 COP/mes de por vida",
    badge: "Solo primeros 15 clientes",
    features: [
      "Facturas ilimitadas",
      "ML pricing inteligente",
      "Todas las integraciones POS",
      "Soporte prioritario",
      "Precio congelado de por vida",
      "Acceso early a nuevas features",
      "Influencia en roadmap"
    ],
    highlight: true,
    savings: "Ahorra $180,000/mes vs Básico"
  },
  {
    name: "Básico",
    price: "$465,000 COP/mes",
    badge: "Precio regular",
    features: [
      "Facturas ilimitadas",
      "ML pricing inteligente",
      "Todas las integraciones POS",
      "Soporte prioritario"
    ]
  },
  {
    name: "Profesional",
    price: "$785,000 COP/mes",
    features: [
      "Todo lo de Básico",
      "Multi-usuario con roles",
      "Analytics avanzados",
      "Reportes personalizados",
      "Soporte telefónico"
    ]
  },
  {
    name: "Empresarial",
    price: "Personalizado",
    features: [
      "Todo lo de Profesional",
      "API dedicada",
      "Soporte 24/7",
      "SLA 99.95%",
      "Account Manager",
      "Onboarding personalizado"
    ]
  }
]
```

**Estrategia de Founders Plan:**
- **Founders Price:** $285,000 COP/mes de por vida (solo primeros 15 clientes)
- **Beneficios:**
  - Precio congelado permanentemente
  - Acceso early a nuevas features
  - Influencia en roadmap del producto
  - Badge "Founder" en plataforma
  - Soporte directo con el equipo

- **Precio Básico (Regular):** $465,000 COP/mes (después de los 15 Founders)
- **Ahorro Founders:** $180,000 COP/mes = $2,160,000 COP/año
- **ROI para el cliente:**
  - Si procesa 50 facturas/mes a 15 min c/u = 750 min ahorrados
  - A $30,000 COP/hora = $375,000 COP ahorrados/mes
  - ROI mensual: 131% sobre precio Founders
  - Payback period: <1 mes

**FAQ Section:**
- ¿Cómo funciona?
- ¿Qué formatos acepta?
- ¿Es seguro?
- ¿Cómo se integra con mi POS?

**Footer:**
- Contacto
- Redes sociales
- Legal (Términos, Privacidad)

#### 3. **Login Page** (`apps/web/app/login/page.tsx`)
- Formulario de autenticación
- OAuth providers (Google, Microsoft)
- Registro de nuevos usuarios
- Recuperación de contraseña

### Componentes UI (50+ componentes)
**Ubicación:** `apps/web/components/ui/`

**Formularios:**
- `input.tsx` - Text input con variants
- `textarea.tsx` - Multi-line input
- `select.tsx` - Dropdown select (Radix)
- `checkbox.tsx` - Checkbox con label
- `radio-group.tsx` - Radio buttons
- `switch.tsx` - Toggle switch
- `slider.tsx` - Range slider
- `form.tsx` - Form wrapper con validación
- `calendar.tsx` - Date picker
- `input-otp.tsx` - OTP input

**Display:**
- `card.tsx` - Card container (Header, Content, Footer)
- `badge.tsx` - Status badges con variants
- `alert.tsx` - Alert messages (info/warning/error)
- `separator.tsx` - Horizontal/vertical divider
- `table.tsx` - Data table components
- `tabs.tsx` - Tab navigation
- `accordion.tsx` - Expandable sections
- `avatar.tsx` - User avatar con fallback
- `progress.tsx` - Progress bar
- `skeleton.tsx` - Loading placeholders

**Navegación:**
- `sidebar.tsx` - Sidebar navigation
- `breadcrumb.tsx` - Breadcrumb trail
- `pagination.tsx` - Page navigation
- `navigation-menu.tsx` - Menu con submenus
- `command.tsx` - Command palette (⌘K)

**Dialogs & Overlays:**
- `dialog.tsx` - Modal dialog
- `sheet.tsx` - Slide-out panel
- `drawer.tsx` - Bottom drawer (mobile)
- `alert-dialog.tsx` - Confirmation dialog
- `popover.tsx` - Floating popover
- `tooltip.tsx` - Hover tooltip
- `hover-card.tsx` - Rich hover content
- `context-menu.tsx` - Right-click menu
- `dropdown-menu.tsx` - Dropdown actions

**Gráficos:**
- `chart.tsx` - Recharts wrapper
  - LineChart - Líneas temporales
  - BarChart - Barras comparativas
  - AreaChart - Áreas apiladas
  - PieChart - Gráfico circular (planned)

**Otros:**
- `button.tsx` - Buttons con variants (default/destructive/outline/ghost)
- `toast.tsx` / `sonner.tsx` - Notifications
- `carousel.tsx` - Image carousel
- `scroll-area.tsx` - Custom scrollbar
- `resizable.tsx` - Resizable panels
- `menubar.tsx` - Menu bar
- `toggle.tsx` / `toggle-group.tsx` - Toggle buttons
- `collapsible.tsx` - Collapsible content

### API Client Architecture
**Ubicación:** `apps/web/lib/api/`

**Structure:**
```
lib/api/
├── index.ts                    # Exports principales
├── facturaAPI.ts              # Wrapper para backward compatibility
├── usePricingWorkflow.ts      # React hook para pricing flow
└── ../../src/lib/api/
    ├── client.ts              # Base API client (Axios)
    └── endpoints/
        └── invoices.ts        # Invoice endpoints
```

**Base Client** (`client.ts`):
```typescript
class ApiClient {
  private baseURL = 'http://localhost:8000/api/v1'
  private tenantId = 'test-tenant'

  async request(method, endpoint, data) {
    const response = await axios({
      method,
      url: `${this.baseURL}${endpoint}`,
      headers: {
        'x-tenant-id': this.tenantId,
        'Content-Type': 'application/json'
      },
      data
    })
    return response.data
  }
}
```

**Invoice Endpoints** (`endpoints/invoices.ts`):
```typescript
export const invoicesApi = {
  // Upload operations
  uploadInvoice: (file: File) => FormData POST,
  uploadPhoto: (file: File) => FormData POST,

  // Status & data
  getStatus: (id: string) => GET /invoices/{id}/status,
  getData: (id: string) => GET /invoices/{id}/data,

  // Pricing workflow
  getPricingData: (id: string) => GET /invoices/{id}/pricing,
  setPricing: (id: string, items: PricingItem[]) => POST,
  confirmPricing: (id: string) => POST,

  // List operations
  list: (limit: number, offset: number) => GET /invoices,
  delete: (id: string) => DELETE /invoices/{id}
}
```

**Pricing Workflow Hook** (`usePricingWorkflow.ts`):
```typescript
export function usePricingWorkflow(invoiceId: string) {
  const [pricingData, setPricingData] = useState<PricingInfo | null>(null)
  const [loading, setLoading] = useState(false)

  const loadPricingData = async () => {
    const data = await facturaAPI.getPricingData(invoiceId)
    setPricingData(data)
  }

  const savePricing = async (items: PricingItem[]) => {
    await facturaAPI.setPricing(invoiceId, items)
  }

  const confirmPricing = async () => {
    await facturaAPI.confirmPricing(invoiceId)
    // Updates inventory in backend
  }

  return { pricingData, loadPricingData, savePricing, confirmPricing, loading }
}
```

**Ejemplo de Uso Completo:**
```typescript
// En un componente React
import { facturaAPI, usePricingWorkflow } from '@/lib/api'

function InvoicePricingModal({ invoiceId }) {
  const { pricingData, loadPricingData, savePricing, confirmPricing } =
    usePricingWorkflow(invoiceId)

  useEffect(() => {
    loadPricingData()
  }, [invoiceId])

  const handleSave = async () => {
    await savePricing(editedItems)
    toast.success('Precios guardados')
  }

  const handleConfirm = async () => {
    await confirmPricing()
    toast.success('Inventario actualizado')
  }

  return (
    <Modal>
      <Table data={pricingData?.line_items} />
      <Button onClick={handleSave}>Guardar</Button>
      <Button onClick={handleConfirm}>Confirmar</Button>
    </Modal>
  )
}
```

### Utilidades de Frontend

**Pricing Utilities** (`lib/simplePricing.ts`):
```typescript
// Calculate sale price with markup
export function calculatePrice(cost: number, markup: number = 35): number {
  return cost * (1 + markup / 100)
}

// Format to Colombian Pesos
export function formatPrice(price: number): string {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
  }).format(price)
}

// Markup configuration hook
export function useMarkupConfig() {
  return {
    defaultMarkup: 35,
    categoryMarkups: {
      'textiles': 30,
      'calzado': 55,
      'accesorios': 45
    }
  }
}
```

### User Experience Features

**1. Real-time Feedback:**
- Toast notifications para todas las acciones
- Loading spinners durante operaciones async
- Skeleton screens durante carga inicial
- Progress bars para uploads

**2. Error Handling:**
```typescript
try {
  await facturaAPI.uploadInvoice(file)
} catch (error) {
  if (error.response?.status === 413) {
    toast.error('Archivo muy grande. Máximo 10MB')
  } else if (error.response?.status === 400) {
    toast.error('Formato de archivo inválido')
  } else {
    toast.error('Error al subir factura. Intenta nuevamente')
  }
}
```

**3. Optimistic Updates:**
- UI se actualiza antes de confirmación del servidor
- Rollback automático si falla

**4. Accessibility:**
- Todos los componentes Radix son accesibles
- Keyboard navigation
- ARIA labels
- Focus management

**5. Performance:**
- Code splitting por ruta (Next.js automático)
- Lazy loading de componentes pesados
- Image optimization con Next/Image
- Memoization de cálculos costosos

**6. Responsive Design:**
```tsx
// Mobile-first approach
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
  {/* Cards adjust based on screen size */}
</div>

// Mobile drawer en lugar de modal
const isMobile = useMediaQuery('(max-width: 768px)')
{isMobile ? <Drawer /> : <Dialog />}
```

---

## 🔐 Multi-Tenant

### Arquitectura Multi-Tenant:
- **Header-based isolation**: Cada request requiere `x-tenant-id`
- **Catálogos separados** por tenant (productos, proveedores, facturas)
- **Configuraciones personalizadas** por tenant
- **Tracking de uso** y límites por plan

### Planes Disponibles:
```typescript
enum TenantPlan {
  FREEMIUM = 'freemium',    // 10 facturas/mes
  BASIC = 'basic',          // 100 facturas/mes
  PREMIUM = 'premium'       // Ilimitado
}
```

### Configuración por Tenant:
```json
{
  "integration_config": {
    "pos_system": "mayasis",
    "auto_sync": true,
    "default_margin": 35.0,
    "enable_ml_pricing": true,
    "pricing_rules": {
      "min_markup": 20,
      "max_markup": 200,
      "apply_rounding": true
    }
  }
}
```

---

## 🔧 Servicios Backend

### 1. Document Processing Service
**Ubicación:** `apps/api/src/services/document_processing/`

**invoice_processor.py** - Orquestación principal:
```python
async def upload_and_process_invoice(file, tenant_id):
    # 1. Crear registro en DB
    invoice = await create_invoice_record(tenant_id)

    # 2. Upload a S3
    s3_key = await upload_to_s3(file, invoice.id)

    # 3. Procesar con Textract
    textract_data = await textract_service.analyze_invoice(s3_key)

    # 4. Extraer y normalizar datos
    invoice_data = await extract_invoice_data(textract_data)

    # 5. Guardar en DB
    await save_invoice_data(invoice.id, invoice_data)

    # 6. ML categorización (background)
    await classify_products(invoice.id)

    return invoice
```

### 2. Textract Service
**Ubicación:** `apps/api/src/services/document_processing/textract/`

**Capacidades:**
- Extracción de tablas (line items)
- Key-value pairs (campos del formulario)
- Texto plano con OCR
- Confidence scores

**Campos extraídos específicos para Colombia:**
- NIT (proveedor y cliente)
- Número de factura
- Fecha de emisión y vencimiento
- IVA (tasa y monto)
- Retenciones (ICA, IVA, Fuente)
- CUFE (Código Único de Factura Electrónica)
- Resolución DIAN

### 3. ML Services
**Ubicación:** `apps/api/src/services/ml_services/`

**pricing_engine.py** - Motor de recomendaciones:
```python
async def recommend_price(
    product_description: str,
    cost_price: float,
    tenant_id: str,
    supplier_id: str = None
) -> PricingRecommendation:
    # 1. Clasificar categoría
    category = await classify_product(product_description)

    # 2. Obtener margen típico de categoría
    category_margin = get_category_margin(category)

    # 3. Analizar historial del tenant
    historical_margin = await get_tenant_avg_margin(tenant_id, category)

    # 4. Considerar proveedor
    supplier_margin = await get_supplier_margin(supplier_id, category)

    # 5. Calcular precio sugerido
    suggested_margin = weighted_average([
        (category_margin, 0.4),
        (historical_margin, 0.4),
        (supplier_margin, 0.2)
    ])

    suggested_price = cost_price * (1 + suggested_margin)

    # 6. Aplicar redondeo colombiano
    final_price = apply_colombian_rounding(suggested_price)

    return PricingRecommendation(
        recommended_price=final_price,
        confidence=calculate_confidence(...),
        margin_percentage=suggested_margin * 100,
        reasoning=f"Based on {category} category pattern"
    )
```

### 4. Integration Service
**Ubicación:** `apps/api/src/services/integrations/`

**Integraciones soportadas:**

**Mayasis POS:**
```python
# Exportar CSV con formato Mayasis
csv_data = await export_to_mayasis(invoice_id)
# Columns: Código, Descripción, Costo, Precio, Stock, Categoría
```

**Square POS:**
```python
# API REST integration
await square_integration.sync_products(invoice_id)
# Usa Square Catalog API
```

**Generic CSV:**
```python
# CSV configurable para cualquier POS
csv_data = await export_generic_csv(
    invoice_id,
    columns=['code', 'description', 'price'],
    delimiter=';'
)
```

---

## 🚀 Cómo Correr el Proyecto

### Requisitos:
- Node.js >= 20.0.0
- Python >= 3.11.0
- pnpm >= 8.0.0
- Docker & Docker Compose
- AWS Account (para Textract en producción)

### Setup Inicial:

```bash
# 1. Clonar repo
git clone https://github.com/EdwLearn/aws-document-processing.git
cd aws-document-processing

# 2. Instalar dependencias Node.js
pnpm install

# 3. Configurar entorno
cp .env.example .env
# Editar .env con tus configuraciones

# 4. Levantar servicios Docker
docker-compose up -d postgres redis localstack

# 5. Setup backend Python
cd apps/api
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt

# 6. Migrar base de datos
cd ../..
pnpm db:migrate

# 7. (Opcional) Seed data de prueba
pnpm db:seed
```

### Desarrollo:

**Opción 1: Todo en paralelo (Turborepo)**
```bash
pnpm dev
# Levanta API + Web simultáneamente
```

**Opción 2: Servicios separados**
```bash
# Terminal 1: Backend
pnpm dev:api
# API en http://localhost:8000
# Docs en http://localhost:8000/docs

# Terminal 2: Frontend
pnpm dev:web
# Web en http://localhost:3000
```

### Testing:

```bash
# Backend tests (pytest)
pnpm test:api
cd apps/api && pytest -v
pytest tests/unit -v           # Solo unit tests
pytest tests/integration -v    # Solo integration tests
pytest --cov                   # Con coverage

# Frontend tests (Vitest)
pnpm test:web
cd apps/web && pnpm test

# E2E tests (Playwright)
pnpm test:e2e
cd apps/web && pnpm test:e2e
```

### Linting & Formatting:

```bash
# Lint todo
pnpm lint

# Format todo
pnpm format

# Type checking
pnpm type-check
```

### Docker (Producción):

```bash
# Development
pnpm docker:dev

# Testing
pnpm docker:test

# Production
pnpm docker:prod
```

---

## 🧪 Testing

### Backend Testing (pytest)
**Ubicación:** `apps/api/tests/`

**Configuración:**
- `pytest.ini` - Config con coverage >80%, markers, asyncio
- `.coveragerc` - Coverage config con exclusiones
- `conftest.py` - Fixtures compartidos

**Fixtures disponibles:**
```python
@pytest.fixture
async def test_db():
    # SQLite in-memory para tests

@pytest.fixture
async def test_client():
    # FastAPI TestClient

@pytest.fixture
def mock_s3():
    # Mock S3 con moto

@pytest.fixture
def mock_textract():
    # Mock AWS Textract responses

@pytest.fixture
def sample_invoice_data():
    # Factory para datos de prueba
```

**Estructura:**
```
apps/api/tests/
├── unit/              # Tests unitarios rápidos
│   ├── test_pricing_engine.py
│   ├── test_category_classifier.py
│   └── test_product_matching.py
├── integration/       # Tests con DB/AWS
│   ├── test_invoice_processing.py
│   ├── test_textract_integration.py
│   └── test_pos_integrations.py
└── fixtures/          # Data fixtures
    └── sample_invoices.json
```

### Frontend Testing
**Ubicación:** `apps/web/tests/`

**Vitest (Unit tests):**
```typescript
// Ejemplo: tests/components/PricingModal.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { PricingModal } from '@/components/PricingModal'

describe('PricingModal', () => {
  it('calculates margin correctly', () => {
    render(<PricingModal invoice={mockInvoice} />)

    const costInput = screen.getByLabelText('Cost Price')
    const saleInput = screen.getByLabelText('Sale Price')

    fireEvent.change(costInput, { target: { value: '10000' } })
    fireEvent.change(saleInput, { target: { value: '15000' } })

    expect(screen.getByText('50%')).toBeInTheDocument()
  })
})
```

**Playwright (E2E tests):**
```typescript
// Ejemplo: tests/e2e/invoice-upload.spec.ts
import { test, expect } from '@playwright/test'

test('can upload and process invoice', async ({ page }) => {
  await page.goto('http://localhost:3000')

  // Upload file
  const fileInput = page.locator('input[type="file"]')
  await fileInput.setInputFiles('fixtures/sample-invoice.pdf')

  // Wait for processing
  await expect(page.locator('.status-completed')).toBeVisible({ timeout: 30000 })

  // Open pricing modal
  await page.click('button:has-text("Set Prices")')

  // Verify pricing interface
  await expect(page.locator('.pricing-modal')).toBeVisible()
})
```

---

## 📊 Estado del Proyecto

### ✅ Completado (MVP Funcional)

**Core Features:**
- ✅ Upload de PDF y fotos móviles
- ✅ Procesamiento con AWS Textract
- ✅ Extracción de campos colombianos (NIT, IVA, CUFE)
- ✅ Enhancement de imágenes con OpenCV
- ✅ Multi-tenant completo
- ✅ Pricing manual con calculadora
- ✅ Analytics básicos
- ✅ Dashboard responsivo

**ML Features:**
- ✅ Clasificación de productos (zero-shot)
- ✅ Recomendaciones de precio
- ✅ Redondeo colombiano inteligente
- ✅ Detección de duplicados (fuzzy matching)

**Infraestructura:**
- ✅ Monorepo con Turborepo
- ✅ Docker Compose para desarrollo
- ✅ CI/CD con GitHub Actions
- ✅ Tests con pytest y Vitest
- ✅ Migraciones con Alembic

### 🔄 En Desarrollo

- 🔄 UI para resolución de duplicados
- 🔄 Integración Mayasis completa (CSV + N8N)
- 🔄 Integración Square POS (API REST)
- 🔄 Mejoras en frontend de pricing
- 🔄 Auto-actualización de inventario

### 🎯 Próximos 2 Meses

**Roadmap Q1 2025:**

**Semana 1-2:**
- Completar anti-duplicados con UI
- Auto-update inventory en confirmación de pricing
- Deploy staging para cliente piloto

**Semana 3-4:**
- Integración Mayasis producción
- Onboarding "Almacén Medellín JA"
- Dashboard analytics avanzado

**Mes 2:**
- Integración Square POS
- Mobile app (React Native)
- Bulk invoice processing
- Sistema de webhooks para integraciones custom

**Objetivos:**
- 🎯 Primer cliente pagador
- 🎯 100 facturas procesadas en producción
- 🎯 ROI documentado >300%
- 🎯 2-3 integraciones POS funcionando

---

## 🔐 Seguridad

### Medidas Implementadas:

**Backend:**
- Multi-tenant isolation con `x-tenant-id` header
- UUIDs para IDs (no secuenciales)
- SQL injection prevention (SQLAlchemy ORM)
- Input validation (Pydantic)
- Password hashing (bcrypt)
- JWT authentication (preparado)
- CORS configurado

**Infraestructura:**
- Secrets en variables de entorno
- AWS credentials con IAM roles
- Database passwords rotables
- HTTPS en producción
- Security scanning con Bandit, Safety, Semgrep

**Compliance:**
- Almacenamiento de facturas para auditoría
- Logs estructurados con trazabilidad
- GDPR-ready (deletion capabilities)

---

## 💾 Backup & Disaster Recovery

### Estrategia de Backup:

**Base de Datos:**
- Backups automáticos diarios (PostgreSQL)
- Retention: 30 días
- Point-in-time recovery

**Documentos (S3):**
- Versioning habilitado
- Lifecycle policies (90 días → Glacier)
- Cross-region replication (producción)

**Código:**
- Git como source of truth
- Tags para releases
- CI/CD rollback automático

---

## 📈 Métricas & Monitoring

### Métricas Técnicas:
- **Accuracy:** >95% con facturas colombianas
- **Processing time:** <30s por factura
- **API response:** <200ms endpoints de consulta
- **Uptime target:** 99.9%

### Métricas de Negocio:
- Facturas procesadas (total, mes actual)
- Tiempo ahorrado por factura (15 min → 2 min)
- ROI calculado por tenant
- Productos catalogados
- Margen promedio

### Monitoring (Planeado):
- Sentry para error tracking
- CloudWatch para AWS metrics
- Prometheus + Grafana para métricas custom
- Health checks en endpoints críticos

---

## 🤝 Contribución

### Workflow de Desarrollo:

```bash
# 1. Fork del repo
git clone https://github.com/tu-usuario/aws-document-processing.git

# 2. Crear feature branch
git checkout -b feature/nueva-funcionalidad

# 3. Hacer cambios y commits
git commit -m "feat: agregar nueva funcionalidad"

# 4. Push a tu fork
git push origin feature/nueva-funcionalidad

# 5. Crear Pull Request
```

### Convención de Commits:

```
feat: nueva feature
fix: bug fix
docs: documentación
refactor: refactorización sin cambios funcionales
test: agregar tests
chore: tareas de mantenimiento
perf: mejoras de performance
style: cambios de estilo/formato
```

### Code Review Checklist:
- ✅ Tests pasan (CI green)
- ✅ Coverage >80%
- ✅ Linting sin errores
- ✅ Type checking OK
- ✅ Documentación actualizada
- ✅ No secrets en código

---

## 📞 Soporte

### Recursos:
- **Documentación:** Este archivo + README.md
- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **Issues:** GitHub Issues
- **Email:** [Tu email de soporte]

### Problemas Comunes:

**Error: "AWS credentials not found"**
```bash
# Configurar AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
# O usar LocalStack para desarrollo local
```

**Error: "Database connection failed"**
```bash
# Verificar que PostgreSQL está corriendo
docker-compose ps
# Reiniciar servicios
docker-compose restart postgres
```

**Error: "Port 3000 already in use"**
```bash
# Matar proceso usando el puerto
lsof -ti:3000 | xargs kill -9
# O cambiar puerto en .env
PORT=3001 pnpm dev:web
```

---

## 📚 Referencias

### Documentación Técnica:
- **FastAPI:** https://fastapi.tiangolo.com
- **Next.js:** https://nextjs.org/docs
- **SQLAlchemy:** https://docs.sqlalchemy.org
- **AWS Textract:** https://docs.aws.amazon.com/textract
- **Pydantic:** https://docs.pydantic.dev

### Librerías ML:
- **Transformers:** https://huggingface.co/docs/transformers
- **OpenCV:** https://docs.opencv.org
- **RapidFuzz:** https://maxbachmann.github.io/RapidFuzz

### Infraestructura:
- **Turborepo:** https://turbo.build/repo/docs
- **pnpm:** https://pnpm.io/workspaces
- **Docker Compose:** https://docs.docker.com/compose
- **Alembic:** https://alembic.sqlalchemy.org

---

## 📝 Notas de Versión

### v2.0.0 (Actual)
- ✅ Migración a monorepo
- ✅ Frontend Next.js completo
- ✅ ML pricing engine
- ✅ Multi-tenant architecture
- ✅ Integraciones POS (en desarrollo)

### v1.0.0 (MVP Original)
- ✅ Upload y procesamiento básico
- ✅ Textract integration
- ✅ Pricing manual simple
- ✅ Single-tenant

---

**Última actualización:** 2026-01-05
**Versión:** 2.0.0
**Mantenedor:** [Tu nombre/equipo]
