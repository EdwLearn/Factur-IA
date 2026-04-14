"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Check, X, ArrowLeft, Zap, Loader2 } from "lucide-react"
import {
  upgradePlan,
  formatPriceCOP,
  type PlanDetails,
} from "@/src/lib/api/endpoints/subscriptions"
import { isAuthenticated } from "@/src/lib/api/endpoints/auth"

// ---------------------------------------------------------------------------
// Static plan data — avoids a round-trip for a marketing/public page
// ---------------------------------------------------------------------------

const PLANS: (PlanDetails & { highlight?: boolean })[] = [
  {
    name: 'freemium',
    display_name: 'Freemium',
    price_cop: 0,
    invoice_limit: 15,
    supplier_limit: 5,
    history_days: 30,
    max_users: 1,
    can_export: false,
    can_inventory: false,
    can_alerts: false,
    support_level: 'email',
    highlight: false,
  },
  {
    name: 'basic',
    display_name: 'Básico',
    price_cop: 79_900,
    invoice_limit: 100,
    supplier_limit: 50,
    history_days: 180,
    max_users: 1,
    can_export: false,
    can_inventory: true,
    can_alerts: true,
    support_level: 'email_priority',
    highlight: false,
  },
  {
    name: 'pro',
    display_name: 'Pro',
    price_cop: 199_900,
    invoice_limit: null,
    supplier_limit: null,
    history_days: null,
    max_users: 3,
    can_export: true,
    can_inventory: true,
    can_alerts: true,
    support_level: 'chat_email',
    highlight: true,
  },
]

const SUPPORT_LABELS: Record<string, string> = {
  email: 'Email',
  email_priority: 'Email prioritario',
  chat_email: 'Chat + Email',
}

function tick(v: boolean) {
  return v
    ? <Check className="w-5 h-5 text-green-500 mx-auto" />
    : <X className="w-5 h-5 text-gray-300 mx-auto" />
}

function val(v: number | null, suffix = '') {
  return v === null ? 'Ilimitado' : `${v.toLocaleString('es-CO')}${suffix}`
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function PricingPage() {
  const router = useRouter()
  const [authenticated, setAuthenticated] = useState(false)
  const [currentPlan, setCurrentPlan] = useState<string | null>(null)
  const [upgrading, setUpgrading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const auth = isAuthenticated()
    setAuthenticated(auth)
    if (auth) {
      const stored = localStorage.getItem('plan') ?? null
      setCurrentPlan(stored)
      // Fetch real plan from API
      import('@/src/lib/api/endpoints/subscriptions').then(({ getCurrentSubscription }) => {
        getCurrentSubscription()
          .then((s) => setCurrentPlan(s.plan))
          .catch(() => {/* ignore */})
      })
    }
  }, [])

  const handleChoosePlan = async (planName: string) => {
    if (!authenticated) {
      router.push('/login')
      return
    }
    if (planName === currentPlan) return
    setUpgrading(planName)
    setError(null)
    try {
      await upgradePlan(planName)
      setCurrentPlan(planName)
      router.push('/dashboard')
    } catch (e: any) {
      setError(e.message || 'Error al actualizar el plan')
    } finally {
      setUpgrading(null)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <div className="max-w-6xl mx-auto px-4 pt-8 pb-4">
        <Link
          href={authenticated ? '/dashboard' : '/'}
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          {authenticated ? 'Volver al dashboard' : 'Volver al inicio'}
        </Link>

        <div className="text-center mb-10">
          <Badge className="bg-blue-100 text-blue-700 mb-3">Planes y precios</Badge>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Elige el plan ideal para tu negocio
          </h1>
          <p className="text-gray-500 max-w-lg mx-auto">
            Automatiza el procesamiento de facturas y gestiona tu inventario.
            Sin contratos, cancela cuando quieras.
          </p>
        </div>

        {error && (
          <p className="text-center text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-4 py-2 mb-6 max-w-lg mx-auto">
            {error}
          </p>
        )}

        {/* Plan cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {PLANS.map((plan) => {
            const isCurrent = plan.name === currentPlan
            return (
              <div
                key={plan.name}
                className={`relative rounded-2xl border-2 bg-white p-6 flex flex-col gap-5 shadow-sm transition-all hover:shadow-md ${
                  plan.highlight
                    ? 'border-blue-500 shadow-blue-100'
                    : isCurrent
                      ? 'border-green-400'
                      : 'border-gray-200'
                }`}
              >
                {plan.highlight && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-blue-500 text-white px-3 shadow">
                      <Zap className="w-3 h-3 mr-1" /> Más popular
                    </Badge>
                  </div>
                )}
                {isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-green-500 text-white px-3 shadow">Tu plan actual</Badge>
                  </div>
                )}

                <div>
                  <h2 className="text-lg font-bold text-gray-900">{plan.display_name}</h2>
                  <div className="mt-1">
                    <span className="text-3xl font-extrabold text-gray-900">
                      {formatPriceCOP(plan.price_cop)}
                    </span>
                    {plan.price_cop > 0 && (
                      <span className="text-sm text-gray-400 ml-1">/mes</span>
                    )}
                  </div>
                </div>

                <ul className="space-y-2.5 flex-1">
                  <FeatureRow label="Facturas / mes" value={val(plan.invoice_limit)} />
                  <FeatureRow label="Proveedores en catálogo" value={val(plan.supplier_limit)} />
                  <BoolRow label="Control de inventario" value={plan.can_inventory} />
                  <BoolRow label="Alertas de stock bajo" value={plan.can_alerts} />
                  <FeatureRow
                    label="Historial de facturas"
                    value={plan.history_days === null ? 'Ilimitado' : plan.history_days === 30 ? '30 días' : '6 meses'}
                  />
                  <BoolRow label="Exportar reportes" value={plan.can_export} />
                  <FeatureRow label="Usuarios" value={String(plan.max_users)} />
                  <FeatureRow label="Soporte" value={SUPPORT_LABELS[plan.support_level]} />
                </ul>

                <Button
                  className={`w-full mt-1 ${plan.highlight && !isCurrent ? 'bg-blue-600 hover:bg-blue-700' : ''}`}
                  variant={isCurrent ? 'outline' : plan.highlight ? 'default' : 'outline'}
                  disabled={isCurrent || upgrading !== null}
                  onClick={() => handleChoosePlan(plan.name)}
                >
                  {upgrading === plan.name
                    ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Actualizando…</>
                    : isCurrent
                      ? 'Plan actual'
                      : authenticated
                        ? `Elegir ${plan.display_name}`
                        : 'Comenzar gratis'}
                </Button>
              </div>
            )
          })}
        </div>

        {/* Feature comparison table */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden mb-16">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left px-5 py-4 font-semibold text-gray-700 w-1/3">Característica</th>
                {PLANS.map((p) => (
                  <th key={p.name} className="text-center px-4 py-4 font-semibold text-gray-700">
                    {p.display_name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                { label: 'Precio mensual', render: (p: typeof PLANS[0]) => formatPriceCOP(p.price_cop) },
                { label: 'Facturas procesadas', render: (p: typeof PLANS[0]) => val(p.invoice_limit, '/mes') },
                { label: 'Proveedores en catálogo', render: (p: typeof PLANS[0]) => val(p.supplier_limit) },
                { label: 'Control de inventario', render: (p: typeof PLANS[0]) => tick(p.can_inventory) },
                { label: 'Alertas de stock bajo', render: (p: typeof PLANS[0]) => tick(p.can_alerts) },
                { label: 'Historial de facturas', render: (p: typeof PLANS[0]) =>
                  p.history_days === null ? 'Ilimitado' : p.history_days === 30 ? '30 días' : '6 meses'
                },
                { label: 'Exportar reportes', render: (p: typeof PLANS[0]) => tick(p.can_export) },
                { label: 'Usuarios', render: (p: typeof PLANS[0]) => String(p.max_users) },
                { label: 'Soporte', render: (p: typeof PLANS[0]) => SUPPORT_LABELS[p.support_level] },
              ].map((row, i) => (
                <tr key={i} className={`border-b border-gray-50 ${i % 2 === 0 ? 'bg-gray-50/40' : ''}`}>
                  <td className="px-5 py-3 text-gray-600 font-medium">{row.label}</td>
                  {PLANS.map((p) => (
                    <td key={p.name} className="px-4 py-3 text-center text-gray-700">
                      {row.render(p)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* FAQ / footer */}
        <p className="text-center text-sm text-gray-400 pb-12">
          ¿Tienes dudas?{' '}
          <a href="mailto:soporte@facturia.co" className="text-blue-500 hover:underline">
            Escríbenos a soporte@facturia.co
          </a>
        </p>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

function FeatureRow({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex items-start justify-between gap-2">
      <span className="text-gray-500 text-xs leading-tight">{label}</span>
      <span className="text-xs font-medium text-gray-800 text-right leading-tight">{value}</span>
    </li>
  )
}

function BoolRow({ label, value }: { label: string; value: boolean }) {
  return (
    <li className="flex items-center justify-between gap-2">
      <span className="text-gray-500 text-xs">{label}</span>
      {value
        ? <Check className="w-4 h-4 text-green-500 shrink-0" />
        : <X className="w-4 h-4 text-gray-300 shrink-0" />}
    </li>
  )
}
