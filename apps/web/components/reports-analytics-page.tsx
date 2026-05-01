"use client"

import { useState, useEffect } from "react"
import { Card, CardContent } from "@/components/ui/card"
import {
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts"
import { TrendingUp, TrendingDown, Package, Receipt, Tag, ArrowUpDown } from "lucide-react"
import { facturaAPI } from "@/lib/api/facturaAPI"
import type { SalesReportResponse, SalesPeriod, PriceAlertsResponse } from "@/lib/api/endpoints/dashboard"
import { PriceEvolutionChart, PriceAlertsChart } from "@/components/dashboard-charts"

// ─── Helpers ──────────────────────────────────────────────────────────────────

const COP = (v: number) =>
  new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(v)

const COP_SHORT = (v: number) => {
  if (v >= 1_000_000_000) return `$${(v / 1_000_000_000).toFixed(1)}B`
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`
  return COP(v)
}

function ChartSkeleton({ height = 280 }: { height?: number }) {
  return (
    <div
      className="animate-pulse bg-gray-100 dark:bg-gray-700 rounded-lg w-full"
      style={{ height }}
    />
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-44 text-center gap-2 text-gray-400 dark:text-gray-500">
      <svg className="w-10 h-10 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M9 17v-2m3 2v-4m3 4v-6M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
      <p className="text-sm max-w-xs">{message}</p>
    </div>
  )
}

// ─── KPI card ─────────────────────────────────────────────────────────────────

function KPICard({
  title, value, icon: Icon, iconBg, iconColor, trend, sub,
}: {
  title: string
  value: string
  icon: React.ElementType
  iconBg: string
  iconColor: string
  trend?: { pct: number }
  sub?: string
}) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="min-w-0 flex-1 mr-3">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{title}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 truncate">{value}</p>
          </div>
          <div className={`w-12 h-12 ${iconBg} rounded-full flex items-center justify-center flex-shrink-0`}>
            <Icon className={`w-6 h-6 ${iconColor}`} />
          </div>
        </div>
        <div className="mt-2 h-5">
          {trend != null ? (
            <span className={`flex items-center text-sm ${trend.pct >= 0 ? "text-green-600" : "text-red-600"}`}>
              {trend.pct >= 0
                ? <TrendingUp className="w-4 h-4 mr-1 flex-shrink-0" />
                : <TrendingDown className="w-4 h-4 mr-1 flex-shrink-0" />}
              {trend.pct >= 0 ? "+" : ""}{trend.pct.toFixed(1)}% vs mes anterior
            </span>
          ) : sub ? (
            <span className="text-sm text-gray-500">{sub}</span>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Period options ───────────────────────────────────────────────────────────

const PERIOD_OPTIONS: { label: string; value: SalesPeriod }[] = [
  { label: "Mes actual",      value: "current_month"    },
  { label: "Últimos 30 días", value: "last_30_days"     },
  { label: "Comparar meses",  value: "month_comparison" },
]

// ─── Page ─────────────────────────────────────────────────────────────────────

export function ReportsAnalyticsPage() {
  const [period, setPeriod] = useState<SalesPeriod>("current_month")
  const [salesData, setSalesData] = useState<SalesReportResponse | null>(null)
  const [priceAlerts, setPriceAlerts] = useState<PriceAlertsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { loadData() }, [period])

  const loadData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [sales, alerts] = await Promise.all([
        facturaAPI.getSalesReport(period),
        facturaAPI.getPriceAlerts().catch(() => null),
      ])
      setSalesData(sales)
      setPriceAlerts(alerts ?? { alerts: [] })
    } catch (err) {
      setError("No se pudieron cargar los datos. Verifica que el servidor esté activo.")
      console.error("Error loading sales report:", err)
    } finally {
      setIsLoading(false)
    }
  }

  const kpis       = salesData?.kpis
  const comparison = salesData?.comparison
  const chartData  = salesData?.revenue_over_time ?? []
  const topProducts = salesData?.top_products ?? []
  const maxRevenue = Math.max(...topProducts.map((p) => p.revenue), 1)

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <p className="text-red-600 text-sm">{error}</p>
        <button
          onClick={loadData}
          className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">

      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Reportes de Ventas</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Ventas sincronizadas desde Alegra · actualización automática cada 6 h
          </p>
        </div>

        {/* Period tabs */}
        <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden text-sm flex-shrink-0">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setPeriod(opt.value)}
              className={`px-4 py-2 transition-colors whitespace-nowrap ${
                period === opt.value
                  ? "bg-blue-600 text-white font-medium"
                  : "text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── 4 KPI cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Ingresos Totales"
          value={isLoading ? "…" : COP_SHORT(kpis?.total_revenue ?? 0)}
          icon={TrendingUp}
          iconBg="bg-blue-100"
          iconColor="text-blue-600"
          trend={comparison ? { pct: comparison.change_pct } : undefined}
        />
        <KPICard
          title="Unidades Vendidas"
          value={isLoading ? "…" : (kpis?.total_units_sold ?? 0).toLocaleString("es-CO")}
          icon={Package}
          iconBg="bg-green-100"
          iconColor="text-green-600"
        />
        <KPICard
          title="Órdenes de Venta"
          value={isLoading ? "…" : (kpis?.total_orders ?? 0).toLocaleString("es-CO")}
          icon={Receipt}
          iconBg="bg-indigo-100"
          iconColor="text-indigo-600"
          sub="facturas Alegra únicas"
        />
        <KPICard
          title="Ticket Promedio"
          value={isLoading ? "…" : COP_SHORT(kpis?.avg_ticket ?? 0)}
          icon={Tag}
          iconBg="bg-orange-100"
          iconColor="text-orange-600"
        />
      </div>

      {/* ── Revenue over time ── */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
          <div>
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
              Ingresos en el Tiempo
            </p>
            {period === "month_comparison" && comparison && (
              <p className="text-xs text-gray-400 mt-0.5">
                Mes anterior: {COP(comparison.previous_month_revenue)} ·
                Mes actual: {COP(comparison.current_month_revenue)}
              </p>
            )}
          </div>

          {period === "month_comparison" && comparison && (
            <span
              className={`text-sm font-semibold px-3 py-1 rounded-full ${
                comparison.change_pct >= 0
                  ? "bg-green-100 text-green-700"
                  : "bg-red-100 text-red-700"
              }`}
            >
              {comparison.change_pct >= 0 ? "▲" : "▼"}{" "}
              {Math.abs(comparison.change_pct)}% vs mes anterior
            </span>
          )}
        </div>

        {isLoading ? (
          <ChartSkeleton />
        ) : chartData.length === 0 ? (
          <EmptyState message="Sin ventas registradas en este período. Sincroniza Alegra desde la sección Inventario." />
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}   />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                tickFormatter={(d) => {
                  const dt = new Date(d + "T00:00:00")
                  return `${dt.getDate()}/${dt.getMonth() + 1}`
                }}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => COP_SHORT(v)}
                width={64}
              />
              <Tooltip
                formatter={(v: number) => [COP(v), "Ingresos"]}
                labelFormatter={(d) => `Fecha: ${d}`}
              />
              <Area
                type="monotone"
                dataKey="revenue"
                stroke="#3b82f6"
                strokeWidth={2.5}
                fill="url(#revenueGrad)"
                dot={{ r: 2, fill: "#3b82f6" }}
                activeDot={{ r: 5 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Top 10 productos por ingresos ── */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-5">
          <ArrowUpDown className="w-4 h-4 text-gray-400" />
          <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
            Top 10 Productos por Ingresos
          </p>
        </div>

        {isLoading ? (
          <ChartSkeleton height={320} />
        ) : topProducts.length === 0 ? (
          <EmptyState message="Sin datos de ventas en este período." />
        ) : (
          <div className="space-y-3">
            {topProducts.map((p, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-xs text-gray-400 w-5 text-right flex-shrink-0">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1.5">
                    <span
                      className="text-sm font-medium text-gray-800 dark:text-gray-100 truncate pr-2"
                      title={p.name}
                    >
                      {p.name}
                    </span>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        {COP(p.revenue)}
                      </span>
                      <span className="text-xs text-gray-400 w-10 text-right tabular-nums">
                        {p.revenue_pct.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all duration-500"
                      style={{ width: `${(p.revenue / maxRevenue) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Evolución de precio + Alertas de variación ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PriceEvolutionChart />
        <PriceAlertsChart data={priceAlerts} />
      </div>

    </div>
  )
}
