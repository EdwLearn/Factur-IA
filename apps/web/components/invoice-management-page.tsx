"use client"

import { useState, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Search, FileText, Download, Eye, Upload, Filter, ChevronLeft, ChevronRight } from "lucide-react"

interface Invoice {
  id: string
  number: string
  vendor: string
  total: number
  status: "completed" | "processing" | "pending"
  date: string
  description: string
}

const sampleInvoices: Invoice[] = [
  {
    id: "1",
    number: "FAC-2024-001",
    vendor: "Distribuidora Medellín S.A.S",
    total: 2450000,
    status: "completed",
    date: "2024-01-15",
    description: "Productos textiles y confecciones",
  },
  {
    id: "2",
    number: "FAC-2024-002",
    vendor: "Calzado Colombia Ltda",
    total: 1850000,
    status: "processing",
    date: "2024-01-14",
    description: "Calzado deportivo y casual",
  },
  {
    id: "3",
    number: "FAC-2024-003",
    vendor: "Accesorios y Más S.A.S",
    total: 890000,
    status: "pending",
    date: "2024-01-13",
    description: "Accesorios de moda y complementos",
  },
  {
    id: "4",
    number: "FAC-2024-004",
    vendor: "Textiles Antioquia S.A.",
    total: 3200000,
    status: "completed",
    date: "2024-01-12",
    description: "Telas y materiales textiles",
  },
  {
    id: "5",
    number: "FAC-2024-005",
    vendor: "Proveedora Nacional Ltda",
    total: 1650000,
    status: "processing",
    date: "2024-01-11",
    description: "Productos varios para retail",
  },
  {
    id: "6",
    number: "FAC-2024-006",
    vendor: "Comercializadora Bogotá S.A.S",
    total: 2100000,
    status: "pending",
    date: "2024-01-10",
    description: "Mercancía general",
  },
  {
    id: "7",
    number: "FAC-2024-007",
    vendor: "Distribuidora Medellín S.A.S",
    total: 1750000,
    status: "completed",
    date: "2024-01-09",
    description: "Productos de temporada",
  },
  {
    id: "8",
    number: "FAC-2024-008",
    vendor: "Calzado Colombia Ltda",
    total: 2800000,
    status: "processing",
    date: "2024-01-08",
    description: "Calzado de trabajo y seguridad",
  },
  {
    id: "9",
    number: "FAC-2024-009",
    vendor: "Accesorios y Más S.A.S",
    total: 950000,
    status: "completed",
    date: "2024-01-07",
    description: "Bisutería y accesorios",
  },
  {
    id: "10",
    number: "FAC-2024-010",
    vendor: "Textiles Antioquia S.A.",
    total: 4200000,
    status: "pending",
    date: "2024-01-06",
    description: "Materiales premium",
  },
  {
    id: "11",
    number: "FAC-2024-011",
    vendor: "Proveedora Nacional Ltda",
    total: 1450000,
    status: "completed",
    date: "2024-01-05",
    description: "Productos de consumo masivo",
  },
  {
    id: "12",
    number: "FAC-2024-012",
    vendor: "Comercializadora Bogotá S.A.S",
    total: 3100000,
    status: "processing",
    date: "2024-01-04",
    description: "Productos especializados",
  },
]

export function InvoiceManagementPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [vendorFilter, setVendorFilter] = useState("all")
  const [dateFilter, setDateFilter] = useState("all")
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 9

  const filteredInvoices = useMemo(() => {
    const filtered = sampleInvoices.filter((invoice) => {
      const matchesSearch =
        invoice.number.toLowerCase().includes(searchTerm.toLowerCase()) ||
        invoice.vendor.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesStatus = statusFilter === "all" || invoice.status === statusFilter
      const matchesVendor = vendorFilter === "all" || invoice.vendor === vendorFilter

      let matchesDate = true
      if (dateFilter !== "all") {
        const invoiceDate = new Date(invoice.date)
        const now = new Date()
        const diffTime = now.getTime() - invoiceDate.getTime()
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

        switch (dateFilter) {
          case "7days":
            matchesDate = diffDays <= 7
            break
          case "month":
            matchesDate = diffDays <= 30
            break
          case "quarter":
            matchesDate = diffDays <= 90
            break
        }
      }

      return matchesSearch && matchesStatus && matchesVendor && matchesDate
    })

    return filtered
  }, [searchTerm, statusFilter, vendorFilter, dateFilter])

  const totalPages = Math.ceil(filteredInvoices.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const paginatedInvoices = filteredInvoices.slice(startIndex, startIndex + itemsPerPage)

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

  const getStatusBadge = (status: Invoice["status"]) => {
    switch (status) {
      case "completed":
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-100 font-medium">Completada</Badge>
      case "processing":
        return <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100 font-medium">Procesando</Badge>
      case "pending":
        return <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100 font-medium">Pendiente</Badge>
    }
  }

  const vendors = [...new Set(sampleInvoices.map((invoice) => invoice.vendor))]

  const handleViewDetails = (invoiceId: string) => {
    alert(`Ver detalles de la factura ${invoiceId}`)
  }

  const handleDownloadPDF = (invoiceNumber: string) => {
    alert(`Descargando PDF de la factura ${invoiceNumber}`)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestión de Facturas</h1>
          <p className="text-gray-600">Administra y procesa tus facturas de proveedores</p>
        </div>
        <Button className="bg-blue-600 hover:bg-blue-700 w-fit">
          <Upload className="w-4 h-4 mr-2" />
          Subir Nueva Factura
        </Button>
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
                  placeholder="Buscar por número de factura o proveedor..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-4">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-48">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los estados</SelectItem>
                  <SelectItem value="completed">Completada</SelectItem>
                  <SelectItem value="processing">Procesando</SelectItem>
                  <SelectItem value="pending">Pendiente</SelectItem>
                </SelectContent>
              </Select>

              <Select value={vendorFilter} onValueChange={setVendorFilter}>
                <SelectTrigger className="w-full sm:w-48">
                  <SelectValue placeholder="Proveedor" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los proveedores</SelectItem>
                  {vendors.map((vendor) => (
                    <SelectItem key={vendor} value={vendor}>
                      {vendor}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={dateFilter} onValueChange={setDateFilter}>
                <SelectTrigger className="w-full sm:w-48">
                  <SelectValue placeholder="Período" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los períodos</SelectItem>
                  <SelectItem value="7days">Últimos 7 días</SelectItem>
                  <SelectItem value="month">Último mes</SelectItem>
                  <SelectItem value="quarter">Último trimestre</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results Summary */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          Mostrando {paginatedInvoices.length} de {filteredInvoices.length} facturas
        </p>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-600">
            {filteredInvoices.length !== sampleInvoices.length && "Filtros aplicados"}
          </span>
        </div>
      </div>

      {/* Invoice Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {paginatedInvoices.map((invoice) => (
          <Card key={invoice.id} className="hover:shadow-lg transition-shadow duration-200">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-lg font-semibold text-gray-900 mb-1">{invoice.number}</CardTitle>
                  <p className="text-sm text-gray-600">{formatDate(invoice.date)}</p>
                </div>
                {getStatusBadge(invoice.status)}
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">Proveedor</p>
                  <p className="text-sm text-gray-900">{invoice.vendor}</p>
                </div>

                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">Descripción</p>
                  <p className="text-sm text-gray-600 line-clamp-2">{invoice.description}</p>
                </div>

                <div className="pt-2 border-t border-gray-100">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-medium text-gray-700">Total</span>
                    <span className="text-lg font-bold text-gray-900">{formatCurrency(invoice.total)}</span>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1 text-blue-600 border-blue-200 hover:bg-blue-50 bg-transparent"
                      onClick={() => handleViewDetails(invoice.id)}
                    >
                      <Eye className="w-4 h-4 mr-1" />
                      Ver Detalles
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1 text-gray-600 hover:bg-gray-50 bg-transparent"
                      onClick={() => handleDownloadPDF(invoice.number)}
                    >
                      <Download className="w-4 h-4 mr-1" />
                      PDF
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {filteredInvoices.length === 0 && (
        <Card>
          <CardContent className="p-12 text-center">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No se encontraron facturas</h3>
            <p className="text-gray-500 mb-6">Intenta ajustar los filtros de búsqueda o sube una nueva factura</p>
            <Button className="bg-blue-600 hover:bg-blue-700">
              <Upload className="w-4 h-4 mr-2" />
              Subir Nueva Factura
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">
                  Página {currentPage} de {totalPages}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="w-4 h-4" />
                  Anterior
                </Button>

                <div className="flex gap-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum
                    if (totalPages <= 5) {
                      pageNum = i + 1
                    } else if (currentPage <= 3) {
                      pageNum = i + 1
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i
                    } else {
                      pageNum = currentPage - 2 + i
                    }

                    return (
                      <Button
                        key={pageNum}
                        variant={currentPage === pageNum ? "default" : "outline"}
                        size="sm"
                        onClick={() => setCurrentPage(pageNum)}
                        className={currentPage === pageNum ? "bg-blue-600 hover:bg-blue-700" : "hover:bg-gray-50"}
                      >
                        {pageNum}
                      </Button>
                    )
                  })}
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                >
                  Siguiente
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
