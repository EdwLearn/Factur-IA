"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  Search,
  Users,
  Phone,
  Mail,
  MapPin,
  FileText,
  Calendar,
  TrendingUp,
  Building2,
  Eye,
  Edit,
  RefreshCw,
  DollarSign,
  CheckCircle,
  Clock,
  XCircle,
} from "lucide-react"
import { facturaAPI } from "@/lib/api/facturaAPI"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Supplier {
  id: string
  name: string
  vatNumber: string
  email?: string | null
  phone?: string | null
  city?: string | null
  address?: string | null
  status: "active" | "inactive"
  totalInvoices: number
  totalAmount: number
  lastInvoiceDate?: string | null
  joinDate: string
}

interface SupplierInvoice {
  id: string
  invoice_number?: string | null
  issue_date?: string | null
  total_amount: number
  status: string
  upload_timestamp: string
  original_filename: string
}

interface SupplierMetrics {
  totalSuppliers: number
  activeSuppliers: number
  newThisMonth: number
}

type EditForm = {
  company_name: string
  email: string
  phone: string
  address: string
  city: string
  department: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SupplierManagementPage() {
  // ── Server state ──
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [metrics, setMetrics] = useState<SupplierMetrics>({
    totalSuppliers: 0,
    activeSuppliers: 0,
    newThisMonth: 0,
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  // ── Filter state ──
  const [searchTerm, setSearchTerm] = useState("")
  const [cityFilter, setCityFilter] = useState("all")
  const [statusFilter, setStatusFilter] = useState("all")

  // ── Profile sheet ──
  const [sheetOpen, setSheetOpen] = useState(false)
  const [selectedSupplier, setSelectedSupplier] = useState<Supplier | null>(null)
  const [activeTab, setActiveTab] = useState("info")

  // ── Edit state ──
  const [editForm, setEditForm] = useState<EditForm>({ company_name: "", email: "", phone: "", address: "", city: "", department: "" })
  const [editLoading, setEditLoading] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)
  const [editSuccess, setEditSuccess] = useState(false)

  // ── Invoices state ──
  const [invoices, setInvoices] = useState<SupplierInvoice[]>([])
  const [invoicesLoading, setInvoicesLoading] = useState(false)

  // ── Data fetching ──
  const loadSuppliers = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const data = await facturaAPI.getSuppliers()
      setSuppliers(data.suppliers as Supplier[])
      setMetrics({
        totalSuppliers: data.metrics.total_suppliers,
        activeSuppliers: data.metrics.active_suppliers,
        newThisMonth: data.metrics.new_this_month,
      })
    } catch (err) {
      console.error("Error loading suppliers:", err)
      setError("No se pudieron cargar los proveedores. Verifica que el servidor esté activo.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadSuppliers() }, [loadSuppliers])

  // ── Client-side filtering ──
  const filteredSuppliers = useMemo(() => {
    return suppliers.filter((supplier) => {
      const matchesSearch =
        supplier.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        supplier.vatNumber.includes(searchTerm)
      const matchesCity = cityFilter === "all" || supplier.city === cityFilter
      const matchesStatus = statusFilter === "all" || supplier.status === statusFilter
      return matchesSearch && matchesCity && matchesStatus
    })
  }, [suppliers, searchTerm, cityFilter, statusFilter])

  const cities = useMemo(
    () => [...new Set(suppliers.map((s) => s.city).filter(Boolean))] as string[],
    [suppliers],
  )

  // ── Open profile ──
  const openProfile = (supplier: Supplier, tab: string = "info") => {
    setSelectedSupplier(supplier)
    setActiveTab(tab)
    setEditForm({
      company_name: supplier.name,
      email: supplier.email ?? "",
      phone: supplier.phone ?? "",
      address: supplier.address ?? "",
      city: supplier.city ?? "",
      department: "",
    })
    setEditError(null)
    setEditSuccess(false)
    setInvoices([])
    setSheetOpen(true)
  }

  // ── Load invoices on tab change ──
  const handleTabChange = useCallback(async (tab: string) => {
    setActiveTab(tab)
    if (tab === "invoices" && selectedSupplier && invoices.length === 0) {
      setInvoicesLoading(true)
      try {
        const res = await (facturaAPI as any).getSupplierInvoices(selectedSupplier.vatNumber)
        const data = (res as any)?.data ?? res
        setInvoices(Array.isArray(data) ? data : [])
      } catch {
        setInvoices([])
      } finally {
        setInvoicesLoading(false)
      }
    }
  }, [selectedSupplier, invoices.length])

  // ── Save edit ──
  const handleEditSave = async () => {
    if (!selectedSupplier) return
    setEditLoading(true)
    setEditError(null)
    setEditSuccess(false)
    try {
      const payload: Record<string, unknown> = {}
      if (editForm.company_name.trim()) payload.company_name = editForm.company_name.trim()
      if (editForm.email.trim()) payload.email = editForm.email.trim()
      if (editForm.phone.trim()) payload.phone = editForm.phone.trim()
      if (editForm.address.trim()) payload.address = editForm.address.trim()
      if (editForm.city.trim()) payload.city = editForm.city.trim()
      if (editForm.department.trim()) payload.department = editForm.department.trim()

      const res = await (facturaAPI as any).updateSupplier(selectedSupplier.vatNumber, payload)
      if (!(res as any).success) {
        throw new Error((res as any).error?.message ?? "Error al guardar")
      }
      const updated = (res as any).data as Supplier
      // Update local list
      setSuppliers(prev => prev.map(s => s.id === selectedSupplier.id ? { ...s, ...updated } : s))
      setSelectedSupplier(prev => prev ? { ...prev, ...updated } : prev)
      setEditSuccess(true)
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Error desconocido")
    } finally {
      setEditLoading(false)
    }
  }

  // ── Formatters ──
  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", minimumFractionDigits: 0 }).format(amount)

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return "—"
    return new Date(dateString).toLocaleDateString("es-CO", { year: "numeric", month: "short", day: "numeric" })
  }

  const getStatusBadge = (status: Supplier["status"]) =>
    status === "active"
      ? <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Activo</Badge>
      : <Badge className="bg-gray-100 text-gray-800 hover:bg-gray-100">Inactivo</Badge>

  const getInvoiceStatusIcon = (status: string) => {
    switch (status) {
      case "confirmed": return <CheckCircle className="w-4 h-4 text-green-600" />
      case "processing": return <Clock className="w-4 h-4 text-blue-600" />
      case "error": return <XCircle className="w-4 h-4 text-red-600" />
      default: return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  const getInvoiceStatusLabel = (status: string) => {
    const map: Record<string, string> = {
      confirmed: "Confirmada",
      processing: "Procesando",
      error: "Error",
      uploaded: "Subida",
      pricing_review: "En revisión",
    }
    return map[status] ?? status
  }

  const getInitials = (name: string) =>
    name.split(" ").map((w) => w[0]).join("").substring(0, 2).toUpperCase()

  // ── Loading / Error ──
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        <span className="ml-2 text-gray-600">Cargando proveedores...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <p className="text-red-600">{error}</p>
        <Button variant="outline" onClick={loadSuppliers}>Reintentar</Button>
      </div>
    )
  }

  // ── Render ──
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestión de Proveedores</h1>
          <p className="text-gray-600">Administra tu red de proveedores y socios comerciales</p>
        </div>
        <Button variant="outline" onClick={loadSuppliers}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Actualizar
        </Button>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Total Proveedores</p>
                <p className="text-2xl font-bold text-gray-900">{metrics.totalSuppliers}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <Users className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Proveedores Activos</p>
                <p className="text-2xl font-bold text-gray-900">{metrics.activeSuppliers}</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <Building2 className="w-6 h-6 text-green-600" />
              </div>
            </div>
            {metrics.totalSuppliers > 0 && (
              <p className="text-sm text-gray-600 mt-2">
                {((metrics.activeSuppliers / metrics.totalSuppliers) * 100).toFixed(0)}% del total
              </p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Nuevos Este Mes</p>
                <p className="text-2xl font-bold text-gray-900">{metrics.newThisMonth}</p>
              </div>
              <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                <Calendar className="w-6 h-6 text-orange-600" />
              </div>
            </div>
            <div className="flex items-center mt-2">
              <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
              <span className="text-sm text-green-600">Primeras facturas recientes</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="Buscar por nombre o NIT..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
              <Select value={cityFilter} onValueChange={setCityFilter}>
                <SelectTrigger className="w-full sm:w-48">
                  <SelectValue placeholder="Ciudad" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas las ciudades</SelectItem>
                  {cities.map((city) => (
                    <SelectItem key={city} value={city}>{city}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-48">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los estados</SelectItem>
                  <SelectItem value="active">Activos</SelectItem>
                  <SelectItem value="inactive">Inactivos</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary */}
      <p className="text-sm text-gray-600">
        Mostrando {filteredSuppliers.length} de {suppliers.length} proveedores
      </p>

      {/* Suppliers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredSuppliers.map((supplier) => (
          <Card key={supplier.id} className="hover:shadow-lg transition-shadow duration-200">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <Avatar className="w-12 h-12">
                    <AvatarFallback className="bg-blue-600 text-white font-semibold">
                      {getInitials(supplier.name)}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <CardTitle className="text-base font-semibold text-gray-900 mb-1 leading-tight">
                      {supplier.name}
                    </CardTitle>
                    <p className="text-sm text-gray-500">NIT: {supplier.vatNumber}</p>
                  </div>
                </div>
                {getStatusBadge(supplier.status)}
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-3">
                <div className="space-y-1.5">
                  {supplier.phone && (
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Phone className="w-3.5 h-3.5 shrink-0" />
                      <span>{supplier.phone}</span>
                    </div>
                  )}
                  {supplier.email && (
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Mail className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate">{supplier.email}</span>
                    </div>
                  )}
                  {supplier.city && (
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <MapPin className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate">
                        {supplier.address ? `${supplier.address}, ${supplier.city}` : supplier.city}
                      </span>
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-gray-100">
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <div>
                      <p className="text-xs text-gray-500">Total Facturas</p>
                      <p className="text-sm font-semibold text-gray-900">{supplier.totalInvoices}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Monto Total</p>
                      <p className="text-sm font-semibold text-gray-900">{formatCurrency(supplier.totalAmount)}</p>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1 text-blue-600 border-blue-200 hover:bg-blue-50"
                      onClick={() => openProfile(supplier, "info")}
                    >
                      <Eye className="w-4 h-4 mr-1" />
                      Ver Perfil
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-gray-600 hover:bg-gray-50"
                      onClick={() => openProfile(supplier, "edit")}
                      title="Editar proveedor"
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-gray-600 hover:bg-gray-50"
                      onClick={() => openProfile(supplier, "invoices")}
                      title="Ver facturas"
                    >
                      <FileText className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {filteredSuppliers.length === 0 && (
        <Card>
          <CardContent className="p-12 text-center">
            <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No se encontraron proveedores</h3>
            <p className="text-gray-500">
              {suppliers.length === 0
                ? "Aún no hay proveedores registrados. Procesa facturas para verlos aquí."
                : "Intenta ajustar los filtros de búsqueda."}
            </p>
          </CardContent>
        </Card>
      )}

      {/* ── Profile Sheet ── */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
          {selectedSupplier && (
            <>
              <SheetHeader className="pb-4 border-b mb-4">
                <div className="flex items-center gap-4">
                  <Avatar className="w-14 h-14">
                    <AvatarFallback className="bg-blue-600 text-white text-lg font-semibold">
                      {getInitials(selectedSupplier.name)}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <SheetTitle className="text-xl">{selectedSupplier.name}</SheetTitle>
                    <p className="text-sm text-gray-500">NIT: {selectedSupplier.vatNumber}</p>
                    <div className="mt-1">{getStatusBadge(selectedSupplier.status)}</div>
                  </div>
                </div>
              </SheetHeader>

              <Tabs value={activeTab} onValueChange={handleTabChange}>
                <TabsList className="w-full mb-6">
                  <TabsTrigger value="info" className="flex-1">Información</TabsTrigger>
                  <TabsTrigger value="edit" className="flex-1">Editar</TabsTrigger>
                  <TabsTrigger value="invoices" className="flex-1">
                    Facturas
                    {selectedSupplier.totalInvoices > 0 && (
                      <Badge variant="secondary" className="ml-2 text-xs">
                        {selectedSupplier.totalInvoices}
                      </Badge>
                    )}
                  </TabsTrigger>
                </TabsList>

                {/* ── TAB: Información ── */}
                <TabsContent value="info" className="space-y-6">
                  {/* Contact */}
                  <div>
                    <h3 className="font-semibold text-gray-500 mb-3 text-sm uppercase tracking-wide">
                      Contacto
                    </h3>
                    <div className="space-y-3">
                      {selectedSupplier.phone ? (
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center shrink-0">
                            <Phone className="w-4 h-4 text-gray-500" />
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Teléfono</p>
                            <p className="text-sm font-medium">{selectedSupplier.phone}</p>
                          </div>
                        </div>
                      ) : null}
                      {selectedSupplier.email ? (
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center shrink-0">
                            <Mail className="w-4 h-4 text-gray-500" />
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Email</p>
                            <p className="text-sm font-medium">{selectedSupplier.email}</p>
                          </div>
                        </div>
                      ) : null}
                      {(selectedSupplier.city || selectedSupplier.address) ? (
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center shrink-0">
                            <MapPin className="w-4 h-4 text-gray-500" />
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Dirección</p>
                            {selectedSupplier.address && (
                              <p className="text-sm font-medium">{selectedSupplier.address}</p>
                            )}
                            {selectedSupplier.city && (
                              <p className="text-sm text-gray-600">{selectedSupplier.city}</p>
                            )}
                          </div>
                        </div>
                      ) : null}
                      {!selectedSupplier.phone && !selectedSupplier.email && !selectedSupplier.city && (
                        <p className="text-sm text-gray-400 italic">Sin información de contacto registrada</p>
                      )}
                    </div>
                  </div>

                  {/* Business metrics */}
                  <div>
                    <h3 className="font-semibold text-sm uppercase tracking-wide text-gray-500 mb-3">
                      Métricas Comerciales
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-blue-50 p-4 rounded-lg">
                        <div className="flex items-center gap-2 mb-1">
                          <FileText className="w-4 h-4 text-blue-600" />
                          <p className="text-xs text-gray-500">Total Facturas</p>
                        </div>
                        <p className="text-2xl font-bold text-gray-900">{selectedSupplier.totalInvoices}</p>
                      </div>
                      <div className="bg-green-50 p-4 rounded-lg">
                        <div className="flex items-center gap-2 mb-1">
                          <DollarSign className="w-4 h-4 text-green-600" />
                          <p className="text-xs text-gray-500">Monto Total</p>
                        </div>
                        <p className="text-xl font-bold text-gray-900">{formatCurrency(selectedSupplier.totalAmount)}</p>
                      </div>
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="flex items-center gap-2 mb-1">
                          <Calendar className="w-4 h-4 text-gray-500" />
                          <p className="text-xs text-gray-500">Última Factura</p>
                        </div>
                        <p className="text-sm font-semibold text-gray-900">{formatDate(selectedSupplier.lastInvoiceDate)}</p>
                      </div>
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="flex items-center gap-2 mb-1">
                          <Calendar className="w-4 h-4 text-gray-500" />
                          <p className="text-xs text-gray-500">Primer Contacto</p>
                        </div>
                        <p className="text-sm font-semibold text-gray-900">{formatDate(selectedSupplier.joinDate)}</p>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-3 pt-2">
                    <Button
                      className="bg-blue-600 hover:bg-blue-700"
                      onClick={() => handleTabChange("edit")}
                    >
                      <Edit className="w-4 h-4 mr-2" />
                      Editar Proveedor
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => handleTabChange("invoices")}
                    >
                      <FileText className="w-4 h-4 mr-2" />
                      Ver Facturas
                    </Button>
                  </div>
                </TabsContent>

                {/* ── TAB: Editar ── */}
                <TabsContent value="edit" className="space-y-4">
                  <p className="text-sm text-gray-500">
                    Actualiza los datos de contacto del proveedor. Los campos en blanco no se modifican.
                  </p>

                  <div className="space-y-2">
                    <Label htmlFor="edit-name">Nombre / Razón Social</Label>
                    <Input
                      id="edit-name"
                      value={editForm.company_name}
                      onChange={(e) => setEditForm(f => ({ ...f, company_name: e.target.value }))}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="edit-email">Email</Label>
                      <Input
                        id="edit-email"
                        type="email"
                        value={editForm.email}
                        onChange={(e) => setEditForm(f => ({ ...f, email: e.target.value }))}
                        placeholder="correo@empresa.com"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="edit-phone">Teléfono</Label>
                      <Input
                        id="edit-phone"
                        value={editForm.phone}
                        onChange={(e) => setEditForm(f => ({ ...f, phone: e.target.value }))}
                        placeholder="+57 300 000 0000"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="edit-address">Dirección</Label>
                    <Input
                      id="edit-address"
                      value={editForm.address}
                      onChange={(e) => setEditForm(f => ({ ...f, address: e.target.value }))}
                      placeholder="Calle 123 # 45-67"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="edit-city">Ciudad</Label>
                      <Input
                        id="edit-city"
                        value={editForm.city}
                        onChange={(e) => setEditForm(f => ({ ...f, city: e.target.value }))}
                        placeholder="Bogotá"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="edit-department">Departamento</Label>
                      <Input
                        id="edit-department"
                        value={editForm.department}
                        onChange={(e) => setEditForm(f => ({ ...f, department: e.target.value }))}
                        placeholder="Cundinamarca"
                      />
                    </div>
                  </div>

                  {editError && (
                    <p className="text-sm text-red-600 bg-red-50 rounded p-3">{editError}</p>
                  )}
                  {editSuccess && (
                    <p className="text-sm text-green-700 bg-green-50 rounded p-3 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4" />
                      Proveedor actualizado correctamente
                    </p>
                  )}

                  <div className="flex gap-3 pt-2">
                    <Button
                      onClick={handleEditSave}
                      disabled={editLoading}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      {editLoading ? "Guardando..." : "Guardar Cambios"}
                    </Button>
                    <Button variant="outline" onClick={() => setActiveTab("info")}>
                      Cancelar
                    </Button>
                  </div>
                </TabsContent>

                {/* ── TAB: Facturas ── */}
                <TabsContent value="invoices">
                  {invoicesLoading ? (
                    <div className="flex items-center justify-center py-16">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
                      <span className="ml-2 text-gray-600 text-sm">Cargando facturas...</span>
                    </div>
                  ) : invoices.length === 0 ? (
                    <div className="text-center py-16">
                      <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                      <p className="text-gray-500">No hay facturas vinculadas a este proveedor</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <p className="text-sm text-gray-500">{invoices.length} factura{invoices.length !== 1 ? "s" : ""} encontrada{invoices.length !== 1 ? "s" : ""}</p>
                      <div className="overflow-x-auto">
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-gray-50">
                              <TableHead className="font-semibold">N° Factura</TableHead>
                              <TableHead className="font-semibold">Fecha</TableHead>
                              <TableHead className="font-semibold text-right">Total</TableHead>
                              <TableHead className="font-semibold text-center">Estado</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {invoices.map((inv) => (
                              <TableRow key={inv.id} className="hover:bg-gray-50">
                                <TableCell>
                                  <div>
                                    <p className="font-medium text-sm">{inv.invoice_number ?? "—"}</p>
                                    <p className="text-xs text-gray-400 truncate max-w-[160px]" title={inv.original_filename}>
                                      {inv.original_filename}
                                    </p>
                                  </div>
                                </TableCell>
                                <TableCell className="text-sm text-gray-600 whitespace-nowrap">
                                  {formatDate(inv.issue_date ?? inv.upload_timestamp)}
                                </TableCell>
                                <TableCell className="text-right font-semibold text-sm">
                                  {formatCurrency(inv.total_amount)}
                                </TableCell>
                                <TableCell className="text-center">
                                  <div className="flex items-center justify-center gap-1.5">
                                    {getInvoiceStatusIcon(inv.status)}
                                    <span className="text-xs text-gray-600">{getInvoiceStatusLabel(inv.status)}</span>
                                  </div>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
