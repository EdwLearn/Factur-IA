"use client"

import { useState, useEffect, useCallback } from "react"
import { facturaAPI } from "@/lib/api/facturaAPI"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  AlertTriangle, TrendingDown, RefreshCw, Loader2,
  ShoppingCart, DollarSign, ArrowRight, Package,
} from "lucide-react"

// ── Types ────────────────────────────────────────────────────────────────────

interface RestockRec {
  type: "restock"
  priority: "critical" | "warning"
  product_code: string
  description: string
  category: string | null
  supplier_name: string | null
  current_stock: number
  min_stock: number
  suggested_qty: number
  last_price: number | null
  estimated_cost: number
  days_until_stockout: number | null
  velocity_per_day: number | null
  insight: string
}

interface Alternative {
  product_code: string
  description: string
  velocity_per_day: number
  margin: number | null
}

interface DeadStockRec {
  type: "dead_stock"
  priority: "high" | "medium"
  product_code: string
  description: string
  category: string | null
  current_stock: number
  capital_tied: number
  days_without_movement: number
  potential_monthly_gain: number
  alternatives: Alternative[]
  insight: string
}

interface Summary {
  total_restock: number
  critical_restock: number
  total_dead_stock: number
  total_capital_tied: number
}

interface RecommendationsData {
  restock: RestockRec[]
  dead_stock: DeadStockRec[]
  summary: Summary
  generated_at: string
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const formatCOP = (n: number) =>
  new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n)

const formatCOPShort = (n: number) => {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(0)}K`
  return formatCOP(n)
}

// ── Component ────────────────────────────────────────────────────────────────

export function RecommendationsPage() {
  const [data, setData]       = useState<RecommendationsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await facturaAPI.getRecommendations()
      const d   = (res as any)?.data ?? res
      if (d && "restock" in d) {
        setData(d as RecommendationsData)
      } else {
        throw new Error("Respuesta inesperada del servidor")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
        <span className="text-gray-500">Analizando inventario...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <p className="text-red-600">{error}</p>
        <Button variant="outline" onClick={load}>Reintentar</Button>
      </div>
    )
  }

  const s = data!.summary
  const generatedAt = new Date(data!.generated_at).toLocaleString("es-CO", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  })

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recomendaciones de IA</h1>
          <p className="text-gray-500 text-sm mt-0.5">Actualizado: {generatedAt}</p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Actualizar
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          label="Alertas críticas"
          value={s.critical_restock}
          icon={<AlertTriangle className="w-5 h-5 text-red-600" />}
          bg="bg-red-50"
          valueColor="text-red-700"
        />
        <SummaryCard
          label="Reabastecer"
          value={s.total_restock}
          icon={<ShoppingCart className="w-5 h-5 text-orange-600" />}
          bg="bg-orange-50"
          valueColor="text-orange-700"
        />
        <SummaryCard
          label="Capital muerto"
          value={s.total_dead_stock}
          icon={<TrendingDown className="w-5 h-5 text-purple-600" />}
          bg="bg-purple-50"
          valueColor="text-purple-700"
        />
        <SummaryCard
          label="Dinero inmovilizado"
          value={formatCOPShort(s.total_capital_tied)}
          icon={<DollarSign className="w-5 h-5 text-blue-600" />}
          bg="bg-blue-50"
          valueColor="text-blue-700"
          isText
        />
      </div>

      {/* No recommendations */}
      {s.total_restock === 0 && s.total_dead_stock === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 gap-3">
            <Package className="w-12 h-12 text-green-400" />
            <p className="text-lg font-medium text-gray-700">Todo en orden</p>
            <p className="text-gray-500 text-sm">No hay alertas de inventario en este momento.</p>
          </CardContent>
        </Card>
      )}

      {/* Restock recommendations */}
      {data!.restock.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <ShoppingCart className="w-5 h-5 text-orange-600" />
            Reabastecimiento ({data!.restock.length})
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {data!.restock.map((rec) => (
              <RestockCard key={rec.product_code} rec={rec} />
            ))}
          </div>
        </section>
      )}

      {/* Dead stock recommendations */}
      {data!.dead_stock.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-purple-600" />
            Capital Inmovilizado ({data!.dead_stock.length})
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {data!.dead_stock.map((rec) => (
              <DeadStockCard key={rec.product_code} rec={rec} />
            ))}
          </div>
        </section>
      )}

    </div>
  )
}

// ── Sub-components ───────────────────────────────────────────────────────────

function SummaryCard({
  label, value, icon, bg, valueColor, isText = false,
}: {
  label: string
  value: number | string
  icon: React.ReactNode
  bg: string
  valueColor: string
  isText?: boolean
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className={`w-9 h-9 ${bg} rounded-lg flex items-center justify-center mb-3`}>
          {icon}
        </div>
        <p className={`text-2xl font-bold ${valueColor}`}>{value}</p>
        <p className="text-xs text-gray-500 mt-0.5">{label}</p>
      </CardContent>
    </Card>
  )
}

function RestockCard({ rec }: { rec: RestockRec }) {
  const isCritical = rec.priority === "critical"
  const border     = isCritical ? "border-l-4 border-l-red-500" : "border-l-4 border-l-orange-400"

  return (
    <Card className={border}>
      <CardContent className="p-4 space-y-3">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="font-semibold text-gray-900 truncate" title={rec.description}>
              {rec.description}
            </p>
            <p className="text-xs text-gray-400">{rec.product_code} · {rec.category ?? "Sin categoría"}</p>
          </div>
          <Badge className={isCritical
            ? "bg-red-100 text-red-800 hover:bg-red-100 shrink-0"
            : "bg-orange-100 text-orange-800 hover:bg-orange-100 shrink-0"
          }>
            {isCritical ? "Crítico" : "Advertencia"}
          </Badge>
        </div>

        {/* Metrics row */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <Metric label="Stock actual" value={rec.current_stock.toFixed(0)} highlight={isCritical} />
          <Metric label="Mínimo" value={rec.min_stock.toFixed(0)} />
          <Metric label="Comprar" value={rec.suggested_qty.toFixed(0)} />
        </div>

        {/* Days until stockout */}
        {rec.days_until_stockout !== null && (
          <div className={`text-xs rounded px-2 py-1 ${
            rec.days_until_stockout === 0
              ? "bg-red-50 text-red-700"
              : rec.days_until_stockout <= 7
                ? "bg-orange-50 text-orange-700"
                : "bg-gray-50 text-gray-600"
          }`}>
            {rec.days_until_stockout === 0
              ? "⚠ Agotado ahora"
              : `⏱ Se agota en ~${rec.days_until_stockout} días`}
            {rec.velocity_per_day !== null && ` · ${rec.velocity_per_day} u/día`}
          </div>
        )}

        {/* Insight */}
        <p className="text-xs text-gray-600 leading-relaxed">{rec.insight}</p>

        {/* Cost footer */}
        {rec.estimated_cost > 0 && (
          <div className="flex items-center justify-between pt-1 border-t border-gray-100">
            <span className="text-xs text-gray-500">Costo estimado</span>
            <span className="font-semibold text-gray-900">{formatCOP(rec.estimated_cost)}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function DeadStockCard({ rec }: { rec: DeadStockRec }) {
  const isHigh = rec.priority === "high"
  const border = isHigh ? "border-l-4 border-l-purple-600" : "border-l-4 border-l-purple-300"

  return (
    <Card className={border}>
      <CardContent className="p-4 space-y-3">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="font-semibold text-gray-900 truncate" title={rec.description}>
              {rec.description}
            </p>
            <p className="text-xs text-gray-400">{rec.product_code} · {rec.category ?? "Sin categoría"}</p>
          </div>
          <Badge className={isHigh
            ? "bg-purple-100 text-purple-800 hover:bg-purple-100 shrink-0"
            : "bg-purple-50 text-purple-700 hover:bg-purple-50 shrink-0"
          }>
            {isHigh ? "Alta prioridad" : "Media prioridad"}
          </Badge>
        </div>

        {/* Metrics row */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <Metric label="Sin movimiento" value={`${rec.days_without_movement}d`} highlight={isHigh} />
          <Metric label="Stock" value={rec.current_stock.toFixed(0)} />
          <Metric label="Inmovilizado" value={formatCOPShort(rec.capital_tied)} highlight />
        </div>

        {/* Insight */}
        <p className="text-xs text-gray-600 leading-relaxed">{rec.insight}</p>

        {/* Alternatives */}
        {rec.alternatives.length > 0 && (
          <div className="space-y-1.5 pt-1 border-t border-gray-100">
            <p className="text-xs font-medium text-gray-500">Reinvertir en:</p>
            {rec.alternatives.map((alt) => (
              <div key={alt.product_code} className="flex items-center gap-2 text-xs">
                <ArrowRight className="w-3 h-3 text-purple-500 shrink-0" />
                <span className="text-gray-700 truncate flex-1" title={alt.description}>
                  {alt.description}
                </span>
                <span className="text-gray-400 shrink-0">{alt.velocity_per_day} u/día</span>
                {alt.margin !== null && (
                  <span className="text-green-700 font-medium shrink-0">{alt.margin}%</span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Gain footer */}
        {rec.potential_monthly_gain > 0 && (
          <div className="flex items-center justify-between pt-1 border-t border-gray-100">
            <span className="text-xs text-gray-500">Ganancia potencial/mes</span>
            <span className="font-semibold text-green-700">+{formatCOP(rec.potential_monthly_gain)}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function Metric({
  label, value, highlight = false,
}: {
  label: string
  value: string
  highlight?: boolean
}) {
  return (
    <div className="bg-gray-50 rounded p-2">
      <p className={`text-sm font-bold ${highlight ? "text-red-600" : "text-gray-900"}`}>{value}</p>
      <p className="text-xs text-gray-400 leading-tight">{label}</p>
    </div>
  )
}
