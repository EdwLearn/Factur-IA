"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { AlertTriangle, Zap } from "lucide-react"
import {
  getCurrentSubscription,
  getUsage,
  usagePercent,
  PLAN_COLORS,
  PLAN_LABELS,
  type CurrentSubscription,
  type UsageInfo,
} from "@/src/lib/api/endpoints/subscriptions"
import { isAuthenticated } from "@/src/lib/api/endpoints/auth"

interface PlanBadgeProps {
  /** Cuando compact=true muestra solo el badge del plan sin detalles */
  compact?: boolean
}

export function PlanBadge({ compact = false }: PlanBadgeProps) {
  const [subscription, setSubscription] = useState<CurrentSubscription | null>(null)
  const [usage, setUsage] = useState<UsageInfo | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isAuthenticated()) {
      setLoading(false)
      return
    }

    Promise.all([getCurrentSubscription(), getUsage()])
      .then(([sub, use]) => {
        setSubscription(sub)
        setUsage(use)
      })
      .catch(() => {/* silently fail — badge is non-critical */})
      .finally(() => setLoading(false))
  }, [])

  if (loading || !subscription || !usage) return null

  const pct = usagePercent(usage)
  const isNearLimit = pct >= 80
  const isAtLimit = pct >= 100
  const planKey = subscription.plan
  const badgeClass = PLAN_COLORS[planKey] ?? 'bg-gray-200 text-gray-800'

  // Modo compacto: solo el badge del plan (para sidebar colapsado)
  if (compact) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex justify-center">
              <Badge className={`text-xs px-2 py-0.5 font-bold ${badgeClass}`}>
                {(PLAN_LABELS[planKey] ?? planKey).slice(0, 3).toUpperCase()}
              </Badge>
            </div>
          </TooltipTrigger>
          <TooltipContent side="right">
            <p className="text-xs font-medium">Plan {PLAN_LABELS[planKey] ?? planKey}</p>
            {usage.invoice_limit !== null && (
              <p className="text-xs">{usage.invoice_count} / {usage.invoice_limit} facturas</p>
            )}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return (
    <TooltipProvider>
      <div className="px-3 py-2 rounded-lg border border-slate-600 bg-slate-700 shadow-sm space-y-2">
        {/* Plan name */}
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-300">Tu plan</span>
          <Badge className={`text-xs px-2 py-0.5 font-bold ${badgeClass}`}>
            {PLAN_LABELS[planKey] ?? planKey}
          </Badge>
        </div>

        {/* Usage bar — only shown for plans with a limit */}
        {usage.invoice_limit !== null && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-gray-400">
              <span>
                {isAtLimit
                  ? <span className="text-red-400 font-semibold flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Límite</span>
                  : `${usage.invoice_count}/${usage.invoice_limit}`}
              </span>
              <span>{usage.days_until_reset}d</span>
            </div>

            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <Progress
                    value={pct}
                    className={`h-1.5 bg-slate-600 ${isAtLimit ? '[&>div]:bg-red-500' : isNearLimit ? '[&>div]:bg-amber-400' : '[&>div]:bg-blue-400'}`}
                  />
                </div>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p className="text-xs">
                  {pct}% usado · reinicia en {usage.days_until_reset} días
                </p>
              </TooltipContent>
            </Tooltip>
          </div>
        )}

        {/* Upgrade CTA */}
        {planKey !== 'pro' && (
          <Link
            href="/pricing"
            className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 font-medium transition-colors"
          >
            <Zap className="w-3 h-3" />
            {isNearLimit ? 'Actualiza ahora' : 'Ver planes'}
          </Link>
        )}
      </div>
    </TooltipProvider>
  )
}
