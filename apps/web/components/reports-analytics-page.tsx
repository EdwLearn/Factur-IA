"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  AreaChart, Area,
  BarChart, Bar,
  LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, Cell, Legend,
} from "recharts"
import {
  BarChart3, TrendingUp, TrendingDown, FileText, Package,
  DollarSign, Download, Calendar, ShoppingCart,
} from "lucide-react"
import { facturaAPI } from "@/lib/api/facturaAPI"
import type { ReportsData, AnalyticsData } from "@/lib/api/endpoints/dashboard"

const DATE_RANGE_MONTHS: Record<string, number> = {
  "7days": 1,
  "30days": 1,
  "3months": 3,
  "6months": 6,
  "12months": 12,
}

const MARGIN_TARGET = 30

function getMarginColor(margin: number): string {
  if (margin >= 40) return "#16a34a"
  if (margin >= MARGIN_TARGET) return "#d97706"
  return "#dc2626"
}

export function ReportsAnalyticsPage() {
  const [dateRange, setDateRange] = useState("12months")
  const [exportFormat, setExportFormat] = useState("pdf")
  const [reportsData, setReportsData] = useState<ReportsData | null>(null)
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)
  const [totalInventoryValue, setTotalInventoryValue] = useState(0)
  const [inventoryGrowth, setInventoryGrowth] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [dateRange])

  const loadData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const months = DATE_RANGE_MONTHS[dateRange] ?? 12
      const [reports, analytics, metrics] = await Promise.all([
        facturaAPI.getReports(months),
        facturaAPI.getDashboardAnalytics(),
        facturaAPI.getDashboardMetrics(),
      ])
      setReportsData(reports)
      setAnalyticsData(analytics)
      setTotalInventoryValue(metrics.total_inventory_value)
      setInventoryGrowth(metrics.month_over_month_inventory)
    } catch (err) {
      setError("No se pudieron cargar los datos. Verifica que el servidor esté activo.")
      console.error("Error loading reports:", err)
    } finally {
      setIsLoading(false)
    }
  }

  // ── Computed values ─────────────────────────────────────────────────────────

  const invoicesThisMonth = reportsData?.monthly_invoices?.at(-1)?.invoices ?? 0
  const invoicesPrevMonth = reportsData?.monthly_invoices?.at(-2)?.invoices ?? 0
  const invoicesGrowth =
    invoicesPrevMonth > 0
      ? ((invoicesThisMonth - invoicesPrevMonth) / invoicesPrevMonth) * 100
      : invoicesThisMonth > 0 ? 100 : 0

  const totalSpend = reportsData?.monthly_invoices?.reduce(
    (sum, m) => sum + (m.value ?? 0), 0
  ) ?? 0

  const spendThisMonth = reportsData?.monthly_invoices?.at(-1)?.value ?? 0
  const spendPrevMonth = reportsData?.monthly_invoices?.at(-2)?.value ?? 0
  const spendGrowth =
    spendPrevMonth > 0
      ? ((spendThisMonth - spendPrevMonth) / spendPrevMonth) * 100
      : spendThisMonth > 0 ? 100 : 0

  const averageMargin = (() => {
    const products = reportsData?.top_products?.filter((p) => p.margin !== null) ?? []
    if (!products.length) return 0
    return products.reduce((sum, p) => sum + (p.margin ?? 0), 0) / products.length
  })()

  const productsWithMargin = (reportsData?.top_products ?? [])
    .filter((p) => p.margin !== null)
    .sort((a, b) => (a.margin ?? 0) - (b.margin ?? 0))
    .slice(0, 8)
    .map((p) => ({
      ...p,
      label: p.description.length > 22 ? p.description.slice(0, 22) + "…" : p.description,
    }))

  // ── Helpers ─────────────────────────────────────────────────────────────────

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      minimumFractionDigits: 0,
    }).format(amount)

  const formatCurrencyShort = (amount: number) => {
    if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`
    if (amount >= 1_000) return `$${(amount / 1_000).toFixed(0)}K`
    return formatCurrency(amount)
  }

  const handleExportReport = () => {
    alert(`Exportando reporte en formato ${exportFormat.toUpperCase()}...`)
  }

  const GrowthBadge = ({ pct }: { pct: number }) => {
    const up = pct >= 0
    return (
      <span className={`flex items-center text-sm ${up ? "text-green-600" : "text-red-600"}`}>
        {up
          ? <TrendingUp className="w-4 h-4 mr-1" />
          : <TrendingDown className="w-4 h-4 mr-1" />}
        {up ? "+" : ""}{pct.toFixed(1)}% vs mes anterior
      </span>
    )
  }

  const SpendTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    return (
      <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg text-sm">
        <p className="font-semibold text-gray-900 mb-1">{label}</p>
        {payload.map((entry: any, i: number) => (
          <p key={i} style={{ color: entry.color }}>
            {entry.dataKey === "value" && `Gasto: ${formatCurrency(entry.value)}`}
            {entry.dataKey === "invoices" && `Facturas: ${entry.value}`}
            {entry.dataKey === "volume" && `Volumen: ${formatCurrency(entry.value)}`}
            {entry.dataKey === "margin" && `Margen: ${entry.value?.toFixed(1)}%`}
          </p>
        ))}
      </div>
    )
  }

  // ── Loading / Error ──────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Cargando reportes...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <p className="text-red-600">{error}</p>
        <Button variant="outline" onClick={loadData}>Reintentar</Button>
      </div>
    )
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">

      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reportes y Análisis</h1>
          <p className="text-gray-600">Insights y métricas de tu negocio</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger className="w-full sm:w-48">
              <Calendar className="w-4 h-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7days">Últimos 7 días</SelectItem>
              <SelectItem value="30days">Últimos 30 días</SelectItem>
              <SelectItem value="3months">Últimos 3 meses</SelectItem>
              <SelectItem value="6months">Últimos 6 meses</SelectItem>
              <SelectItem value="12months">Últimos 12 meses</SelectItem>
            </SelectContent>
          </Select>
          <div className="flex gap-2">
            <Select value={exportFormat} onValueChange={setExportFormat}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pdf">PDF</SelectItem>
                <SelectItem value="excel">Excel</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={handleExportReport} className="bg-blue-600 hover:bg-blue-700">
              <Download className="w-4 h-4 mr-2" />
              Exportar
            </Button>
          </div>
        </div>
      </div>

      {/* ── KPI Cards (4) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

        {/* Gasto total del período */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Gasto del Período</p>
                <p className="text-2xl font-bold text-gray-900">{formatCurrencyShort(totalSpend)}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <ShoppingCart className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <div className="mt-2">
              <GrowthBadge pct={spendGrowth} />
            </div>
          </CardContent>
        </Card>

        {/* Facturas este mes */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Facturas Este Mes</p>
                <p className="text-2xl font-bold text-gray-900">{invoicesThisMonth}</p>
              </div>
              <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center">
                <FileText className="w-6 h-6 text-indigo-600" />
              </div>
            </div>
            <div className="mt-2">
              <GrowthBadge pct={invoicesGrowth} />
            </div>
          </CardContent>
        </Card>

        {/* Valor inventario */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Valor Inventario</p>
                <p className="text-2xl font-bold text-gray-900">{formatCurrencyShort(totalInventoryValue)}</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <Package className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <div className="mt-2">
              <GrowthBadge pct={inventoryGrowth} />
            </div>
          </CardContent>
        </Card>

        {/* Margen promedio */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Margen Promedio</p>
                <p className="text-2xl font-bold text-gray-900">{averageMargin.toFixed(1)}%</p>
              </div>
              <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-orange-600" />
              </div>
            </div>
            <div className="mt-2">
              <span className={`text-sm ${averageMargin >= MARGIN_TARGET ? "text-green-600" : "text-red-500"}`}>
                {averageMargin >= MARGIN_TARGET ? "Rentabilidad saludable" : `Por debajo del objetivo (${MARGIN_TARGET}%)`}
              </span>
            </div>
          </CardContent>
        </Card>

      </div>

      {/* ── Fila 1: Gasto mensual + Top proveedores ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Gasto mensual en compras (área) */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShoppingCart className="w-5 h-5 text-blue-600" />
              Gasto Mensual en Compras
            </CardTitle>
          </CardHeader>
          <CardContent>
            {(reportsData?.monthly_invoices?.length ?? 0) === 0 ? (
              <div className="h-72 flex items-center justify-center text-gray-400 text-sm">
                Sin datos para el período seleccionado
              </div>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={reportsData?.monthly_invoices ?? []}>
                    <defs>
                      <linearGradient id="gradSpend" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4F63FF" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#4F63FF" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      tickFormatter={(v) => formatCurrencyShort(v)}
                      width={64}
                    />
                    <Tooltip content={<SpendTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#4F63FF"
                      strokeWidth={2.5}
                      fill="url(#gradSpend)"
                      dot={{ fill: "#4F63FF", r: 3 }}
                      activeDot={{ r: 5 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top 5 proveedores */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-indigo-600" />
              Top 5 Proveedores por Volumen
            </CardTitle>
          </CardHeader>
          <CardContent>
            {(reportsData?.top_suppliers?.length ?? 0) === 0 ? (
              <div className="h-72 flex items-center justify-center text-gray-400 text-sm">
                Sin proveedores con facturas en este período
              </div>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={reportsData?.top_suppliers ?? []} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11 }}
                      tickFormatter={(v) => formatCurrencyShort(v)}
                    />
                    <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} width={110} />
                    <Tooltip content={<SpendTooltip />} />
                    <Bar dataKey="volume" fill="#6366f1" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

      </div>

      {/* ── Fila 2: Tendencia del margen + Margen por producto ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Tendencia del margen (últimos 8 meses) */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-600" />
              Tendencia del Margen
              <span className="ml-auto text-xs font-normal text-gray-400">Últimos 8 meses</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {(analyticsData?.margin_trend?.length ?? 0) === 0 ? (
              <div className="h-72 flex items-center justify-center text-gray-400 text-sm">
                Sin datos de margen disponibles
              </div>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={analyticsData?.margin_trend ?? []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      tickFormatter={(v) => `${v}%`}
                      domain={[0, "auto"]}
                      width={44}
                    />
                    <Tooltip content={<SpendTooltip />} />
                    <ReferenceLine
                      y={MARGIN_TARGET}
                      stroke="#d97706"
                      strokeDasharray="4 4"
                      label={{ value: `Objetivo ${MARGIN_TARGET}%`, position: "insideTopRight", fontSize: 11, fill: "#d97706" }}
                    />
                    <Line
                      type="monotone"
                      dataKey="margin"
                      stroke="#16a34a"
                      strokeWidth={2.5}
                      dot={{ fill: "#16a34a", r: 3 }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Margen por producto (semáforo) */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-orange-600" />
              Margen por Producto
              <div className="ml-auto flex items-center gap-3 text-xs font-normal text-gray-500">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-600 inline-block" />≥40%</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />25–40%</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-600 inline-block" />&lt;25%</span>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {productsWithMargin.length === 0 ? (
              <div className="h-72 flex items-center justify-center text-gray-400 text-sm">
                Configura precios de venta para ver el margen por producto
              </div>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={productsWithMargin} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11 }}
                      tickFormatter={(v) => `${v}%`}
                      domain={[0, "auto"]}
                    />
                    <YAxis dataKey="label" type="category" tick={{ fontSize: 10 }} width={130} />
                    <Tooltip content={<SpendTooltip />} />
                    <ReferenceLine
                      x={MARGIN_TARGET}
                      stroke="#d97706"
                      strokeDasharray="4 4"
                    />
                    <Bar dataKey="margin" radius={[0, 4, 4, 0]}>
                      {productsWithMargin.map((entry, index) => (
                        <Cell key={index} fill={getMarginColor(entry.margin ?? 0)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

      </div>

      {/* ── Insights del negocio ── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Insights del Negocio
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-2">Gasto en Compras</h4>
              <p className="text-sm text-blue-800">
                {totalSpend > 0
                  ? `Gasto total en el período: ${formatCurrency(totalSpend)}. Este mes ${
                      spendGrowth >= 0
                        ? `aumentó un ${spendGrowth.toFixed(1)}%`
                        : `bajó un ${Math.abs(spendGrowth).toFixed(1)}%`
                    } vs el anterior.`
                  : "No hay facturas registradas en el período seleccionado."}
              </p>
            </div>

            <div className="bg-green-50 p-4 rounded-lg">
              <h4 className="font-semibold text-green-900 mb-2">Rentabilidad</h4>
              <p className="text-sm text-green-800">
                {averageMargin > 0
                  ? `Margen promedio: ${averageMargin.toFixed(1)}%. ${
                      averageMargin >= MARGIN_TARGET
                        ? "Rentabilidad saludable — por encima del objetivo del 30%."
                        : `Está ${(MARGIN_TARGET - averageMargin).toFixed(1)} puntos por debajo del objetivo del 30%.`
                    }`
                  : "Configura precios de venta en los productos para ver el margen promedio."}
              </p>
            </div>

            <div className="bg-orange-50 p-4 rounded-lg">
              <h4 className="font-semibold text-orange-900 mb-2">Concentración de Proveedores</h4>
              <p className="text-sm text-orange-800">
                {(reportsData?.top_suppliers?.length ?? 0) > 0
                  ? `Proveedor principal: "${reportsData!.top_suppliers[0].name}" con ${formatCurrency(
                      reportsData!.top_suppliers[0].volume
                    )} en compras (${reportsData!.top_suppliers[0].invoices} factura${
                      reportsData!.top_suppliers[0].invoices !== 1 ? "s" : ""
                    }).`
                  : "No hay facturas registradas con proveedores en este período."}
              </p>
            </div>

          </div>
        </CardContent>
      </Card>

    </div>
  )
}
