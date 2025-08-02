"use client"

import { useState, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import {
  Search,
  Users,
  Plus,
  Phone,
  Mail,
  MapPin,
  FileText,
  Calendar,
  TrendingUp,
  Building2,
  Eye,
  Edit,
  MoreHorizontal,
} from "lucide-react"

interface Supplier {
  id: string
  name: string
  vatNumber: string
  email: string
  phone: string
  city: string
  address: string
  type: "manufacturer" | "distributor" | "wholesaler" | "service"
  status: "active" | "inactive"
  totalInvoices: number
  totalAmount: number
  lastInvoiceDate: string
  joinDate: string
  contactPerson: string
}

const sampleSuppliers: Supplier[] = [
  {
    id: "1",
    name: "Distribuidora Medellín S.A.S",
    vatNumber: "900123456-1",
    email: "ventas@dismedellin.com.co",
    phone: "+57 4 123-4567",
    city: "Medellín",
    address: "Carrera 70 #45-23, El Poblado",
    type: "distributor",
    status: "active",
    totalInvoices: 45,
    totalAmount: 125000000,
    lastInvoiceDate: "2024-01-15",
    joinDate: "2023-03-15",
    contactPerson: "María González",
  },
  {
    id: "2",
    name: "Calzado Colombia Ltda",
    vatNumber: "800987654-2",
    email: "pedidos@calzadocol.com.co",
    phone: "+57 1 987-6543",
    city: "Bogotá",
    address: "Calle 127 #15-45, Zona Rosa",
    type: "manufacturer",
    status: "active",
    totalInvoices: 32,
    totalAmount: 89500000,
    lastInvoiceDate: "2024-01-14",
    joinDate: "2023-01-20",
    contactPerson: "Carlos Rodríguez",
  },
  {
    id: "3",
    name: "Textiles Antioquia S.A.",
    vatNumber: "900555777-3",
    email: "comercial@textilant.com.co",
    phone: "+57 4 555-7777",
    city: "Medellín",
    address: "Zona Industrial Itagüí",
    type: "manufacturer",
    status: "active",
    totalInvoices: 67,
    totalAmount: 198000000,
    lastInvoiceDate: "2024-01-12",
    joinDate: "2022-11-10",
    contactPerson: "Ana Martínez",
  },
  {
    id: "4",
    name: "Accesorios y Más S.A.S",
    vatNumber: "900333444-4",
    email: "info@accesoriosymas.co",
    phone: "+57 2 333-4444",
    city: "Cali",
    address: "Avenida 6N #28-45",
    type: "wholesaler",
    status: "active",
    totalInvoices: 28,
    totalAmount: 45600000,
    lastInvoiceDate: "2024-01-13",
    joinDate: "2023-06-05",
    contactPerson: "Luis Herrera",
  },
  {
    id: "5",
    name: "Proveedora Nacional Ltda",
    vatNumber: "800111222-5",
    email: "ventas@provnacional.com.co",
    phone: "+57 1 111-2222",
    city: "Bogotá",
    address: "Carrera 30 #45-67, Centro",
    type: "distributor",
    status: "inactive",
    totalInvoices: 15,
    totalAmount: 23400000,
    lastInvoiceDate: "2023-12-20",
    joinDate: "2023-08-12",
    contactPerson: "Patricia Silva",
  },
  {
    id: "6",
    name: "Comercializadora Bogotá S.A.S",
    vatNumber: "900777888-6",
    email: "contacto@combogota.co",
    phone: "+57 1 777-8888",
    city: "Bogotá",
    address: "Zona Industrial Puente Aranda",
    type: "distributor",
    status: "active",
    totalInvoices: 52,
    totalAmount: 134500000,
    lastInvoiceDate: "2024-01-10",
    joinDate: "2023-02-28",
    contactPerson: "Roberto Jiménez",
  },
  {
    id: "7",
    name: "Servicios Logísticos del Valle",
    vatNumber: "900999000-7",
    email: "servicios@logvalle.com.co",
    phone: "+57 2 999-0000",
    city: "Cali",
    address: "Zona Franca del Pacífico",
    type: "service",
    status: "active",
    totalInvoices: 18,
    totalAmount: 28900000,
    lastInvoiceDate: "2024-01-11",
    joinDate: "2023-09-15",
    contactPerson: "Sandra López",
  },
  {
    id: "8",
    name: "Manufacturas del Caribe S.A.",
    vatNumber: "800444555-8",
    email: "produccion@mancaribe.co",
    phone: "+57 5 444-5555",
    city: "Barranquilla",
    address: "Vía 40 #85-123",
    type: "manufacturer",
    status: "active",
    totalInvoices: 39,
    totalAmount: 87300000,
    lastInvoiceDate: "2024-01-09",
    joinDate: "2023-04-18",
    contactPerson: "Miguel Torres",
  },
]

export function SupplierManagementPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [cityFilter, setCityFilter] = useState("all")
  const [typeFilter, setTypeFilter] = useState("all")
  const [statusFilter, setStatusFilter] = useState("all")
  const [selectedSupplier, setSelectedSupplier] = useState<Supplier | null>(null)

  const filteredSuppliers = useMemo(() => {
    return sampleSuppliers.filter((supplier) => {
      const matchesSearch =
        supplier.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        supplier.vatNumber.includes(searchTerm) ||
        supplier.contactPerson.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesCity = cityFilter === "all" || supplier.city === cityFilter
      const matchesType = typeFilter === "all" || supplier.type === typeFilter
      const matchesStatus = statusFilter === "all" || supplier.status === statusFilter

      return matchesSearch && matchesCity && matchesType && matchesStatus
    })
  }, [searchTerm, cityFilter, typeFilter, statusFilter])

  const metrics = useMemo(() => {
    const totalSuppliers = sampleSuppliers.length
    const activeSuppliers = sampleSuppliers.filter((s) => s.status === "active").length

    // Simulate "new this month" - suppliers joined in the last 30 days
    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
    const newThisMonth = sampleSuppliers.filter((s) => new Date(s.joinDate) >= thirtyDaysAgo).length

    return {
      totalSuppliers,
      activeSuppliers,
      newThisMonth,
    }
  }, [])

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      minimumFractionDigits: 0,
    }).format(amount)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("es-CO", {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  }

  const getSupplierTypeLabel = (type: Supplier["type"]) => {
    const types = {
      manufacturer: "Fabricante",
      distributor: "Distribuidor",
      wholesaler: "Mayorista",
      service: "Servicios",
    }
    return types[type]
  }

  const getSupplierTypeColor = (type: Supplier["type"]) => {
    const colors = {
      manufacturer: "bg-blue-100 text-blue-800",
      distributor: "bg-green-100 text-green-800",
      wholesaler: "bg-purple-100 text-purple-800",
      service: "bg-orange-100 text-orange-800",
    }
    return colors[type]
  }

  const getStatusBadge = (status: Supplier["status"]) => {
    return status === "active" ? (
      <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Activo</Badge>
    ) : (
      <Badge className="bg-gray-100 text-gray-800 hover:bg-gray-100">Inactivo</Badge>
    )
  }

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((word) => word[0])
      .join("")
      .substring(0, 2)
      .toUpperCase()
  }

  const cities = [...new Set(sampleSuppliers.map((s) => s.city))]
  const types = ["manufacturer", "distributor", "wholesaler", "service"] as const

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestión de Proveedores</h1>
          <p className="text-gray-600">Administra tu red de proveedores y socios comerciales</p>
        </div>
        <Button className="bg-blue-600 hover:bg-blue-700 w-fit">
          <Plus className="w-4 h-4 mr-2" />
          Agregar Proveedor
        </Button>
      </div>

      {/* Metrics Cards */}
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
            <div className="flex items-center mt-2">
              <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
              <span className="text-sm text-green-600">+8% este mes</span>
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
            <div className="flex items-center mt-2">
              <span className="text-sm text-gray-600">
                {((metrics.activeSuppliers / metrics.totalSuppliers) * 100).toFixed(0)}% del total
              </span>
            </div>
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
              <span className="text-sm text-green-600">Crecimiento constante</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="Buscar por nombre, NIT o contacto..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-4">
              <Select value={cityFilter} onValueChange={setCityFilter}>
                <SelectTrigger className="w-full sm:w-48">
                  <SelectValue placeholder="Ciudad" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas las ciudades</SelectItem>
                  {cities.map((city) => (
                    <SelectItem key={city} value={city}>
                      {city}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-full sm:w-48">
                  <SelectValue placeholder="Tipo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los tipos</SelectItem>
                  {types.map((type) => (
                    <SelectItem key={type} value={type}>
                      {getSupplierTypeLabel(type)}
                    </SelectItem>
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

      {/* Results Summary */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          Mostrando {filteredSuppliers.length} de {sampleSuppliers.length} proveedores
        </p>
      </div>

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
                    <CardTitle className="text-lg font-semibold text-gray-900 mb-1">{supplier.name}</CardTitle>
                    <p className="text-sm text-gray-600">NIT: {supplier.vatNumber}</p>
                  </div>
                </div>
                {getStatusBadge(supplier.status)}
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge className={`${getSupplierTypeColor(supplier.type)} text-xs px-2 py-1`}>
                    {getSupplierTypeLabel(supplier.type)}
                  </Badge>
                  <span className="text-sm text-gray-600">{supplier.city}</span>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Phone className="w-4 h-4" />
                    <span>{supplier.phone}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Mail className="w-4 h-4" />
                    <span className="truncate">{supplier.email}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <MapPin className="w-4 h-4" />
                    <span className="truncate">{supplier.address}</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-gray-100">
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <p className="text-xs text-gray-500">Total Facturas</p>
                      <p className="text-sm font-semibold text-gray-900">{supplier.totalInvoices}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Monto Total</p>
                      <p className="text-sm font-semibold text-gray-900">{formatCurrency(supplier.totalAmount)}</p>
                    </div>
                  </div>

                  <div className="mb-4">
                    <p className="text-xs text-gray-500">Última Factura</p>
                    <p className="text-sm text-gray-900">{formatDate(supplier.lastInvoiceDate)}</p>
                  </div>

                  <div className="flex gap-2">
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1 text-blue-600 border-blue-200 hover:bg-blue-50 bg-transparent"
                          onClick={() => setSelectedSupplier(supplier)}
                        >
                          <Eye className="w-4 h-4 mr-1" />
                          Ver Perfil
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-2xl">
                        <DialogHeader>
                          <DialogTitle className="flex items-center gap-3">
                            <Avatar className="w-12 h-12">
                              <AvatarFallback className="bg-blue-600 text-white font-semibold">
                                {getInitials(supplier.name)}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <h2 className="text-xl font-bold">{supplier.name}</h2>
                              <p className="text-sm text-gray-600">NIT: {supplier.vatNumber}</p>
                            </div>
                          </DialogTitle>
                        </DialogHeader>

                        <div className="space-y-6">
                          {/* Status and Type */}
                          <div className="flex gap-4">
                            {getStatusBadge(supplier.status)}
                            <Badge className={`${getSupplierTypeColor(supplier.type)}`}>
                              {getSupplierTypeLabel(supplier.type)}
                            </Badge>
                          </div>

                          {/* Contact Information */}
                          <div>
                            <h3 className="font-semibold text-gray-900 mb-3">Información de Contacto</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              <div className="space-y-3">
                                <div className="flex items-center gap-2">
                                  <Phone className="w-4 h-4 text-gray-400" />
                                  <span className="text-sm">{supplier.phone}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <Mail className="w-4 h-4 text-gray-400" />
                                  <span className="text-sm">{supplier.email}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <Users className="w-4 h-4 text-gray-400" />
                                  <span className="text-sm">{supplier.contactPerson}</span>
                                </div>
                              </div>
                              <div>
                                <div className="flex items-start gap-2">
                                  <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
                                  <div>
                                    <p className="text-sm">{supplier.address}</p>
                                    <p className="text-sm text-gray-600">{supplier.city}</p>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Business Metrics */}
                          <div>
                            <h3 className="font-semibold text-gray-900 mb-3">Métricas Comerciales</h3>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                              <div className="bg-gray-50 p-3 rounded-lg">
                                <p className="text-xs text-gray-500">Total Facturas</p>
                                <p className="text-lg font-semibold text-gray-900">{supplier.totalInvoices}</p>
                              </div>
                              <div className="bg-gray-50 p-3 rounded-lg">
                                <p className="text-xs text-gray-500">Monto Total</p>
                                <p className="text-lg font-semibold text-gray-900">
                                  {formatCurrency(supplier.totalAmount)}
                                </p>
                              </div>
                              <div className="bg-gray-50 p-3 rounded-lg">
                                <p className="text-xs text-gray-500">Última Factura</p>
                                <p className="text-sm font-semibold text-gray-900">
                                  {formatDate(supplier.lastInvoiceDate)}
                                </p>
                              </div>
                              <div className="bg-gray-50 p-3 rounded-lg">
                                <p className="text-xs text-gray-500">Cliente Desde</p>
                                <p className="text-sm font-semibold text-gray-900">{formatDate(supplier.joinDate)}</p>
                              </div>
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="flex gap-3 pt-4 border-t">
                            <Button className="bg-blue-600 hover:bg-blue-700">
                              <Edit className="w-4 h-4 mr-2" />
                              Editar Proveedor
                            </Button>
                            <Button variant="outline">
                              <FileText className="w-4 h-4 mr-2" />
                              Ver Facturas
                            </Button>
                          </div>
                        </div>
                      </DialogContent>
                    </Dialog>

                    <Button variant="outline" size="sm" className="text-gray-600 hover:bg-gray-50 bg-transparent">
                      <MoreHorizontal className="w-4 h-4" />
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
            <p className="text-gray-500 mb-6">Intenta ajustar los filtros de búsqueda o agrega un nuevo proveedor</p>
            <Button className="bg-blue-600 hover:bg-blue-700">
              <Plus className="w-4 h-4 mr-2" />
              Agregar Proveedor
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
