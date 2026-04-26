"use client"

import { useState, useEffect } from "react"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts"
import {
  type TopSuppliersResponse,
  type TopProductsResponse,
  type PriceEvolutionResponse,
  type PriceAlertsResponse,
} from "@/src/lib/api/endpoints/dashboard"
import { facturaAPI } from "@/lib/api"

// ─── Shared helpers ───────────────────────────────────────────────────────────

const COP = (v: number) =>
  new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(v)

function ChartSkeleton({ height = 260 }: { height?: number }) {
  return (
    <div
      className="animate-pulse bg-gray-100 dark:bg-gray-700 rounded-lg w-full"
      style={{ height }}
    />
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-52 text-center gap-2 text-gray-400 dark:text-gray-500">
      <svg className="w-10 h-10 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M9 17v-2m3 2v-4m3 4v-6M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
      <p className="text-sm">{message}</p>
    </div>
  )
}

// ─── Blue gradient shades for top suppliers ───────────────────────────────────
const SUPPLIER_COLORS = ["#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd"]

// ─── Chart 1: Top Suppliers ───────────────────────────────────────────────────

export function TopSuppliersChart({ data }: { data: TopSuppliersResponse | null }) {
  const chartData = data?.suppliers?.map((s) => ({
    name: s.name.length > 20 ? s.name.slice(0, 20) + "…" : s.name,
    fullName: s.name,
    total_gasto: s.total_gasto,
    num_facturas: s.num_facturas,
  })) ?? []

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
      <p className="text-sm font-semibold text-gray-600 dark:text-gray-300 mb-4">
        Top 5 Proveedores — Gasto del Mes
      </p>

      {data === null ? (
        <ChartSkeleton />
      ) : chartData.length === 0 ? (
        <EmptyState message="Procesa tus primeras facturas para ver esta métrica" />
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart
            layout="vertical"
            data={chartData}
            margin={{ top: 0, right: 16, left: 8, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11 }}
              width={130}
            />
            <Tooltip
              formatter={(value: number, _name: string, props: any) => [
                COP(value),
                `${props.payload.fullName} · ${props.payload.num_facturas} factura(s)`,
              ]}
              labelFormatter={() => ""}
            />
            <Bar dataKey="total_gasto" radius={[0, 4, 4, 0]}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={SUPPLIER_COLORS[i % SUPPLIER_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

// ─── Chart 2: Top Products ────────────────────────────────────────────────────

export function TopProductsChart({ data }: { data: TopProductsResponse | null }) {
  const chartData = data?.products?.map((p) => ({
    name: p.description.length > 15 ? p.description.slice(0, 15) + "…" : p.description,
    fullName: p.description,
    cantidad_total: p.cantidad_total,
    gasto_total: p.gasto_total,
    num_facturas: p.num_facturas,
  })) ?? []

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
      <p className="text-sm font-semibold text-gray-600 dark:text-gray-300 mb-4">
        Top 8 Productos Más Comprados — Cantidad del Mes
      </p>

      {data === null ? (
        <ChartSkeleton />
      ) : chartData.length === 0 ? (
        <EmptyState message="Procesa tus primeras facturas para ver esta métrica" />
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData} margin={{ top: 0, right: 8, left: 0, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10 }}
              angle={-40}
              textAnchor="end"
              height={70}
            />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value: number, _name: string, props: any) => [
                `${value} uds — ${COP(props.payload.gasto_total)}`,
                props.payload.fullName,
              ]}
              labelFormatter={() => ""}
            />
            <Bar dataKey="cantidad_total" fill="#10b981" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

// ─── Chart 3: Price Evolution ─────────────────────────────────────────────────

export function PriceEvolutionChart() {
  const [search, setSearch] = useState("")
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<PriceEvolutionResponse | null>(null)

  const handleSearch = async () => {
    const term = search.trim()
    if (!term) return
    setQuery(term)
    setLoading(true)
    try {
      const result = await facturaAPI.getPriceEvolution(term)
      setData(result)
    } catch {
      setData({ product: term, evolution: [] })
    } finally {
      setLoading(false)
    }
  }

  const chartData = data?.evolution?.map((e) => ({
    semana: e.semana,
    precio_promedio: e.precio_promedio,
    precio_min: e.precio_min,
    precio_max: e.precio_max,
    supplier: e.supplier ?? "",
  })) ?? []

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
      <p className="text-sm font-semibold text-gray-600 dark:text-gray-300 mb-3">
        Evolución de Precio — Últimos 6 Meses
      </p>

      <div className="flex gap-2 mb-4">
        <Input
          placeholder="Busca un producto (ej: CINTA ENMASCARAR)"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          className="text-sm"
        />
        <button
          onClick={handleSearch}
          className="px-3 py-1 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap"
        >
          Buscar
        </button>
      </div>

      {!query ? (
        <EmptyState message="Busca un producto para ver su evolución de precio" />
      ) : loading ? (
        <ChartSkeleton />
      ) : chartData.length === 0 ? (
        <EmptyState message={`Sin historial de precios para "${query}"`} />
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="semana" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`} />
            <Tooltip
              formatter={(value: number, name: string, props: any) => [
                COP(value),
                name === "precio_promedio"
                  ? `Promedio — ${props.payload.supplier}`
                  : name === "precio_min"
                  ? "Mínimo"
                  : "Máximo",
              ]}
              labelFormatter={(label) => `Semana: ${label}`}
            />
            <Area
              type="monotone"
              dataKey="precio_max"
              stroke="#c4b5fd"
              strokeWidth={1}
              fill="url(#priceGradient)"
              dot={false}
            />
            <Area
              type="monotone"
              dataKey="precio_min"
              stroke="#c4b5fd"
              strokeWidth={1}
              fill="white"
              dot={false}
            />
            <Area
              type="monotone"
              dataKey="precio_promedio"
              stroke="#8b5cf6"
              strokeWidth={2}
              fill="none"
              dot={{ r: 3, fill: "#8b5cf6" }}
              activeDot={{ r: 5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

// ─── Chart 5: Sales Rotation (POS → Alegra) ──────────────────────────────────

interface RotationItem {
  product_id: string | null
  description: string
  unidades_vendidas: number
  valor_vendido: number
  stock_actual: number
  rotacion: number
  dias_stock: number
}

const DAYS_OPTIONS = [
  { label: "30 días", value: 30 },
  { label: "60 días", value: 60 },
  { label: "90 días", value: 90 },
]

const diasBadge = (dias: number) => {
  if (dias <= 7)  return { label: `${dias} días`, cls: "bg-red-100 text-red-700" }
  if (dias <= 20) return { label: `${dias} días`, cls: "bg-amber-100 text-amber-700" }
  if (dias >= 999) return { label: "Sin ventas", cls: "bg-gray-100 text-gray-400" }
  return { label: `${dias} días`, cls: "bg-emerald-100 text-emerald-700" }
}

export function SalesRotationChart() {
  const [days, setDays] = useState(30)
  const [data, setData] = useState<RotationItem[] | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [loading, setLoading] = useState(false)

  const load = async (d: number) => {
    setLoading(true)
    try {
      const raw = await facturaAPI.getInventoryRotation(d)
      const items: RotationItem[] = (raw as any)?.data ?? raw ?? []
      setData(items)
    } catch {
      setData([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(days) }, [days])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await facturaAPI.syncSales()
      await load(days)
    } catch {
      // silently ignore — load() handles empty state
    } finally {
      setSyncing(false)
    }
  }

  const rows = (data ?? []).slice(0, 15)

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 col-span-1 lg:col-span-2">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <p className="text-sm font-semibold text-gray-600 dark:text-gray-300">
            Rotación de Productos — Ventas desde POS (Alegra)
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            Días de stock = tiempo estimado hasta agotar el inventario al ritmo actual de ventas
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-gray-200 overflow-hidden text-xs">
            {DAYS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setDays(opt.value)}
                className={`px-3 py-1.5 transition-colors ${
                  days === opt.value
                    ? "bg-blue-600 text-white font-medium"
                    : "text-gray-500 hover:bg-gray-50"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <button
            onClick={handleSync}
            disabled={syncing || loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50"
          >
            <svg
              className={`w-3.5 h-3.5 ${syncing ? "animate-spin" : ""}`}
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {syncing ? "Sincronizando…" : "Sync Alegra"}
          </button>
        </div>
      </div>

      {/* Table */}
      {data === null || loading ? (
        <ChartSkeleton height={220} />
      ) : rows.length === 0 ? (
        <EmptyState message="Sin ventas registradas desde Alegra en este período. Pulsa «Sync Alegra» para importar." />
      ) : (
        <>
          <div className="overflow-auto max-h-[360px]">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white dark:bg-gray-800">
                <tr className="text-xs text-gray-500 border-b border-gray-100 dark:border-gray-700">
                  <th className="text-left py-2 pr-3 font-medium">Producto</th>
                  <th className="text-right py-2 pr-3 font-medium whitespace-nowrap">Uds. vendidas</th>
                  <th className="text-right py-2 pr-3 font-medium whitespace-nowrap">Valor vendido</th>
                  <th className="text-right py-2 pr-3 font-medium whitespace-nowrap">Stock actual</th>
                  <th className="text-right py-2 pr-3 font-medium">Rotación</th>
                  <th className="text-right py-2 font-medium">Días de stock</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
                {rows.map((item, i) => {
                  const badge = diasBadge(Math.round(item.dias_stock))
                  return (
                    <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors">
                      <td className="py-2.5 pr-3 font-medium text-gray-900 dark:text-gray-100 max-w-[220px]">
                        <span className="block truncate" title={item.description}>
                          {item.description}
                        </span>
                      </td>
                      <td className="py-2.5 pr-3 text-right text-gray-700 dark:text-gray-300 font-semibold">
                        {item.unidades_vendidas.toLocaleString("es-CO")}
                      </td>
                      <td className="py-2.5 pr-3 text-right text-gray-500 whitespace-nowrap">
                        {COP(item.valor_vendido)}
                      </td>
                      <td className="py-2.5 pr-3 text-right text-gray-700 dark:text-gray-300">
                        {item.stock_actual.toLocaleString("es-CO")}
                      </td>
                      <td className="py-2.5 pr-3 text-right text-gray-500">
                        {item.rotacion > 0 ? item.rotacion.toFixed(2) : "—"}
                      </td>
                      <td className="py-2.5 text-right">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${badge.cls}`}>
                          {badge.label}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Status legend */}
          <div className="flex items-center gap-4 mt-3 pt-3 border-t border-gray-100 text-xs text-gray-400">
            <span className="font-medium text-gray-500">Días de stock:</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red-400 inline-block" /> ≤7 (crítico)</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-400 inline-block" /> 8–20 (bajo)</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" /> &gt;20 (sano)</span>
          </div>
        </>
      )}
    </div>
  )
}

// ─── Chart 4: Price Alerts ────────────────────────────────────────────────────

export function PriceAlertsChart({ data }: { data: PriceAlertsResponse | null }) {
  const alerts = data?.alerts ?? []

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
      <p className="text-sm font-semibold text-gray-600 dark:text-gray-300 mb-4">
        Alertas de Variación de Precio (&gt;10%)
      </p>

      {data === null ? (
        <ChartSkeleton height={220} />
      ) : alerts.length === 0 ? (
        <EmptyState message="No hay variaciones significativas este mes 🎉" />
      ) : (
        <div className="overflow-auto max-h-[260px]">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-gray-100 dark:border-gray-700">
                <th className="text-left py-2 pr-3 font-medium">Producto</th>
                <th className="text-right py-2 pr-3 font-medium whitespace-nowrap">Precio ant.</th>
                <th className="text-right py-2 pr-3 font-medium whitespace-nowrap">Precio act.</th>
                <th className="text-right py-2 font-medium">Variación</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
              {alerts.map((alert, i) => (
                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors">
                  <td className="py-2 pr-3">
                    <p className="font-medium text-gray-900 dark:text-gray-100 leading-tight">
                      {alert.description.length > 28
                        ? alert.description.slice(0, 28) + "…"
                        : alert.description}
                    </p>
                    {alert.supplier && (
                      <p className="text-xs text-gray-400 truncate max-w-[160px]">
                        {alert.supplier}
                      </p>
                    )}
                  </td>
                  <td className="py-2 pr-3 text-right text-gray-500 whitespace-nowrap">
                    {COP(alert.precio_anterior)}
                  </td>
                  <td className="py-2 pr-3 text-right font-medium text-gray-900 dark:text-gray-100 whitespace-nowrap">
                    {COP(alert.precio_actual)}
                  </td>
                  <td className="py-2 text-right">
                    <Badge
                      className={`text-white text-xs px-2 py-0.5 font-semibold ${
                        alert.subio
                          ? "bg-red-500 hover:bg-red-500"
                          : "bg-green-500 hover:bg-green-500"
                      }`}
                    >
                      {alert.subio ? "▲" : "▼"}{" "}
                      {alert.subio ? "+" : ""}
                      {alert.variacion_pct}%
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
