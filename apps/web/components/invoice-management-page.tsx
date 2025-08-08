"use client"

import { useState, useMemo, useEffect } from "react"
import { facturaAPI, type InvoiceData } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Search, FileText, Download, Eye, Upload, Filter, ChevronLeft, ChevronRight } from "lucide-react"

interface ApiInvoice {
  id: string
  invoice_number: string
  supplier_name: string
  supplier_nit: string
  total_amount: number
  issue_date: string
  status: 'uploaded' | 'processing' | 'completed' | 'failed'
  upload_timestamp: string
  line_items?: any[]
}

interface InvoiceManagementPageProps {
  uploadedInvoices?: any[]
  invoiceStatuses?: any
}

export function InvoiceManagementPage({ uploadedInvoices = [], invoiceStatuses = {} }: InvoiceManagementPageProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [vendorFilter, setVendorFilter] = useState("all")
  const [dateFilter, setDateFilter] = useState("all")
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 9

  const [invoices, setInvoices] = useState<ApiInvoice[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadInvoices = async () => {
      try {
        setLoading(true)
        console.log('🔄 Cargando facturas desde API...')
        
        const response = await facturaAPI.listInvoices(100, 0)
        const apiInvoices = response.invoices || []

        const allInvoices = [...apiInvoices, ...uploadedInvoices.map(inv => ({
          id: inv.id,
          invoice_number: inv.original_filename,
          supplier_name: 'Procesando...',
          supplier_nit: '',
          total_amount: 0,
          issue_date: inv.upload_timestamp,
          status: 'uploaded',
          upload_timestamp: inv.upload_timestamp
        }))]
        
        const mappedInvoices: ApiInvoice[] = response.invoices || []
        setInvoices(allInvoices)
        setError(null)
        
      } catch (err) {
      // Si falla la API, usar solo las facturas subidas
      const localInvoices = uploadedInvoices.map(inv => {
        const currentStatus = invoiceStatuses[inv.id] || { status: 'uploaded' }
  
        return {
        id: inv.id,
        invoice_number: inv.original_filename.replace(/\.(pdf|jpg|jpeg|png)$/i, ''),
        supplier_name: currentStatus.status === 'completed' ? 'Datos disponibles' : 'Extrayendo datos...',
        supplier_nit: currentStatus.status === 'completed' ? 'Ver detalles' : '',
        total_amount: 0,
        issue_date: inv.upload_timestamp,
        status: currentStatus.status,
        upload_timestamp: inv.upload_timestamp,
        original_filename: inv.original_filename
      }
    })
      setInvoices(localInvoices)
      setError(null)
    } finally {
      setLoading(false)
    }
  }

    loadInvoices()
  }, [uploadedInvoices])

  const filteredInvoices = useMemo(() => {
    return invoices.filter((invoice) => {
      const matchesSearch =
        (invoice.invoice_number || '')?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (invoice.supplier_name || '')?.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesStatus = statusFilter === "all" || invoice.status === statusFilter
      const matchesVendor = vendorFilter === "all" || invoice.supplier_name  === vendorFilter

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

    return filteredInvoices
  }, [invoices, searchTerm, statusFilter, vendorFilter, dateFilter])

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
    if (!dateString) return 'Fecha no disponible'
  
    try {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return 'Fecha inválida'
    
      return date.toLocaleDateString("es-CO", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    } catch {
      return 'Fecha inválida'
    }
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

  const vendors = [...new Set(invoices.map((invoice) => invoice.supplier_name).filter(Boolean))]

  const handleViewDetails = async (invoiceId: string) => {
    try {
      // Verificar si la factura está completa
      const status = invoiceStatuses[invoiceId]
      if (status?.status !== 'completed') {
        alert('⏳ La factura aún se está procesando. Intenta en unos momentos.')
        return
      }
    
      // Obtener datos de la factura
      const invoiceData = await facturaAPI.getInvoiceData(invoiceId)
      alert(`✅ Factura: ${invoiceData.invoice_number}\nProveedor: ${invoiceData.supplier?.company_name}\nTotal: ${formatCurrency(invoiceData.totals?.total || 0)}`)
    } catch (error) {
      alert('❌ Error al cargar los detalles de la factura')
    }
  }

  const handleDownloadPDF = async (invoiceId: string) => {
    try {
      const status = invoiceStatuses[invoiceId]
      if (status?.status !== 'completed') {
        alert('⏳ Los datos aún se están extrayendo. Intenta en unos momentos.')
        return
      }
    
      const pricingData = await facturaAPI.getPricingInfo(invoiceId)
      console.log('📊 Datos de la factura:', pricingData)
      alert(`📋 Datos disponibles:\n${pricingData.total_items} productos\nTotal: ${formatCurrency(pricingData.total_cost)}`)
    } catch (error) {
      alert('❌ Error al obtener los datos de la factura')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Cargando facturas...</span>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <FileText className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Error cargando facturas</h3>
          <p className="text-red-600 mb-6">{error}</p>
          <Button onClick={() => window.location.reload()} className="bg-blue-600 hover:bg-blue-700">
            Reintentar
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Button 
        onClick={async () => {
          try {
            const invoiceData = await facturaAPI.getInvoiceData('1ecf71dc-69a3-46bb-b8c9-d226b39ad823');
            console.log('📊 Datos completos de Textract:', invoiceData);
      
            const pricingData = await facturaAPI.getPricingInfo('1ecf71dc-69a3-46bb-b8c9-d226b39ad823');
            console.log('💰 Datos de precios:', pricingData);
          } catch (err) {
            console.error('❌ Error:', err);
          }
        }}
        variant="outline"
      >
        🔍 Ver Datos Factura
      </Button>


      <Button 
        onClick={async () => {
          try {
            const test = await facturaAPI.testEndpoint()
            console.log('🧪 Test API:', test)
      
            const invoices = await facturaAPI.listInvoices(10, 0)
            console.log('📋 Lista facturas:', invoices)
          } catch (err) {
            console.error('❌ Error test:', err)
          }
        }}
        variant="outline"
      >
      🧪 Test API
      </Button>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestión de Facturas</h1>
          <p className="text-gray-600">Administra y procesa tus facturas de proveedores</p>
        </div>
        <Button className="bg-blue-600 hover:bg-blue-700 w-fit" onClick={() => window.location.href = '/'}>
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
            {filteredInvoices.length !== invoices.length && "Filtros aplicados"}
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
                  <CardTitle className="text-lg font-semibold text-gray-900 mb-1">
                    {invoice.invoice_number || invoice.original_filename || `ID: ${invoice.id.substring(0, 8)}...`}
                  </CardTitle>
                  <p className="text-sm text-gray-600">{formatDate(invoice.date)}</p>
                </div>
                {getStatusBadge(invoice.status)}
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">Proveedor</p>
                  <p className="text-sm text-gray-900">
                    {invoice.supplier_name || 'Extrayendo datos...'}
                  </p>
                </div>

                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">Estado</p>
                  <p className="text-sm text-gray-600">
                    {invoice.status === 'completed' ? 'Datos extraídos' : 'Procesando datos...'}
                  </p>
                </div>

                <div className="pt-2 border-t border-gray-100">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-medium text-gray-700">Total</span>
                    <span className="text-lg font-bold text-gray-900">
                      {invoice.total_amount && invoice.total_amount > 0
                      ? formatCurrency(invoice.total_amount)
                      : 'Procesando...'}
                    </span>
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
