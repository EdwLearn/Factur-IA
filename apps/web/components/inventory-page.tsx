"use client"

import { useState, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Package, Search, Edit, History, AlertTriangle, TrendingUp, DollarSign } from "lucide-react"

interface Product {
  id: string
  code: string
  description: string
  category: string
  supplier: string
  currentStock: number
  minimumStock: number
  purchasePrice: number
  salePrice: number
  status: "normal" | "low" | "out"
}

const sampleProducts: Product[] = [
  {
    id: "1",
    code: "TEX001",
    description: "Camiseta Polo Básica Blanca Talla M",
    category: "Textiles",
    supplier: "Confecciones ABC",
    currentStock: 45,
    minimumStock: 20,
    purchasePrice: 25000,
    salePrice: 45000,
    status: "normal",
  },
  {
    id: "2",
    code: "CAL002",
    description: "Zapatos Deportivos Nike Air Max",
    category: "Calzado",
    supplier: "Distribuidora XYZ",
    currentStock: 8,
    minimumStock: 15,
    purchasePrice: 180000,
    salePrice: 320000,
    status: "low",
  },
  {
    id: "3",
    code: "ACC003",
    description: "Correa de Cuero Marrón",
    category: "Accesorios",
    supplier: "Cueros Colombia",
    currentStock: 0,
    minimumStock: 10,
    purchasePrice: 35000,
    salePrice: 65000,
    status: "out",
  },
  {
    id: "4",
    code: "TEX004",
    description: "Jean Clásico Azul Talla 32",
    category: "Textiles",
    supplier: "Confecciones ABC",
    currentStock: 32,
    minimumStock: 25,
    purchasePrice: 45000,
    salePrice: 85000,
    status: "normal",
  },
  {
    id: "5",
    code: "CAL005",
    description: "Sandalias de Playa Adidas",
    category: "Calzado",
    supplier: "Distribuidora XYZ",
    currentStock: 12,
    minimumStock: 20,
    purchasePrice: 65000,
    salePrice: 120000,
    status: "low",
  },
  {
    id: "6",
    code: "ACC006",
    description: "Gorra Deportiva Negra",
    category: "Accesorios",
    supplier: "Accesorios Plus",
    currentStock: 28,
    minimumStock: 15,
    purchasePrice: 18000,
    salePrice: 35000,
    status: "normal",
  },
  {
    id: "7",
    code: "TEX007",
    description: "Blusa Elegante Blanca Talla S",
    category: "Textiles",
    supplier: "Moda Femenina",
    currentStock: 5,
    minimumStock: 12,
    purchasePrice: 32000,
    salePrice: 58000,
    status: "low",
  },
  {
    id: "8",
    code: "CAL008",
    description: "Botas de Trabajo Caterpillar",
    category: "Calzado",
    supplier: "Seguridad Industrial",
    currentStock: 18,
    minimumStock: 8,
    purchasePrice: 220000,
    salePrice: 380000,
    status: "normal",
  },
]

export function InventoryPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [categoryFilter, setCategoryFilter] = useState("all")
  const [supplierFilter, setSupplierFilter] = useState("all")
  const [stockFilter, setStockFilter] = useState("all")

  const filteredProducts = useMemo(() => {
    return sampleProducts.filter((product) => {
      const matchesSearch =
        product.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        product.description.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesCategory = categoryFilter === "all" || product.category === categoryFilter
      const matchesSupplier = supplierFilter === "all" || product.supplier === supplierFilter
      const matchesStock =
        stockFilter === "all" ||
        (stockFilter === "normal" && product.status === "normal") ||
        (stockFilter === "low" && product.status === "low") ||
        (stockFilter === "out" && product.status === "out")

      return matchesSearch && matchesCategory && matchesSupplier && matchesStock
    })
  }, [searchTerm, categoryFilter, supplierFilter, stockFilter])

  const metrics = useMemo(() => {
    const totalProducts = sampleProducts.length
    const inventoryValue = sampleProducts.reduce(
      (sum, product) => sum + product.currentStock * product.purchasePrice,
      0,
    )
    const lowStockProducts = sampleProducts.filter(
      (product) => product.status === "low" || product.status === "out",
    ).length

    return {
      totalProducts,
      inventoryValue,
      lowStockProducts,
    }
  }, [])

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      minimumFractionDigits: 0,
    }).format(amount)
  }

  const getStockStatusBadge = (product: Product) => {
    switch (product.status) {
      case "low":
        return (
          <Badge className="bg-orange-100 text-orange-800 hover:bg-orange-100">
            <AlertTriangle className="w-3 h-3 mr-1" />
            Stock Bajo
          </Badge>
        )
      case "out":
        return (
          <Badge className="bg-red-100 text-red-800 hover:bg-red-100">
            <AlertTriangle className="w-3 h-3 mr-1" />
            Agotado
          </Badge>
        )
      default:
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Normal</Badge>
    }
  }

  const getRowClassName = (product: Product) => {
    if (product.status === "low") {
      return "bg-orange-50 hover:bg-orange-100"
    }
    if (product.status === "out") {
      return "bg-red-50 hover:bg-red-100"
    }
    return "hover:bg-gray-50"
  }

  const categories = [...new Set(sampleProducts.map((p) => p.category))]
  const suppliers = [...new Set(sampleProducts.map((p) => p.supplier))]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Gestión de Inventario</h1>
        <p className="text-gray-600">Administra tu inventario de productos</p>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Total Productos</p>
                <p className="text-2xl font-bold text-gray-900">{metrics.totalProducts}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <Package className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <div className="flex items-center mt-2">
              <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
              <span className="text-sm text-green-600">+5% este mes</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Valor Inventario</p>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(metrics.inventoryValue)}</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <div className="flex items-center mt-2">
              <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
              <span className="text-sm text-green-600">+12% este mes</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Stock Bajo</p>
                <p className="text-2xl font-bold text-gray-900">{metrics.lowStockProducts}</p>
              </div>
              <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-orange-600" />
              </div>
            </div>
            <div className="flex items-center mt-2">
              <span className="text-sm text-orange-600">Requiere atención</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="Buscar por código o descripción..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                <SelectTrigger className="w-full sm:w-48">
                  <SelectValue placeholder="Categoría" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas las categorías</SelectItem>
                  {categories.map((category) => (
                    <SelectItem key={category} value={category}>
                      {category}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={supplierFilter} onValueChange={setSupplierFilter}>
                <SelectTrigger className="w-full sm:w-48">
                  <SelectValue placeholder="Proveedor" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los proveedores</SelectItem>
                  {suppliers.map((supplier) => (
                    <SelectItem key={supplier} value={supplier}>
                      {supplier}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={stockFilter} onValueChange={setStockFilter}>
                <SelectTrigger className="w-full sm:w-48">
                  <SelectValue placeholder="Estado Stock" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los estados</SelectItem>
                  <SelectItem value="normal">Stock Normal</SelectItem>
                  <SelectItem value="low">Stock Bajo</SelectItem>
                  <SelectItem value="out">Agotado</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Products Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Productos ({filteredProducts.length})</span>
            <Button className="bg-blue-600 hover:bg-blue-700">
              <Package className="w-4 h-4 mr-2" />
              Agregar Producto
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-gray-50">
                  <TableHead className="font-semibold">Código</TableHead>
                  <TableHead className="font-semibold">Descripción</TableHead>
                  <TableHead className="font-semibold">Categoría</TableHead>
                  <TableHead className="font-semibold">Proveedor</TableHead>
                  <TableHead className="font-semibold text-center">Stock Actual</TableHead>
                  <TableHead className="font-semibold text-center">Stock Mínimo</TableHead>
                  <TableHead className="font-semibold text-right">Precio Compra</TableHead>
                  <TableHead className="font-semibold text-right">Precio Venta</TableHead>
                  <TableHead className="font-semibold text-center">Estado</TableHead>
                  <TableHead className="font-semibold text-center">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredProducts.map((product, index) => (
                  <TableRow
                    key={product.id}
                    className={`${getRowClassName(product)} ${index % 2 === 0 ? "bg-white" : "bg-gray-50"}`}
                  >
                    <TableCell className="font-medium">{product.code}</TableCell>
                    <TableCell className="max-w-xs">
                      <div className="truncate" title={product.description}>
                        {product.description}
                      </div>
                    </TableCell>
                    <TableCell>{product.category}</TableCell>
                    <TableCell>{product.supplier}</TableCell>
                    <TableCell className="text-center">
                      <span
                        className={`font-semibold ${
                          product.status === "low"
                            ? "text-orange-600"
                            : product.status === "out"
                              ? "text-red-600"
                              : "text-gray-900"
                        }`}
                      >
                        {product.currentStock}
                      </span>
                    </TableCell>
                    <TableCell className="text-center text-gray-600">{product.minimumStock}</TableCell>
                    <TableCell className="text-right">{formatCurrency(product.purchasePrice)}</TableCell>
                    <TableCell className="text-right font-semibold">{formatCurrency(product.salePrice)}</TableCell>
                    <TableCell className="text-center">{getStockStatusBadge(product)}</TableCell>
                    <TableCell className="text-center">
                      <div className="flex items-center justify-center gap-2">
                        <Button variant="ghost" size="sm" className="text-blue-600 hover:text-blue-700">
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="sm" className="text-gray-600 hover:text-gray-700">
                          <History className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {filteredProducts.length === 0 && (
            <div className="text-center py-12">
              <Package className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No se encontraron productos</h3>
              <p className="text-gray-500">Intenta ajustar los filtros de búsqueda</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
