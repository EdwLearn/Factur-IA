"use client"

import { useState, useMemo, useEffect, useCallback } from "react"
import { facturaAPI } from "@/lib/api"
import { apiClient } from "@/src/lib/api/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Package, Search, Edit, History, AlertTriangle, TrendingUp, DollarSign, RefreshCw, X, Loader2 } from "lucide-react"

interface ApiProduct {
  id: string
  product_code: string
  description: string
  reference?: string | null
  unit_measure?: string
  category?: string | null
  supplier_name?: string | null
  current_stock: number
  min_stock: number
  max_stock?: number | null
  sale_price?: number | null
  last_purchase_price?: number | null
  last_purchase_date?: string | null
  stock_status: 'ok' | 'low' | 'out'
}

interface InventoryStats {
  total_products: number
  total_inventory_value: number
  low_stock_count: number
  out_of_stock_count: number
  total_movements_today: number
  total_defective_items: number
}

interface InventoryMovement {
  id: string
  product_id: string
  movement_type: string
  quantity: number
  reference_price?: number | null
  movement_date: string
  invoice_id?: string | null
  notes?: string | null
  product_code?: string | null
  product_description?: string | null
}

type EditFormData = {
  description: string
  unit_measure: string
  category: string
  min_stock: string
  max_stock: string
  sale_price: string
}

export function InventoryPage() {
  const [products, setProducts] = useState<ApiProduct[]>([])
  const [stats, setStats] = useState<InventoryStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [searchTerm, setSearchTerm] = useState("")
  const [stockFilter, setStockFilter] = useState("all")
  const [categoryFilter, setCategoryFilter] = useState("all")
  const [supplierFilter, setSupplierFilter] = useState("all")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")

  // Edit dialog
  const [editProduct, setEditProduct] = useState<ApiProduct | null>(null)
  const [editForm, setEditForm] = useState<EditFormData>({ description: "", unit_measure: "", category: "", min_stock: "", max_stock: "", sale_price: "" })
  const [editLoading, setEditLoading] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  // Alegra sync
  const [alegraSyncing, setAlegraSyncing] = useState(false)
  const [alegraSyncToast, setAlegraSyncToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // History dialog
  const [historyProduct, setHistoryProduct] = useState<ApiProduct | null>(null)
  const [historyMovements, setHistoryMovements] = useState<InventoryMovement[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const [productsRes, statsRes] = await Promise.all([
        facturaAPI.listProducts({ limit: 500 }),
        facturaAPI.getInventoryStats(),
      ])

      const productsData = (productsRes as any)?.data ?? productsRes
      if (Array.isArray(productsData)) {
        setProducts(productsData)
      } else if (productsData && Array.isArray(productsData.products)) {
        setProducts(productsData.products)
      } else {
        setProducts([])
      }

      const statsData = (statsRes as any)?.data ?? statsRes
      if (statsData && typeof statsData === 'object' && 'total_products' in statsData) {
        setStats(statsData as InventoryStats)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleAlegraSync = async () => {
    setAlegraSyncing(true)
    setAlegraSyncToast(null)
    try {
      const res = await apiClient.post("/integrations/alegra/sync-items")
      if (!res.success) throw new Error(res.error?.message ?? "Error al sincronizar")
      const d = res.data
      const pushed = d?.pushed_items ?? 0
      const updated = d?.updated_items ?? 0
      const pulled = d?.pulled_items ?? 0
      const contacts = d?.synced_contacts ?? 0
      setAlegraSyncToast({
        type: 'success',
        message: `Sincronización completa — ${pushed} nuevos · ${updated} actualizados · ${pulled} traídos · ${contacts} contactos`,
      })
      await loadData()
    } catch (err) {
      setAlegraSyncToast({
        type: 'error',
        message: err instanceof Error ? err.message : "Error al sincronizar con Alegra",
      })
    } finally {
      setAlegraSyncing(false)
    }
  }

  const categories = useMemo(() => [...new Set(products.map(p => p.category).filter(Boolean))].sort(), [products])
  const suppliers = useMemo(() => [...new Set(products.map(p => p.supplier_name).filter(Boolean))].sort(), [products])

  const filteredProducts = useMemo(() => {
    return products.filter((product) => {
      const matchesSearch =
        product.product_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        product.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (product.supplier_name ?? '').toLowerCase().includes(searchTerm.toLowerCase())

      const uiStatus = product.stock_status === 'ok' ? 'normal' : product.stock_status
      const matchesStock = stockFilter === 'all' || uiStatus === stockFilter
      const matchesCategory = categoryFilter === 'all' || product.category === categoryFilter
      const matchesSupplier = supplierFilter === 'all' || product.supplier_name === supplierFilter

      let matchesDate = true
      if (dateFrom || dateTo) {
        const purchaseDate = product.last_purchase_date ? product.last_purchase_date.slice(0, 10) : null
        if (!purchaseDate) {
          matchesDate = false
        } else {
          if (dateFrom && purchaseDate < dateFrom) matchesDate = false
          if (dateTo && purchaseDate > dateTo) matchesDate = false
        }
      }

      return matchesSearch && matchesStock && matchesCategory && matchesSupplier && matchesDate
    })
  }, [products, searchTerm, stockFilter, categoryFilter, supplierFilter, dateFrom, dateTo])

  const formatCurrency = (amount: number | null | undefined) => {
    if (amount == null) return '—'
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      minimumFractionDigits: 0,
    }).format(amount)
  }

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return '—'
    return new Date(dateStr).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' })
  }

  const getStockBadge = (status: ApiProduct['stock_status']) => {
    switch (status) {
      case 'low':
        return (
          <Badge className="bg-orange-100 text-orange-800 hover:bg-orange-100">
            <AlertTriangle className="w-3 h-3 mr-1" />
            Stock Bajo
          </Badge>
        )
      case 'out':
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

  const getRowClassName = (status: ApiProduct['stock_status']) => {
    if (status === 'low') return 'bg-orange-50 hover:bg-orange-100'
    if (status === 'out') return 'bg-red-50 hover:bg-red-100'
    return 'hover:bg-gray-50'
  }

  // --- Edit handlers ---
  const openEdit = (product: ApiProduct) => {
    setEditProduct(product)
    setEditError(null)
    setEditForm({
      description: product.description,
      unit_measure: product.unit_measure ?? "",
      category: product.category ?? "",
      min_stock: String(product.min_stock),
      max_stock: product.max_stock != null ? String(product.max_stock) : "",
      sale_price: product.sale_price != null ? String(product.sale_price) : "",
    })
  }

  const closeEdit = () => {
    setEditProduct(null)
    setEditError(null)
  }

  const handleEditSave = async () => {
    if (!editProduct) return
    setEditLoading(true)
    setEditError(null)
    try {
      const payload: Record<string, unknown> = {
        description: editForm.description.trim(),
        unit_measure: editForm.unit_measure.trim() || "UNIDAD",
        min_stock: parseFloat(editForm.min_stock) || 0,
      }
      if (editForm.category.trim()) payload.category = editForm.category.trim()
      if (editForm.max_stock.trim()) payload.max_stock = parseFloat(editForm.max_stock)
      if (editForm.sale_price.trim()) payload.sale_price = parseFloat(editForm.sale_price)

      const res = await facturaAPI.updateProduct(editProduct.id, payload)
      if (!(res as any).success) {
        throw new Error((res as any).error?.message ?? 'Error al actualizar')
      }
      // Update local state
      setProducts(prev => prev.map(p => p.id === editProduct.id ? { ...p, ...payload, stock_status: p.stock_status } as ApiProduct : p))
      closeEdit()
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setEditLoading(false)
    }
  }

  // --- History handlers ---
  const openHistory = async (product: ApiProduct) => {
    setHistoryProduct(product)
    setHistoryMovements([])
    setHistoryLoading(true)
    try {
      const res = await (facturaAPI as any).getProductMovements(product.id)
      const data = (res as any)?.data ?? res
      setHistoryMovements(Array.isArray(data) ? data : [])
    } catch {
      setHistoryMovements([])
    } finally {
      setHistoryLoading(false)
    }
  }

  const closeHistory = () => setHistoryProduct(null)

  const getMovementBadge = (type: string) => {
    switch (type) {
      case 'purchase': return <Badge className="bg-blue-100 text-blue-800">Compra</Badge>
      case 'sale': return <Badge className="bg-green-100 text-green-800">Venta</Badge>
      case 'adjustment': return <Badge className="bg-purple-100 text-purple-800">Ajuste</Badge>
      default: return <Badge variant="outline">{type}</Badge>
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        <span className="ml-2 text-gray-600">Cargando inventario...</span>
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <Package className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Error cargando inventario</h3>
          <p className="text-red-600 mb-6">{error}</p>
          <Button onClick={loadData} className="bg-blue-600 hover:bg-blue-700">
            <RefreshCw className="w-4 h-4 mr-2" />
            Reintentar
          </Button>
        </CardContent>
      </Card>
    )
  }

  const totalProducts = stats?.total_products ?? products.length
  const inventoryValue = stats?.total_inventory_value ?? 0
  const lowStockCount = (stats?.low_stock_count ?? 0) + (stats?.out_of_stock_count ?? 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestión de Inventario</h1>
          <p className="text-gray-600">Administra tu inventario de productos</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handleAlegraSync}
            disabled={alegraSyncing}
            className="border-orange-200 text-orange-700 hover:bg-orange-50"
          >
            {alegraSyncing ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            {alegraSyncing ? "Sincronizando..." : "Sincronizar con Alegra"}
          </Button>
          <Button variant="outline" onClick={loadData}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Actualizar
          </Button>
        </div>
      </div>

      {/* Alegra sync result banner */}
      {alegraSyncToast && (
        <div className={`flex items-center justify-between px-4 py-3 rounded-lg text-sm border ${
          alegraSyncToast.type === 'success'
            ? 'bg-green-50 border-green-200 text-green-800'
            : 'bg-red-50 border-red-200 text-red-800'
        }`}>
          <span>{alegraSyncToast.message}</span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 ml-4 hover:bg-transparent"
            onClick={() => setAlegraSyncToast(null)}
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      )}

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Total Productos</p>
                <p className="text-2xl font-bold text-gray-900">{totalProducts}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <Package className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <div className="flex items-center mt-2">
              <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
              <span className="text-sm text-green-600">{filteredProducts.length} mostrados</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Valor Inventario</p>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(inventoryValue)}</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <div className="flex items-center mt-2">
              <span className="text-sm text-gray-500">Basado en precio de venta</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Stock Bajo / Agotado</p>
                <p className="text-2xl font-bold text-gray-900">{lowStockCount}</p>
              </div>
              <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-orange-600" />
              </div>
            </div>
            <div className="flex items-center mt-2">
              <span className="text-sm text-orange-600">
                {lowStockCount > 0 ? 'Requiere atención' : 'Todo en orden'}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col gap-4">
            {/* Row 1: search + stock/category/supplier */}
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
                    {categories.map(cat => (
                      <SelectItem key={cat!} value={cat!}>{cat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={supplierFilter} onValueChange={setSupplierFilter}>
                  <SelectTrigger className="w-full sm:w-48">
                    <SelectValue placeholder="Proveedor" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos los proveedores</SelectItem>
                    {suppliers.map(sup => (
                      <SelectItem key={sup!} value={sup!}>{sup}</SelectItem>
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

            {/* Row 2: date range filter */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <span className="text-sm text-gray-500 whitespace-nowrap">Última compra:</span>
              <div className="flex items-center gap-2 flex-wrap">
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-40"
                  placeholder="Desde"
                />
                <span className="text-gray-400">—</span>
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-40"
                  placeholder="Hasta"
                />
                {(dateFrom || dateTo) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => { setDateFrom(""); setDateTo("") }}
                    className="text-gray-500 hover:text-gray-700 px-2"
                  >
                    <X className="w-4 h-4" />
                    Limpiar
                  </Button>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Products Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Productos ({filteredProducts.length})</span>
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
                  <TableHead className="font-semibold text-center">Stock</TableHead>
                  <TableHead className="font-semibold text-center">Mínimo</TableHead>
                  <TableHead className="font-semibold text-right">Precio Compra</TableHead>
                  <TableHead className="font-semibold text-right">Precio Venta</TableHead>
                  <TableHead className="font-semibold text-center">Últ. Compra</TableHead>
                  <TableHead className="font-semibold text-center">Estado</TableHead>
                  <TableHead className="font-semibold text-center">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredProducts.map((product, idx) => (
                  <TableRow
                    key={product.id}
                    className={`${getRowClassName(product.stock_status)} ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}
                  >
                    <TableCell className="font-medium">{product.product_code}</TableCell>
                    <TableCell className="max-w-xs">
                      <div className="truncate" title={product.description}>
                        {product.description}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">{product.category ?? '—'}</TableCell>
                    <TableCell className="text-sm text-gray-600 max-w-[160px]">
                      <div className="truncate" title={product.supplier_name ?? ''}>
                        {product.supplier_name ?? '—'}
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <span
                        className={`font-semibold ${
                          product.stock_status === 'low'
                            ? 'text-orange-600'
                            : product.stock_status === 'out'
                              ? 'text-red-600'
                              : 'text-gray-900'
                        }`}
                      >
                        {product.current_stock}
                      </span>
                    </TableCell>
                    <TableCell className="text-center text-gray-600">{product.min_stock}</TableCell>
                    <TableCell className="text-right">{formatCurrency(product.last_purchase_price)}</TableCell>
                    <TableCell className="text-right font-semibold">{formatCurrency(product.sale_price)}</TableCell>
                    <TableCell className="text-center text-sm text-gray-600">{formatDate(product.last_purchase_date)}</TableCell>
                    <TableCell className="text-center">{getStockBadge(product.stock_status)}</TableCell>
                    <TableCell className="text-center">
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                          title="Editar producto"
                          onClick={() => openEdit(product)}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-gray-600 hover:text-gray-700 hover:bg-gray-100"
                          title="Ver historial de movimientos"
                          onClick={() => openHistory(product)}
                        >
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
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {products.length === 0 ? 'Sin productos en inventario' : 'No se encontraron productos'}
              </h3>
              <p className="text-gray-500">
                {products.length === 0
                  ? 'Los productos aparecen aquí al confirmar el precio de una factura procesada'
                  : 'Intenta ajustar los filtros de búsqueda'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit Product Dialog */}
      <Dialog open={!!editProduct} onOpenChange={(open) => { if (!open) closeEdit() }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Editar Producto</DialogTitle>
          </DialogHeader>
          {editProduct && (
            <div className="space-y-4 py-2">
              <div className="text-sm text-gray-500 font-medium">{editProduct.product_code}</div>

              <div className="space-y-2">
                <Label htmlFor="edit-description">Descripción</Label>
                <Input
                  id="edit-description"
                  value={editForm.description}
                  onChange={(e) => setEditForm(f => ({ ...f, description: e.target.value }))}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-unit">Unidad de medida</Label>
                  <Input
                    id="edit-unit"
                    value={editForm.unit_measure}
                    onChange={(e) => setEditForm(f => ({ ...f, unit_measure: e.target.value }))}
                    placeholder="UNIDAD"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-category">Categoría</Label>
                  <Input
                    id="edit-category"
                    value={editForm.category}
                    onChange={(e) => setEditForm(f => ({ ...f, category: e.target.value }))}
                    placeholder="Sin categoría"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-min-stock">Stock mínimo</Label>
                  <Input
                    id="edit-min-stock"
                    type="number"
                    min="0"
                    value={editForm.min_stock}
                    onChange={(e) => setEditForm(f => ({ ...f, min_stock: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-max-stock">Stock máximo</Label>
                  <Input
                    id="edit-max-stock"
                    type="number"
                    min="0"
                    value={editForm.max_stock}
                    onChange={(e) => setEditForm(f => ({ ...f, max_stock: e.target.value }))}
                    placeholder="—"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-sale-price">Precio venta</Label>
                  <Input
                    id="edit-sale-price"
                    type="number"
                    min="0"
                    value={editForm.sale_price}
                    onChange={(e) => setEditForm(f => ({ ...f, sale_price: e.target.value }))}
                    placeholder="—"
                  />
                </div>
              </div>

              {editError && (
                <p className="text-sm text-red-600 bg-red-50 rounded p-2">{editError}</p>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={closeEdit} disabled={editLoading}>
              Cancelar
            </Button>
            <Button onClick={handleEditSave} disabled={editLoading} className="bg-blue-600 hover:bg-blue-700">
              {editLoading ? "Guardando..." : "Guardar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* History Dialog */}
      <Dialog open={!!historyProduct} onOpenChange={(open) => { if (!open) closeHistory() }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              Historial de movimientos
              {historyProduct && (
                <span className="ml-2 text-sm font-normal text-gray-500">
                  — {historyProduct.product_code}: {historyProduct.description}
                </span>
              )}
            </DialogTitle>
          </DialogHeader>

          <div className="max-h-96 overflow-y-auto">
            {historyLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
                <span className="ml-2 text-gray-600 text-sm">Cargando historial...</span>
              </div>
            ) : historyMovements.length === 0 ? (
              <div className="text-center py-12">
                <History className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">No hay movimientos registrados</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="bg-gray-50">
                    <TableHead className="font-semibold">Fecha</TableHead>
                    <TableHead className="font-semibold">Tipo</TableHead>
                    <TableHead className="font-semibold text-right">Cantidad</TableHead>
                    <TableHead className="font-semibold text-right">Precio ref.</TableHead>
                    <TableHead className="font-semibold">Notas</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {historyMovements.map((mov) => (
                    <TableRow key={mov.id}>
                      <TableCell className="text-sm text-gray-600 whitespace-nowrap">
                        {formatDate(mov.movement_date)}
                      </TableCell>
                      <TableCell>{getMovementBadge(mov.movement_type)}</TableCell>
                      <TableCell className={`text-right font-medium ${mov.quantity >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                        {mov.quantity >= 0 ? '+' : ''}{mov.quantity}
                      </TableCell>
                      <TableCell className="text-right text-sm">{formatCurrency(mov.reference_price)}</TableCell>
                      <TableCell className="text-sm text-gray-500 max-w-[180px]">
                        <div className="truncate" title={mov.notes ?? ''}>{mov.notes ?? '—'}</div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={closeHistory}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
