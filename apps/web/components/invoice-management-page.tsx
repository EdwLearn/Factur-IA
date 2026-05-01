"use client"

import { useState, useMemo, useEffect } from "react"
import { useRouter } from "next/navigation"
import { facturaAPI, type InvoiceData } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Search, FileText, Download, Eye, Upload, Filter, ChevronLeft, ChevronRight, Layers, AlertTriangle, CheckSquare, Square } from "lucide-react"

interface ApiInvoice {
  id: string | null
  invoice_id?: string
  invoice_number: string
  supplier_name: string
  supplier_nit: string
  total_amount: number
  issue_date: string
  status: 'uploaded' | 'processing' | 'completed' | 'failed' | 'merged'
  upload_timestamp: string
  original_filename?: string
  line_items?: any[]
  parent_invoice_id?: string | null
  page_number?: number | null
  total_pages?: number | null
  is_consolidated?: boolean
}

interface InvoiceManagementPageProps {
  uploadedInvoices?: any[]
  invoiceStatuses?: any
  setActiveTab?: (tab: string) => void
}

export function InvoiceManagementPage({ uploadedInvoices = [], invoiceStatuses = {}, setActiveTab }: InvoiceManagementPageProps) {
  const router = useRouter()
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [vendorFilter, setVendorFilter] = useState("all")
  const [dateFilter, setDateFilter] = useState("all")
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 9

  const [invoices, setInvoices] = useState<ApiInvoice[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Merge mode state
  const [selectMode, setSelectMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [showMergeModal, setShowMergeModal] = useState(false)
  const [primaryInvoiceId, setPrimaryInvoiceId] = useState<string | null>(null)
  const [isMerging, setIsMerging] = useState(false)
  const [mergeToast, setMergeToast] = useState<string | null>(null)

  const loadInvoices = async () => {
    try {
      setLoading(true)
      const response = await facturaAPI.listInvoices(100, 0)
      if (!response.success) throw new Error(response.error?.message ?? 'Error al cargar facturas')
      const data = response.data
      if (Array.isArray(data)) {
        setInvoices(data)
      } else if (data && Array.isArray((data as any).invoices)) {
        setInvoices((data as any).invoices)
      } else {
        setInvoices([])
      }
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido')
      setInvoices([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadInvoices() }, [uploadedInvoices])

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleMergeConfirm = async () => {
    if (!primaryInvoiceId) return
    const secondaryIds = [...selectedIds].filter(id => id !== primaryInvoiceId)
    setIsMerging(true)
    try {
      const res = await facturaAPI.mergeInvoices(primaryInvoiceId, secondaryIds)
      if (!res.success) throw new Error(res.error?.message ?? 'Error al fusionar')
      setShowMergeModal(false)
      setSelectMode(false)
      setSelectedIds(new Set())
      setPrimaryInvoiceId(null)
      setMergeToast('Facturas fusionadas exitosamente')
      setTimeout(() => setMergeToast(null), 4000)
      await loadInvoices()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Error al fusionar facturas')
    } finally {
      setIsMerging(false)
    }
  }

  const filteredInvoices = useMemo(() => {
    const normalizedStatusFilter = statusFilter
    const result = invoices.filter((invoice) => {
      const matchesSearch =
        (invoice.invoice_number || '')?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (invoice.supplier_name || '')?.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesStatus = normalizedStatusFilter === "all" || invoice.status === normalizedStatusFilter
      const matchesVendor = vendorFilter === "all" || invoice.supplier_name === vendorFilter

      let matchesDate = true
      if (dateFilter !== "all") {
        const invoiceDate = new Date(invoice.upload_timestamp || invoice.issue_date)
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

    return result
  }, [invoices, searchTerm, statusFilter, vendorFilter, dateFilter])

  const totalPages = Math.ceil(filteredInvoices.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const paginatedInvoices = filteredInvoices.slice(startIndex, startIndex + itemsPerPage)

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  const formatDate = (dateString: string) => {
    if (!dateString) return 'Fecha no disponible'
  
    try {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return 'Fecha no disponible'
    
      return date.toLocaleDateString("es-CO", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    } catch {
      return 'Fecha inválida'
    }
  }

  const getStatusBadge = (status: ApiInvoice["status"]) => {
    switch (status) {
      case "completed":
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-100 font-medium">Completada</Badge>
      case "processing":
        return <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100 font-medium">Procesando</Badge>
      case "uploaded":
        return <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100 font-medium">Subida</Badge>
      case "failed":
        return <Badge className="bg-red-100 text-red-800 hover:bg-red-100 font-medium">Error</Badge>
      case "merged":
        return <Badge className="bg-purple-100 text-purple-800 hover:bg-purple-100 font-medium">Fusionada</Badge>
      default:
        return null
    }
  }

  const vendors = [...new Set(invoices.map((invoice) => invoice.supplier_name).filter(Boolean))]

  const handleViewDetails = (invoiceId: string) => {
    router.push(`/invoices/${invoiceId}`)
  }

  const handleDownloadPDF = async (invoiceId: string) => {
    try {
      const res = await facturaAPI.getDownloadUrl(invoiceId)
      if (!res.success || !res.data?.url) {
        alert('No se pudo obtener el enlace de descarga')
        return
      }
      const a = document.createElement('a')
      a.href = res.data.url
      a.download = res.data.filename
      a.target = '_blank'
      a.rel = 'noopener noreferrer'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    } catch (error) {
      alert('Error al descargar la factura')
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
      {/* Toast de éxito fusión */}
      {mergeToast && (
        <div className="fixed top-4 right-4 z-50 bg-green-600 text-white px-5 py-3 rounded-lg shadow-lg text-sm font-medium animate-in fade-in slide-in-from-top-2">
          {mergeToast}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestión de Facturas</h1>
          <p className="text-gray-600">Administra y procesa tus facturas de proveedores</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => {
              setSelectMode(!selectMode)
              setSelectedIds(new Set())
              setPrimaryInvoiceId(null)
            }}
            className="flex items-center gap-2 border border-gray-200 rounded-lg px-4 py-2 text-sm hover:bg-gray-50 transition-colors"
          >
            <Layers className="h-4 w-4" />
            {selectMode ? "Cancelar selección" : "Fusionar páginas"}
          </button>
          <Button className="bg-blue-600 hover:bg-blue-700 w-fit" onClick={() => setActiveTab?.('Dashboard')}>
            <Upload className="w-4 h-4 mr-2" />
            Subir Nueva Factura
          </Button>
        </div>
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
                  <SelectItem value="uploaded">Subida</SelectItem>
                  <SelectItem value="failed">Error</SelectItem>
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
        {paginatedInvoices.map((invoice, idx) => {
          const key =
            (invoice.id && String(invoice.id)) ||
            invoice.invoice_number ||
            invoice.original_filename ||
            `${invoice.upload_timestamp}-${idx}`

          return (
            <Card
              key={key}
              className={`hover:shadow-lg transition-shadow duration-200 ${
                selectMode && invoice.id && selectedIds.has(String(invoice.id))
                  ? 'ring-2 ring-blue-500'
                  : ''
              }`}
              onClick={selectMode && invoice.id ? () => toggleSelect(String(invoice.id)) : undefined}
              style={selectMode ? { cursor: 'pointer' } : undefined}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-2">
                    {selectMode && invoice.id && (
                      <div className="mt-0.5 flex-shrink-0">
                        {selectedIds.has(String(invoice.id))
                          ? <CheckSquare className="w-5 h-5 text-blue-600" />
                          : <Square className="w-5 h-5 text-gray-400" />
                        }
                      </div>
                    )}
                    <div>
                      <CardTitle className="text-lg font-semibold text-gray-900 mb-1">
                        {invoice.invoice_number
                        || invoice.original_filename
                        || (invoice.id ? `ID: ${String(invoice.id).slice(0, 8)}...` : 'Factura')}
                      </CardTitle>
                      <p className="text-sm text-gray-600">{formatDate(invoice.issue_date || invoice.upload_timestamp)}</p>
                    </div>
                  </div>
                  {getStatusBadge(invoice.status)}
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-3">
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-1">Proveedor</p>
                    <p className="text-sm text-gray-900">
                      {invoice.supplier_name || 'Proveedor no disponible'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-1">Estado</p>
                    <p className="text-sm text-gray-600">
                      {invoice.status === 'completed' ? 'Datos extraídos' : 'Procesando datos...'}
                      {invoice.total_pages && invoice.total_pages > 1 && (
                        <span className="ml-2 inline-flex items-center gap-1 text-xs text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded font-medium">
                          <Layers className="w-3 h-3" />
                          {invoice.total_pages} páginas
                        </span>
                      )}
                    </p>
                  </div>

                  <div className="pt-2 border-t border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-sm font-medium text-gray-700">Total</span>
                      <span className="text-lg font-bold text-gray-900">
                        {invoice.total_amount != null && invoice.total_amount > 0
                          ? formatCurrency(Number(invoice.total_amount))
                          : (invoice as any).total != null && (invoice as any).total > 0
                            ? formatCurrency(Number((invoice as any).total))
                            : invoice.status === 'completed'
                              ? 'Sin total'
                              : 'Calculando...'}
                      </span>
                    </div>

                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1 text-blue-600 border-blue-200 hover:bg-blue-50 bg-transparent"
                        onClick={() => (invoice.id ? handleViewDetails(String(invoice.id)) : alert('Factura sin ID'))}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        Ver Detalles
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1 text-gray-600 hover:bg-gray-50 bg-transparent"
                        onClick={() => (invoice.id ? handleDownloadPDF(String(invoice.id)) : alert('Factura sin ID'))}
                      >
                        <Download className="w-4 h-4 mr-1" />
                        PDF
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
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

      {/* Banner de selección activa */}
      {selectMode && selectedIds.size >= 2 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-white border border-gray-200 rounded-xl shadow-xl px-6 py-4 flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700">
            {selectedIds.size} facturas seleccionadas
          </span>
          <button
            onClick={() => { setSelectMode(false); setSelectedIds(new Set()); setPrimaryInvoiceId(null) }}
            className="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Cancelar
          </button>
          <button
            onClick={() => {
              const ids = [...selectedIds]
              setPrimaryInvoiceId(ids[0])
              setShowMergeModal(true)
            }}
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            Fusionar en una sola →
          </button>
        </div>
      )}

      {/* Modal de confirmación de fusión */}
      {showMergeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md mx-4">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Fusionar facturas</h2>

            <p className="text-sm text-gray-600 mb-3">Se unirán los ítems de:</p>
            <ul className="mb-4 space-y-1">
              {[...selectedIds].map(id => {
                const inv = invoices.find(i => String(i.id) === id)
                return (
                  <li key={id} className="text-sm text-gray-700 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                    {inv?.invoice_number || inv?.original_filename || `ID: ${id.slice(0, 8)}…`}
                    {inv?.supplier_name ? ` — ${inv.supplier_name}` : ''}
                    {inv?.total_amount ? ` — $${Number(inv.total_amount).toLocaleString('es-CO')}` : ''}
                  </li>
                )
              })}
            </ul>

            <p className="text-sm text-gray-600 mb-2">¿Cuál es la factura principal (la que queda)?</p>
            <div className="space-y-2 mb-5">
              {[...selectedIds].map((id, idx) => {
                const inv = invoices.find(i => String(i.id) === id)
                return (
                  <label key={id} className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="radio"
                      name="primary"
                      value={id}
                      checked={primaryInvoiceId === id}
                      onChange={() => setPrimaryInvoiceId(id)}
                      className="accent-blue-600"
                    />
                    <span className="text-sm text-gray-700">
                      {inv?.invoice_number || `Factura ${idx + 1}`}
                      {idx === 0 ? ' (la primera seleccionada)' : ''}
                    </span>
                  </label>
                )
              })}
            </div>

            <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg mb-5">
              <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-yellow-700">Esta acción no se puede deshacer. Las facturas secundarias quedarán marcadas como fusionadas.</p>
            </div>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowMergeModal(false)}
                className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleMergeConfirm}
                disabled={isMerging || !primaryInvoiceId}
                className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 transition-colors"
              >
                {isMerging ? 'Fusionando...' : 'Confirmar fusión'}
              </button>
            </div>
          </div>
        </div>
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
