"use client"

import { useState } from "react"
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
