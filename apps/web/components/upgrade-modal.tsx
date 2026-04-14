"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Check, X, Zap, Loader2 } from "lucide-react"
import { upgradePlan, formatPriceCOP, PLAN_LABELS } from "@/src/lib/api/endpoints/subscriptions"
import Link from "next/link"

// ---------------------------------------------------------------------------
// Static plan data for the modal — keeps it self-contained and fast
// (no extra API call needed just to show the modal)
// ---------------------------------------------------------------------------

const PLANS = [
  {
    key: 'freemium',
    name: 'Freemium',
    price: 0,
    invoices: '15 / mes',
    suppliers: '5',
    inventory: false,
    alerts: false,
    history: '30 días',
    export: false,
    users: 1,
    highlight: false,
  },
  {
    key: 'basic',
    name: 'Básico',
    price: 79_900,
    invoices: '100 / mes',
    suppliers: '50',
    inventory: true,
    alerts: true,
    history: '6 meses',
    export: false,
    users: 1,
    highlight: false,
  },
  {
    key: 'pro',
    name: 'Pro',
    price: 199_900,
    invoices: 'Ilimitadas',
    suppliers: 'Ilimitados',
    inventory: true,
    alerts: true,
    history: 'Ilimitado',
    export: true,
    users: 3,
    highlight: true,
  },
]

const FEATURES = [
  { label: 'Facturas procesadas', key: 'invoices' as const },
  { label: 'Proveedores en catálogo', key: 'suppliers' as const },
  { label: 'Control de inventario', key: 'inventory' as const },
  { label: 'Alertas stock bajo', key: 'alerts' as const },
  { label: 'Historial de facturas', key: 'history' as const },
  { label: 'Exportar reportes', key: 'export' as const },
  { label: 'Usuarios', key: 'users' as const },
]

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface UpgradeModalProps {
  open: boolean
  onClose: () => void
  currentPlan?: string
  /** Shown above the plans table to explain why the modal appeared */
  reason?: string
}

export function UpgradeModal({ open, onClose, currentPlan = 'freemium', reason }: UpgradeModalProps) {
  const [upgrading, setUpgrading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleUpgrade = async (planKey: string) => {
    if (planKey === currentPlan) return
    setUpgrading(planKey)
    setError(null)
    try {
      await upgradePlan(planKey)
      // Reload so the new plan limits take effect everywhere
      window.location.reload()
    } catch (e: any) {
      setError(e.message || 'Error al actualizar el plan')
      setUpgrading(null)
    }
  }

  const renderCell = (plan: typeof PLANS[0], key: keyof typeof PLANS[0]) => {
    const value = plan[key]
    if (typeof value === 'boolean') {
      return value
        ? <Check className="w-4 h-4 text-green-500 mx-auto" />
        : <X className="w-4 h-4 text-gray-300 mx-auto" />
    }
    return <span className="text-sm text-center block">{String(value)}</span>
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <Zap className="w-5 h-5 text-blue-500" />
            Actualiza tu plan
          </DialogTitle>
          {reason && (
            <DialogDescription className="text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 text-sm mt-1">
              {reason}
            </DialogDescription>
          )}
        </DialogHeader>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
            {error}
          </p>
        )}

        {/* Plans grid */}
        <div className="grid grid-cols-3 gap-3 mt-2">
          {PLANS.map((plan) => {
            const isCurrent = plan.key === currentPlan
            return (
              <div
                key={plan.key}
                className={`rounded-xl border-2 p-4 flex flex-col gap-3 transition-all ${
                  plan.highlight
                    ? 'border-blue-500 shadow-md'
                    : isCurrent
                      ? 'border-gray-300 bg-gray-50'
                      : 'border-gray-200'
                }`}
              >
                {plan.highlight && (
                  <Badge className="bg-blue-500 text-white self-start text-xs">Recomendado</Badge>
                )}
                <div>
                  <h3 className="font-semibold text-gray-900">{plan.name}</h3>
                  <p className="text-xl font-bold text-gray-900 mt-1">
                    {formatPriceCOP(plan.price)}
                    {plan.price > 0 && <span className="text-xs font-normal text-gray-400"> /mes</span>}
                  </p>
                </div>

                <ul className="space-y-1.5 flex-1">
                  {FEATURES.map((f) => (
                    <li key={f.key} className="flex items-start gap-2 text-xs text-gray-600">
                      {typeof plan[f.key] === 'boolean' ? (
                        plan[f.key]
                          ? <Check className="w-3.5 h-3.5 text-green-500 mt-0.5 shrink-0" />
                          : <X className="w-3.5 h-3.5 text-gray-300 mt-0.5 shrink-0" />
                      ) : (
                        <Check className="w-3.5 h-3.5 text-blue-400 mt-0.5 shrink-0" />
                      )}
                      <span>
                        <span className="font-medium">{f.label}:</span>{' '}
                        {typeof plan[f.key] !== 'boolean' && String(plan[f.key])}
                      </span>
                    </li>
                  ))}
                </ul>

                <Button
                  size="sm"
                  className="w-full mt-1"
                  variant={isCurrent ? 'outline' : plan.highlight ? 'default' : 'outline'}
                  disabled={isCurrent || upgrading !== null}
                  onClick={() => handleUpgrade(plan.key)}
                >
                  {upgrading === plan.key
                    ? <><Loader2 className="w-3 h-3 animate-spin mr-1" /> Actualizando…</>
                    : isCurrent
                      ? 'Plan actual'
                      : `Elegir ${plan.name}`}
                </Button>
              </div>
            )
          })}
        </div>

        <p className="text-xs text-gray-400 text-center mt-2">
          ¿Tienes preguntas?{' '}
          <Link href="/pricing" className="text-blue-500 hover:underline" onClick={onClose}>
            Ver comparación completa
          </Link>
        </p>
      </DialogContent>
    </Dialog>
  )
}
