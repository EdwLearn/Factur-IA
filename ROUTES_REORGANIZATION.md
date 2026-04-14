# 🗺️ Reorganización de Rutas - FacturIA

## 📋 Resumen

Se reorganizó la estructura de rutas del frontend para seguir el flujo lógico de un SaaS, donde los usuarios primero ven la landing page con información del producto antes de hacer login y acceder al dashboard.

## 🔄 Cambios Realizados

### Antes (❌ Estructura Antigua)

```
/                  → Dashboard (directo a la app)
/landing           → Landing Page del SaaS
/login             → Página de Login
```

**Problema:** Los usuarios iban directo al dashboard sin ver primero la información del producto.

### Después (✅ Estructura Nueva)

```
/                  → Landing Page del SaaS (inicio)
/login             → Página de Login
/dashboard         → Dashboard de la aplicación
```

**Beneficio:** Flujo lógico típico de un SaaS: Landing → Login → App

## 📁 Estructura de Archivos

### Landing Page (Raíz `/`)
**Archivo:** [`apps/web/app/page.tsx`](apps/web/app/page.tsx)

**Contenido:**
- Hero section con propuesta de valor
- Features (Procesamiento IA, Integración POS, etc.)
- Proceso paso a paso
- Testimonios de clientes
- Planes de pricing
- Sección de contacto
- Footer con links útiles

**Links importantes:**
- "Iniciar Sesión" → `/login`
- "Comenzar Gratis" → `/dashboard`
- "Probar Ahora" → `/dashboard`

### Login Page (`/login`)
**Archivo:** [`apps/web/app/login/page.tsx`](apps/web/app/login/page.tsx)

**Contenido:**
- Formulario de login (email + password)
- Botón "Volver al inicio" → `/`
- Opciones de login social (Google, Facebook)
- Link "Comienza tu prueba gratuita" → `/dashboard`

**Funcionalidad actual:**
```typescript
const handleLogin = (e: React.FormEvent) => {
  e.preventDefault()
  // Simulate login - redirect to dashboard
  window.location.href = "/dashboard"
}
```

**⚠️ TODO:** Integrar con sistema de autenticación real (JWT, OAuth, etc.)

### Dashboard (`/dashboard`)
**Archivo:** [`apps/web/app/dashboard/page.tsx`](apps/web/app/dashboard/page.tsx)

**Contenido:**
- Dashboard completo de FacturIA
- Sidebar con navegación (Dashboard, Facturas, Inventario, etc.)
- Métricas en tiempo real conectadas al backend
- Upload de facturas
- Gráficos y analytics
- Gestión de precios

**Conexión con Backend:**
- ✅ GET `/api/v1/dashboard/metrics`
- ✅ GET `/api/v1/dashboard/recent-invoices`
- ✅ GET `/api/v1/dashboard/analytics`

## 🚀 Flujo de Usuario

### 1. Visitante Nuevo
```
Usuario visita localhost:3000
    ↓
Landing Page (/)
    ↓
Ve features, pricing, testimonios
    ↓
Click en "Iniciar Sesión" o "Comenzar Gratis"
    ↓
Login Page (/login)
    ↓
Ingresa credenciales
    ↓
Redirigido a /dashboard
```

### 2. Usuario con Sesión Activa
```
Usuario visita localhost:3000
    ↓
Landing Page (/)
    ↓
Detecta sesión activa (TODO)
    ↓
Auto-redirect a /dashboard
```

### 3. Usuario en el Dashboard
```
Usuario en /dashboard
    ↓
Trabaja con la aplicación
    ↓
Click en "Cerrar Sesión"
    ↓
Redirigido a / (Landing)
```

## 🎨 Componentes de Navegación

### Landing Page
```tsx
// Header Navigation
<Link href="/login">Iniciar Sesión</Link>
<Link href="/dashboard">Comenzar Gratis</Link>

// Hero Section
<Link href="/dashboard">Probar Ahora</Link>

// Pricing Cards
<Link href="/dashboard">Comenzar</Link>
```

### Login Page
```tsx
// Back button
<Link href="/">Volver al inicio</Link>

// Form submit
window.location.href = "/dashboard"

// Sign up link
<Link href="/dashboard">Comienza tu prueba gratuita</Link>
```

### Dashboard
```tsx
// Logout button (TODO)
// Should redirect to "/"
```

## 🔒 Protección de Rutas (TODO)

Actualmente NO hay protección de rutas. Cualquiera puede acceder a `/dashboard` directamente.

### Implementación Recomendada

**Opción 1: Middleware de Next.js**
```typescript
// middleware.ts
export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth_token')

  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
}
```

**Opción 2: Client-side Check**
```typescript
// apps/web/app/dashboard/page.tsx
useEffect(() => {
  const token = localStorage.getItem('auth_token')
  if (!token) {
    window.location.href = '/login'
  }
}, [])
```

**Opción 3: Server Component (Recomendado)**
```typescript
// apps/web/app/dashboard/page.tsx
export default async function DashboardPage() {
  const session = await getServerSession()

  if (!session) {
    redirect('/login')
  }

  return <DashboardComponent />
}
```

## 📝 Next Steps

### 1. Autenticación ✨ ALTA PRIORIDAD
- [ ] Implementar sistema de auth (NextAuth.js o Auth0)
- [ ] Agregar login real con backend
- [ ] Almacenar JWT tokens
- [ ] Implementar refresh tokens
- [ ] Agregar protección de rutas

### 2. Session Management
- [ ] Detectar sesión activa en landing
- [ ] Auto-redirect si ya está logueado
- [ ] Persistir sesión entre recargas
- [ ] Implementar "Recordarme"
- [ ] Timeout de sesión

### 3. Logout Functionality
- [ ] Implementar botón de logout en dashboard
- [ ] Limpiar tokens al hacer logout
- [ ] Redirect a landing (/) después de logout
- [ ] Opción de "Cerrar en todos los dispositivos"

### 4. UX Improvements
- [ ] Loading states durante login
- [ ] Error messages amigables
- [ ] Forgot password flow
- [ ] Sign up flow
- [ ] Email verification
- [ ] Onboarding para nuevos usuarios

### 5. Social Login
- [ ] Implementar Google OAuth
- [ ] Implementar Facebook Login
- [ ] Manejar callbacks de OAuth
- [ ] Vincular cuentas sociales con usuarios

## 🧪 Testing

### Flujo Manual Actual

**1. Landing Page:**
```bash
# Abrir navegador
http://localhost:3000

# Verificar:
✓ Se muestra la landing page
✓ Header tiene "Iniciar Sesión" y "Comenzar Gratis"
✓ Hero section tiene CTA "Probar Ahora"
✓ Pricing cards tienen CTAs
```

**2. Login:**
```bash
# Click en "Iniciar Sesión"
http://localhost:3000/login

# Verificar:
✓ Formulario de login visible
✓ Botón "Volver al inicio" funciona
✓ Submit del form redirige a /dashboard
```

**3. Dashboard:**
```bash
# Después de login
http://localhost:3000/dashboard

# Verificar:
✓ Dashboard se carga correctamente
✓ Sidebar visible
✓ Métricas se cargan del backend
✓ Upload de facturas funciona
```

### Tests E2E Recomendados (Playwright)

```typescript
// tests/e2e/user-flow.spec.ts
test('complete user flow', async ({ page }) => {
  // Visit landing
  await page.goto('/')
  await expect(page.locator('h1')).toContainText('FacturIA')

  // Go to login
  await page.click('text=Iniciar Sesión')
  await expect(page).toHaveURL('/login')

  // Fill login form
  await page.fill('input[type="email"]', 'test@example.com')
  await page.fill('input[type="password"]', 'password123')
  await page.click('button[type="submit"]')

  // Should be redirected to dashboard
  await expect(page).toHaveURL('/dashboard')
  await expect(page.locator('h2')).toContainText('Bienvenido')
})
```

## 📊 Analytics & Tracking (Recomendado)

```typescript
// Track page views
export function trackPageView(path: string) {
  // Google Analytics
  gtag('event', 'page_view', { page_path: path })

  // Mixpanel
  mixpanel.track('Page View', { path })
}

// Track conversions
export function trackConversion(event: string) {
  gtag('event', 'conversion', { event_name: event })
}
```

**Eventos importantes:**
- Landing page view
- CTA clicks ("Comenzar Gratis", "Probar Ahora")
- Login attempt
- Successful login
- Dashboard view
- Feature usage

## 🎯 KPIs a Medir

1. **Landing Page:**
   - Visitors
   - CTA click rate
   - Time on page
   - Bounce rate

2. **Login Page:**
   - Login attempts
   - Success rate
   - Failed attempts
   - Social login usage

3. **Dashboard:**
   - Daily active users
   - Session duration
   - Features used
   - Invoice processing volume

---

**Creado:** 2025-01-05
**Autor:** Claude (Anthropic)
**Versión:** 1.0.0
