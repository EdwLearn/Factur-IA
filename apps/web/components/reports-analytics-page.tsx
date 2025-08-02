"use client"

import { useState, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { BarChart3, TrendingUp, FileText, Package, DollarSign, Download, Calendar } from "lucide-react"

// Mock data for charts
const monthlyInvoicesData = [
  { month: "Jul 2023", invoices: 45, value: 125000000 },
  { month: "Ago 2023", invoices: 52, value: 142000000 },
  { month: "Sep 2023", invoices: 48, value: 138000000 },
  { month: "Oct 2023", invoices: 61, value: 165000000 },
  { month: "Nov 2023", invoices: 58, value: 158000000 },
  { month: "Dic 2023", invoices: 72, value: 195000000 },
  { month: "Ene 2024", invoices: 67, value: 182000000 },
  { month: "Feb 2024", invoices: 74, value: 201000000 },
  { month: "Mar 2024", invoices: 69, value: 189000000 },
  { month: "Abr 2024", invoices: 78, value: 215000000 },
  { month: "May 2024", invoices: 82, value: 225000000 },
  { month: "Jun 2024", invoices: 85, value: 235000000 },
]

const topSuppliersData = [
  { name: "Textiles Antioquia S.A.", volume: 198000000, invoices: 67 },
  { name: "Distribuidora Medellín S.A.S", volume: 165000000, invoices: 45 },
  { name: "Comercializadora Bogotá S.A.S", volume: 134500000, invoices: 52 },
  { name: "Calzado Colombia Ltda", volume: 125000000, invoices: 39 },
  { name: "Manufacturas del Caribe S.A.", volume: 87300000, invoices: 32 },
]

interface BestSellingProduct {
  id: string
  name: string
  category: string
  unitsSold: number
  revenue: number
  margin: number
  supplier: string
}

const bestSellingProducts: BestSellingProduct[] = [
  {
    id: "1",
    name: "Camiseta Polo Básica Blanca",
    category: "Textiles",
    unitsSold: 245,
    revenue: 11025000,
    margin: 44.4,
    supplier: "Textiles Antioquia S.A.",
  },
  {
    id: "2",
    name: "Jean Clásico Azul Talla 32",
    category: "Textiles",
    unitsSold: 189,
    revenue: 16065000,
    margin: 46.7,
    supplier: "Distribuidora Medellín S.A.S",
  },
  {
    id: "3",
    name: "Zapatos Deportivos Nike Air Max",
    category: "Calzado",
    unitsSold: 156,
    revenue: 49920000,
    margin: 43.8,
    supplier: "Calzado Colombia Ltda",
  },
  {
    id: "4",
    name: "Blusa Elegante Blanca",
    category: "Textiles",
    unitsSold: 134,
    revenue: 7772000,
    margin: 45.2,
    supplier: "Textiles Antioquia S.A.",
  },
  {
    id: "5",
    name: "Botas de Trabajo Caterpillar",
    category: "Calzado",
    unitsSold: 98,
    revenue: 37240000,
    margin: 41.8,
    supplier: "Calzado Colombia Ltda",
  },
  {
    id: "6",
    name: "Correa de Cuero Marrón",
    category: "Accesorios",
    unitsSold: 87,
    revenue: 5655000,
    margin: 46.2,
    supplier: "Accesorios y Más S.A.S",
  },
  {
    id: "7",
    name: "Gorra Deportiva Negra",
    category: "Accesorios",
    unitsSold: 76,
    revenue: 2660000,
    margin: 48.6,
    supplier: "Accesorios y Más S.A.S",
  },
  {
    id: "8",
    name: "Sandalias de Playa Adidas",
    category: "Calzado",
    unitsSold: 65,
    revenue: 7800000,
    margin: 45.8,
    supplier: "Calzado Colombia Ltda",
  },
]

export function ReportsAnalyticsPage() {
  const [dateRange, setDateRange] = useState("12months")
  const [exportFormat, setExportFormat] = useState("pdf")

  const keyMetrics = useMemo(() => {
    const currentMonth = monthlyInvoicesData[monthlyInvoicesData.length - 1]
    const previousMonth = monthlyInvoicesData[monthlyInvoicesData.length - 2]

    const invoicesThisMonth = currentMonth.invoices
    const invoicesGrowth = ((currentMonth.invoices - previousMonth.invoices) / previousMonth.invoices) * 100

    const totalInventoryValue = 285000000 // Mock value
    const inventoryGrowth = 12.5

    const totalRevenue = bestSellingProducts.reduce((sum, product) => sum + product.revenue, 0)
    const totalCost = bestSellingProducts.reduce(
      (sum, product) => sum + product.revenue * (1 - product.margin / 100),
      0,
    )
    const averageMargin = ((totalRevenue - totalCost) / totalRevenue) * 100

    return {
      invoicesThisMonth,
      invoicesGrowth,
      totalInventoryValue,
      inventoryGrowth,
      averageMargin,
    }
  }, [])

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      minimumFractionDigits: 0,
    }).format(amount)
  }

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("es-CO").format(num)
  }

  const handleExportReport = () => {
    alert(`Exportando reporte en formato ${exportFormat.toUpperCase()}...`)
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-medium text-gray-900">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.dataKey === "invoices" && `Facturas: ${entry.value}`}
              {entry.dataKey === "value" && `Valor: ${formatCurrency(entry.value)}`}
              {entry.dataKey === "volume" && `Volumen: ${formatCurrency(entry.value)}`}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-6">
      {/* Header */}
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

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Facturas Este Mes</p>
                <p className="text-2xl font-bold text-gray-900">{keyMetrics.invoicesThisMonth}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <div className="flex items-center mt-2">
              <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
              <span className="text-sm text-green-600">+{keyMetrics.invoicesGrowth.toFixed(1)}% vs mes anterior</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Valor Total Inventario</p>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(keyMetrics.totalInventoryValue)}</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <Package className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <div className="flex items-center mt-2">
              <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
              <span className="text-sm text-green-600">+{keyMetrics.inventoryGrowth}% este mes</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Margen Promedio</p>
                <p className="text-2xl font-bold text-gray-900">{keyMetrics.averageMargin.toFixed(1)}%</p>
              </div>
              <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-orange-600" />
              </div>
            </div>
            <div className="flex items-center mt-2">
              <span className="text-sm text-gray-600">Rentabilidad saludable</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monthly Invoices Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Facturas Procesadas por Mes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={monthlyInvoicesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line
                    type="monotone"
                    dataKey="invoices"
                    stroke="#4F63FF"
                    strokeWidth={3}
                    dot={{ fill: "#4F63FF", strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6, stroke: "#4F63FF", strokeWidth: 2 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Top Suppliers Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Top 5 Proveedores por Volumen
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topSuppliersData} layout="horizontal">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} width={120} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="volume" fill="#4F63FF" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Best Selling Products Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="w-5 h-5" />
            Productos Más Vendidos
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-gray-50">
                  <TableHead className="font-semibold">Producto</TableHead>
                  <TableHead className="font-semibold">Categoría</TableHead>
                  <TableHead className="font-semibold text-center">Unidades Vendidas</TableHead>
                  <TableHead className="font-semibold text-right">Ingresos</TableHead>
                  <TableHead className="font-semibold text-center">Margen</TableHead>
                  <TableHead className="font-semibold">Proveedor</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {bestSellingProducts.map((product, index) => (
                  <TableRow
                    key={product.id}
                    className={`${index % 2 === 0 ? "bg-white" : "bg-gray-50"} hover:bg-blue-50`}
                  >
                    <TableCell className="font-medium">{product.name}</TableCell>
                    <TableCell>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          product.category === "Textiles"
                            ? "bg-blue-100 text-blue-800"
                            : product.category === "Calzado"
                              ? "bg-green-100 text-green-800"
                              : "bg-purple-100 text-purple-800"
                        }`}
                      >
                        {product.category}
                      </span>
                    </TableCell>
                    <TableCell className="text-center font-semibold">{formatNumber(product.unitsSold)}</TableCell>
                    <TableCell className="text-right font-semibold">{formatCurrency(product.revenue)}</TableCell>
                    <TableCell className="text-center">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          product.margin >= 45
                            ? "bg-green-100 text-green-800"
                            : product.margin >= 40
                              ? "bg-yellow-100 text-yellow-800"
                              : "bg-red-100 text-red-800"
                        }`}
                      >
                        {product.margin.toFixed(1)}%
                      </span>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">{product.supplier}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Summary Insights */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Insights del Negocio
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-2">Crecimiento Sostenido</h4>
              <p className="text-sm text-blue-800">
                Las facturas procesadas han aumentado un {keyMetrics.invoicesGrowth.toFixed(1)}% este mes, mostrando un
                crecimiento constante en el volumen de negocio.
              </p>
            </div>

            <div className="bg-green-50 p-4 rounded-lg">
              <h4 className="font-semibold text-green-900 mb-2">Margen Saludable</h4>
              <p className="text-sm text-green-800">
                El margen promedio de {keyMetrics.averageMargin.toFixed(1)}% indica una rentabilidad saludable en todos
                los productos.
              </p>
            </div>

            <div className="bg-orange-50 p-4 rounded-lg">
              <h4 className="font-semibold text-orange-900 mb-2">Diversificación</h4>
              <p className="text-sm text-orange-800">
                Los textiles lideran las ventas, pero el calzado y accesorios también contribuyen significativamente a
                los ingresos.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
