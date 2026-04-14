"use client"

import type React from "react"

import { useState, useCallback, useRef, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { calculatePrice, formatPrice, useMarkupConfig } from "@/lib/simplePricing"
import {
  FileText,
  Package,
  Users,
  BarChart3,
  Settings,
  Calculator,
  Upload,
  Camera,
  TrendingUp,
  AlertTriangle,
  Archive,
  X,
  CheckCircle,
  FileIcon,
  LogOut,
  Menu,
  Sparkles,
  ArrowRight,
} from "lucide-react"
// Import API :
import {
  facturaAPI,
  usePricingWorkflow,
  type InvoiceUploadResponse,
  type InvoiceStatus,
  type PricingInfo,
  type DashboardMetrics,
  type RecentInvoice as RecentInvoiceAPI,
  type AnalyticsData
} from "@/lib/api"
import { isAuthenticated, getStoredTenantId, logout } from "@/src/lib/api/endpoints/auth"
import { PlanBadge } from "@/components/plan-badge"
import { UpgradeModal } from "@/components/upgrade-modal"

import { InventoryPage } from "@/components/inventory-page"
import { InvoiceManagementPage } from "@/components/invoice-management-page"
import { SupplierManagementPage } from "@/components/supplier-management-page"
import { ReportsAnalyticsPage } from "@/components/reports-analytics-page"
import { ConfigurationPage } from "@/components/configuration-page"
import { RecommendationsPage } from "@/components/recommendations-page"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { LineChart, Line, BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from "recharts"

export default function FacturIADashboard() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState("Dashboard")
  const [dragActive, setDragActive] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({})
  //const [isUploading, setIsUploading] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadedInvoices, setUploadedInvoices] = useState<InvoiceUploadResponse[]>([])
  const [invoiceStatuses, setInvoiceStatuses] = useState<{[key: string]: InvoiceStatus}>({})
  const [processingError, setProcessingError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [selectedInvoice, setSelectedInvoice] = useState<any>(null)
  const [isInvoiceModalOpen, setIsInvoiceModalOpen] = useState(false)
  const [editedProducts, setEditedProducts] = useState<any[]>([])
  const [validationErrors, setValidationErrors] = useState<{ [key: string]: string }>({})
  const [markupPercentage, setMarkupPercentage] = useState(30)
  const [isConfirming, setIsConfirming] = useState(false)

  // Upgrade modal
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false)
  const [upgradeReason, setUpgradeReason] = useState<string | undefined>(undefined)
  const [currentPlan, setCurrentPlan] = useState<string>("freemium")

  // Mobile menu
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Tenant display name (from localStorage, populated on login)
  const [companyName, setCompanyName] = useState("")
  useEffect(() => {
    setCompanyName(localStorage.getItem("company_name") ?? "")
  }, [])

  // Dashboard data states
  const [dashboardMetrics, setDashboardMetrics] = useState<DashboardMetrics | null>(null)
  const [recentInvoicesData, setRecentInvoicesData] = useState<RecentInvoiceAPI[]>([])
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)
  const [isDashboardLoading, setIsDashboardLoading] = useState(false)
  const [timePeriod, setTimePeriod] = useState<"day" | "week" | "month">("week")

  // Extra dashboard data
  const [topSuppliersData, setTopSuppliersData] = useState<Array<{name: string; invoices: number; volume: number}>>([])
  const [stockAlertsData, setStockAlertsData] = useState<Array<{description: string; current_stock: number; min_stock: number; stock_status: string}>>([])
  const [recSummary, setRecSummary] = useState<{critical_restock: number; total_dead_stock: number; total_capital_tied: number} | null>(null)

  const sidebarItems = [
    { name: "Dashboard", icon: BarChart3, active: activeTab === "Dashboard" },
    { name: "Facturas", icon: FileText, active: activeTab === "Facturas" },
    { name: "Inventario", icon: Package, active: activeTab === "Inventario" },
    { name: "Proveedores", icon: Users, active: activeTab === "Proveedores" },
    { name: "Reportes", icon: BarChart3, active: activeTab === "Reportes" },
    { name: "Recomendaciones", icon: Sparkles, active: activeTab === "Recomendaciones" },
    { name: "Configuración", icon: Settings, active: activeTab === "Configuración" },
  ]

  // Guard: redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login")
      return
    }
    // Load current plan for UpgradeModal
    import("@/src/lib/api/endpoints/subscriptions").then(({ getCurrentSubscription }) => {
      getCurrentSubscription()
        .then((s) => setCurrentPlan(s.plan))
        .catch(() => {/* silently ignore */})
    })
  }, [router])

  // Load dashboard data when component mounts or activeTab changes to Dashboard
  useEffect(() => {
    if (activeTab === "Dashboard") {
      loadDashboardData()
    }
  }, [activeTab, timePeriod])

  const loadDashboardData = async () => {
    setIsDashboardLoading(true)
    try {
      const tenantId = getStoredTenantId() || "demo-company"
      facturaAPI.setTenantId(tenantId)

      // Load all dashboard data in parallel
      const [metrics, recentInvs, analytics] = await Promise.all([
        facturaAPI.getDashboardMetrics(),
        facturaAPI.getRecentInvoices(10),
        facturaAPI.getDashboardAnalytics(),
      ])

      setDashboardMetrics(metrics)
      setRecentInvoicesData(recentInvs)
      setAnalyticsData(analytics)
    } catch (error) {
      console.error("Error loading dashboard data:", error)
      // Keep mock data if API fails
    } finally {
      setIsDashboardLoading(false)
    }
  }

  const sliceByPeriod = <T,>(arr: T[]): T[] => {
    if (!arr?.length) return arr ?? []
    const n = { day: 1, week: 7, month: arr.length }[timePeriod]
    return arr.slice(-n)
  }

  const validateFile = (file: File): boolean => {
    const allowedTypes = ["application/pdf", "image/jpeg", "image/jpg", "image/png", "application/xml", "text/xml"]
    const maxSize = 10 * 1024 * 1024 // 10MB

    if (!allowedTypes.includes(file.type)) {
      alert(`Tipo de archivo no permitido: ${file.type}. Solo se permiten PDF, JPG, PNG y XML.`)
      return false
    }

    if (file.size > maxSize) {
      alert(`Archivo demasiado grande: ${(file.size / 1024 / 1024).toFixed(2)}MB. Máximo permitido: 10MB.`)
      return false
    }

    return true
  }

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files) return

    const validFiles: File[] = []
    Array.from(files).forEach((file) => {
      if (validateFile(file)) {
        validFiles.push(file)
      }
    })

    if (validFiles.length > 0) {
      setUploadedFiles((prev) => [...prev, ...validFiles])
    }
  }, [])

  const processFiles = async () => {
    if (uploadedFiles.length === 0) {
      alert("Por favor selecciona archivos primero")
      return
    }

    setIsUploading(true)
    setProcessingError(null)
    const newInvoices: InvoiceUploadResponse[] = []

    try {
      for (const file of uploadedFiles) {
        console.log(`🔄 Procesando: ${file.name}`)
      
        // Start progress
        setUploadProgress(prev => ({ ...prev, [file.name]: 0 }))
      
        const progressInterval = setInterval(() => {
          setUploadProgress(prev => {
            const current = prev[file.name] || 0
            if (current < 90) {
              return { ...prev, [file.name]: current + 15 }
            }
            return prev
          })
        }, 300)
      
        try {
          const isXml = file.type === 'application/xml' || file.type === 'text/xml'
                        || file.name.toLowerCase().endsWith('.xml')
          const isPdf = file.type === 'application/pdf'

          const response = isPdf || isXml
            ? await facturaAPI.uploadInvoice(file)
            : await facturaAPI.uploadPhoto(file)

          clearInterval(progressInterval)
          setUploadProgress(prev => ({ ...prev, [file.name]: 100 }))

          if (!response.success || !response.data) {
            throw new Error(response.error?.message || 'Error al subir archivo')
          }

          const invoice = response.data as InvoiceUploadResponse
          newInvoices.push(invoice)
          console.log(`✅ Subido: ${invoice.id}`)

          // Start status polling for this invoice
          pollInvoiceStatus(invoice.id)
        
        } catch (fileError: any) {
          clearInterval(progressInterval)
          setUploadProgress(prev => {
            const newProgress = { ...prev }
            delete newProgress[file.name]
            return newProgress
          })
          console.error(`❌ Error con archivo ${file.name}:`, fileError)

          // Límite de plan alcanzado → abrir modal de upgrade
          const msg: string = fileError?.message ?? String(fileError)
          if (msg.includes("límite") || msg.includes("402") || msg.includes("plan")) {
            setUpgradeReason(msg)
            setUpgradeModalOpen(true)
            break // No intentar los siguientes archivos
          }
          // Otro error → continúa con el siguiente archivo
        }
      }

      setUploadedInvoices(prev => [...prev, ...newInvoices])
   
      if (newInvoices.length > 0) {
        alert(`✅ ${newInvoices.length} facturas enviadas para procesamiento`)
        // Clear uploaded files after processing
        setUploadedFiles([])
      }
   
    } catch (error) {
      console.error('❌ Error procesando archivos:', error)
      setProcessingError(error instanceof Error ? error.message : 'Error desconocido')
      alert(`Error: ${error}`)
    } finally {
      setIsUploading(false)
    }
  }

  // Función de polling
  const pollInvoiceStatus = async (invoiceId: string) => {
    const maxAttempts = 30 // 1 minuto máximo
    let attempts = 0
  
    const poll = async () => {
      try {
        const response = await facturaAPI.getInvoiceStatus(invoiceId)
        const statusData = (response as any)?.data ?? response
        setInvoiceStatuses(prev => ({ ...prev, [invoiceId]: statusData }))

        if (statusData?.status === 'completed' || statusData?.status === 'failed' || attempts >= maxAttempts) {
          return
        }

        attempts++
        setTimeout(poll, 2000) // Poll every 2 seconds
      } catch (error) {
        console.error(`Error polling status for ${invoiceId}:`, error)
      }
    }
  
    poll()
  }

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setDragActive(false)

      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFiles(e.dataTransfer.files)
      }
    },
    [handleFiles],
  )

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files)
  }

  const removeFile = (fileName: string) => {
    setUploadedFiles((prev) => prev.filter((file) => file.name !== fileName))
    setUploadProgress((prev) => {
      const newProgress = { ...prev }
      delete newProgress[fileName]
      return newProgress
    })
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  const getPageTitle = () => {
    switch (activeTab) {
      case "Facturas":
        return "Gestión de Facturas"
      case "Inventario":
        return "Gestión de Inventario"
      case "Proveedores":
        return "Gestión de Proveedores"
      case "Reportes":
        return "Reportes y Análisis"
      default:
        return `Bienvenido, ${companyName}`
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      minimumFractionDigits: 0,
    }).format(amount)
  }

  const handleInvoiceClick = async (invoice: InvoiceUploadResponse, status: InvoiceStatus) => {
    try {
      if (status.status === "completed" || status.status === "pending") {
        console.log(`📄 Abriendo gestión de precios para: ${invoice.id}`)
  
        // 1) Trae pricing como siempre
        const pricingRaw = await facturaAPI.getPricingInfo(invoice.id)
        const pricingData = (pricingRaw as any)?.data ?? pricingRaw

        // 2) CALCULAR TOTAL CON FALLBACK
        let total = Number(pricingData?.total_cost ?? 0)

        // si parece un conteo de items o viene vacío, intenta con Textract
        if (!total || total < 1000) {
          try {
            const invoiceRaw = await facturaAPI.getInvoiceData(invoice.id)
            const invoiceData = (invoiceRaw as any)?.data ?? invoiceRaw
            if (invoiceData?.totals?.total) {
              total = Number(invoiceData.totals.total)
            }
          } catch {
            // no hacemos nada: nos quedamos con el total que haya
          }
        }
  
        // 3) Configurar el estado para el modal usando "total" (el confiable)
        setSelectedInvoice({
          id: invoice.id,
          supplier: pricingData.supplier_name,
          status: status.status.toUpperCase(),
          statusColor: status.status === 'completed' ? '#10B981' : '#F59E0B',
          total,                                    // <-- aquí ya no usamos pricingData.total_cost directo
          items: pricingData.total_items,
          products: pricingData.line_items.map(item => ({
            code: item.product_code,
            description: item.description,
            quantity: item.quantity,
            purchasePrice: item.unit_price,
            suggestedPrice: item.sale_price || calculatePrice(item.unit_price, markupPercentage).finalPrice,
            finalPrice: item.sale_price || calculatePrice(item.unit_price, markupPercentage).finalPrice
          }))
        })
  
        setEditedProducts(pricingData.line_items.map(item => ({
          id: item.id,
          line_item_id: item.line_item_id,
          code: item.product_code,
          description: item.description,
          quantity: item.quantity,
          purchasePrice: item.unit_price,
          suggestedPrice: item.sale_price || calculatePrice(item.unit_price, markupPercentage).finalPrice,
          finalPrice: item.sale_price || calculatePrice(item.unit_price, markupPercentage).finalPrice
        })))
  
        setIsInvoiceModalOpen(true)
        setValidationErrors({})
      } else {
        alert(`Estado ${status.status}: Esta factura aún no está lista para gestión de precios`)
      }
    } catch (error) {
      console.error('Error cargando datos de precios:', error)
      alert('Error al cargar los datos de la factura. Intenta de nuevo.')
    }
  }
  

  const handleProductChange = (index: number, field: string, value: string | number) => {
    const updatedProducts = [...editedProducts]
    updatedProducts[index] = { ...updatedProducts[index], [field]: value }

    // Validate final price
    if (field === "finalPrice") {
      const purchasePrice = updatedProducts[index].purchasePrice
      const finalPrice = Number(value)
      const errorKey = `${index}-finalPrice`

      if (finalPrice < purchasePrice) {
        setValidationErrors((prev) => ({
          ...prev,
          [errorKey]: `El precio final no puede ser menor al precio de compra (${formatCurrency(purchasePrice)})`,
        }))
      } else {
        setValidationErrors((prev) => {
          const newErrors = { ...prev }
          delete newErrors[errorKey]
          return newErrors
        })
      }
    }

    setEditedProducts(updatedProducts)
  }

  const applySuggestedPrice = (index: number) => {
    const pricingResult = calculatePrice(editedProducts[index].purchasePrice, markupPercentage)
    handleProductChange(index, "finalPrice", pricingResult.finalPrice)
    handleProductChange(index, "suggestedPrice", pricingResult.finalPrice)
  }

  const applyAllSuggestedPrices = () => {
    const updatedProducts = editedProducts.map((product) => ({
      ...product,
      finalPrice: product.suggestedPrice,
    }))
    setEditedProducts(updatedProducts)
    setValidationErrors({})
  }

  const applyMarkupToAll = () => {
    const updatedProducts = editedProducts.map((product) => {
      const pricingResult = calculatePrice(product.purchasePrice, markupPercentage)
      return {
        ...product,
        suggestedPrice: pricingResult.finalPrice,
        finalPrice: pricingResult.finalPrice,
      }
    })
    setEditedProducts(updatedProducts)
    setValidationErrors({})
  }

  const handleSaveChanges = async () => {
    // Check for validation errors
    const hasErrors = Object.keys(validationErrors).length > 0
    if (hasErrors) {
      alert("Por favor corrige los errores antes de guardar")
      return
    }

    if (!selectedInvoice) {
      alert("Error: No hay factura seleccionada")
      return
    }

    try {
      console.log("💾 Guardando cambios en la BD...")
    
      // Preparar datos para enviar a la API
      const lineItemsToUpdate = editedProducts.map((product, index) => ({
        line_item_id: product.line_item_id || product.id, // Usar ID real del producto
        sale_price: product.finalPrice
      }))

      console.log("📝 Datos a guardar:", lineItemsToUpdate)

      // Enviar a la API REAL — backend espera { line_items: [...] }
      const response = await facturaAPI.setPricing(selectedInvoice.id, { line_items: lineItemsToUpdate })

      console.log("✅ Respuesta de la API:", response)

      if (!response.success) {
        alert(`Error al guardar precios: ${response.error?.message ?? 'Error desconocido'}`)
        return
      }

      // Si todo salió bien
      alert(`✅ Cambios guardados exitosamente en la base de datos!\n\n${lineItemsToUpdate.length} productos actualizados`)
    
      setIsInvoiceModalOpen(false)
    
      // Opcional: Refrescar el estado de la factura
      // pollInvoiceStatus(selectedInvoice.id)
    
    } catch (error) {
      console.error("❌ Error guardando en BD:", error)
      alert(`Error al guardar: ${error}`)
    }
  }

  const handleConfirmAndSend = async () => {
    if (Object.keys(validationErrors).length > 0) {
      alert("Por favor corrige los errores antes de confirmar")
      return
    }
    if (!selectedInvoice) return

    setIsConfirming(true)
    try {
      // 1) Guardar precios — backend espera { line_items: [...] }
      const lineItemsToUpdate = editedProducts.map((product) => ({
        line_item_id: product.line_item_id || product.id,
        sale_price: product.finalPrice,
      }))
      const saveRes = await facturaAPI.setPricing(selectedInvoice.id, { line_items: lineItemsToUpdate })
      if (!saveRes.success) {
        throw new Error(saveRes.error?.message ?? 'Error al guardar precios')
      }

      // 2) Confirmar → actualiza inventario y envía a Alegra
      const confirmResult: any = await facturaAPI.confirmPricing(selectedInvoice.id)
      if (!confirmResult.success) {
        throw new Error(confirmResult.error?.message ?? 'Error al confirmar la factura')
      }
      const result = confirmResult?.data?.result ?? {}

      const alegraMsg = result?.alegra_bill
        ? `\n\nFactura creada en Alegra (ID: ${result.alegra_bill.id})`
        : "\n\n(Alegra no configurado — inventario actualizado localmente)"

      alert(
        `✅ Confirmado exitosamente\n` +
        `${result?.total_items ?? lineItemsToUpdate.length} productos actualizados en inventario` +
        alegraMsg
      )
      setIsInvoiceModalOpen(false)
      setEditedProducts([])
      setValidationErrors({})
    } catch (error) {
      console.error("Error al confirmar:", error)
      alert(`Error al confirmar: ${error}`)
    } finally {
      setIsConfirming(false)
    }
  }

  const handleCancelChanges = () => {
    setIsInvoiceModalOpen(false)
    setEditedProducts([])
    setValidationErrors({})
  }


  const handleMobileNav = (name: string) => {
    setActiveTab(name)
    setMobileMenuOpen(false)
  }

  return (
    <div className="flex h-screen h-dvh bg-gray-50 overflow-hidden">

      {/* ── Sidebar desktop: colapsa a iconos, expande al hover ── */}
      <div className="hidden md:flex group flex-col bg-slate-800 text-white flex-shrink-0
                      w-16 hover:w-64 transition-[width] duration-300 ease-in-out overflow-hidden">

        {/* Logo */}
        <div className="flex items-center gap-2 px-3 h-16 flex-shrink-0 border-b border-slate-700 overflow-hidden">
          {/* Ícono azul con FileText — idéntico al de la landing */}
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <FileText className="w-5 h-5 text-white" />
          </div>
          {/* Texto + bandera — aparecen al expandir */}
          <span className="text-xl font-bold text-white whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-200 delay-100">
            FacturIA
          </span>
          <div className="flex items-center gap-1 ml-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 delay-100">
            <div className="w-2 h-3 bg-yellow-400 rounded-sm"></div>
            <div className="w-2 h-3 bg-blue-500 rounded-sm"></div>
            <div className="w-2 h-3 bg-red-500 rounded-sm"></div>
          </div>
        </div>

        {/* Nav items */}
        <nav className="flex-1 px-2 py-3 space-y-1 overflow-hidden">
          {sidebarItems.map((item) => (
            <button
              key={item.name}
              onClick={() => setActiveTab(item.name)}
              className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg text-left transition-colors ${
                item.active ? "bg-blue-600 text-white" : "text-gray-300 hover:bg-slate-700 hover:text-white"
              }`}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              <span className="whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-200 delay-100 text-sm">
                {item.name}
              </span>
            </button>
          ))}
        </nav>

        {/* Plan + Logout */}
        <div className="px-2 pb-4 space-y-2 flex-shrink-0 border-t border-slate-700 pt-3">
          {/* Modo compacto (icono solo) */}
          <div className="block group-hover:hidden">
            <PlanBadge compact />
          </div>
          {/* Modo expandido */}
          <div className="hidden group-hover:block">
            <PlanBadge />
          </div>

          <button
            onClick={() => { logout(); router.replace("/login") }}
            className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-left text-gray-300 hover:bg-red-700 hover:text-white transition-colors"
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            <span className="whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-200 delay-100 text-sm">
              Cerrar Sesión
            </span>
          </button>
        </div>
      </div>

      {/* ── Overlay menú móvil ── */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* Fondo oscuro */}
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileMenuOpen(false)} />
          {/* Panel */}
          <div className="relative w-64 bg-slate-800 text-white flex flex-col h-full">
            <div className="flex items-center justify-between px-4 h-14 border-b border-slate-700">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                  <FileText className="w-5 h-5 text-white" />
                </div>
                <span className="text-lg font-bold text-white">FacturIA</span>
                <div className="flex items-center gap-1">
                  <div className="w-2 h-3 bg-yellow-400 rounded-sm"></div>
                  <div className="w-2 h-3 bg-blue-500 rounded-sm"></div>
                  <div className="w-2 h-3 bg-red-500 rounded-sm"></div>
                </div>
              </div>
              <button onClick={() => setMobileMenuOpen(false)} className="text-gray-400 hover:text-white p-1">
                <X className="w-5 h-5" />
              </button>
            </div>
            <nav className="flex-1 px-2 py-3 space-y-1 overflow-y-auto">
              {sidebarItems.map((item) => (
                <button
                  key={item.name}
                  onClick={() => handleMobileNav(item.name)}
                  className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg text-left transition-colors ${
                    item.active ? "bg-blue-600 text-white" : "text-gray-300 hover:bg-slate-700 hover:text-white"
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  <span className="text-sm">{item.name}</span>
                </button>
              ))}
            </nav>
            <div className="px-2 pb-4 space-y-2 border-t border-slate-700 pt-3">
              <PlanBadge />
              <button
                onClick={() => { logout(); router.replace("/login") }}
                className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-left text-gray-300 hover:bg-red-700 hover:text-white transition-colors"
              >
                <LogOut className="w-5 h-5" />
                <span className="text-sm">Cerrar Sesión</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-4 md:px-6 py-4 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Hamburger — solo móvil */}
              <button
                className="md:hidden p-1 text-gray-500 hover:text-gray-800"
                onClick={() => setMobileMenuOpen(true)}
              >
                <Menu className="w-6 h-6" />
              </button>
              <h2 className="text-xl font-semibold text-gray-800">{getPageTitle()}</h2>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="text-right hidden sm:block">
                  <p className="text-sm font-medium text-gray-900">{companyName}</p>
                  <p className="text-xs text-gray-500">Administrador</p>
                </div>
                <Avatar>
                  <AvatarFallback className="bg-blue-600 text-white">
                    {companyName.slice(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
              </div>
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <main className="flex-1 p-4 md:p-6 overflow-auto pb-20 md:pb-6">
          {activeTab === "Dashboard" && (
            <>
              {/* Metrics Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600 mb-1">Facturas este mes</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {isDashboardLoading ? "..." : dashboardMetrics?.total_invoices_month || 0}
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                        <FileText className="w-6 h-6 text-blue-600" />
                      </div>
                    </div>
                    <div className="flex items-center mt-2">
                      {!isDashboardLoading && dashboardMetrics && (
                        <>
                          {dashboardMetrics.month_over_month_invoices >= 0 ? (
                            <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                          ) : (
                            <svg className="w-4 h-4 text-red-500 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                            </svg>
                          )}
                          <span className={`text-sm ${dashboardMetrics.month_over_month_invoices >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {dashboardMetrics.month_over_month_invoices >= 0 ? '+' : ''}{dashboardMetrics.month_over_month_invoices}%
                          </span>
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600 mb-1">Total inventario</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {isDashboardLoading ? "..." : formatCurrency(dashboardMetrics?.total_inventory_value || 0)}
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                        <Archive className="w-6 h-6 text-green-600" />
                      </div>
                    </div>
                    <div className="flex items-center mt-2">
                      <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                      <span className="text-sm text-green-600">
                        +{dashboardMetrics?.month_over_month_inventory || 0}%
                      </span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600 mb-1">Alertas pendientes</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {isDashboardLoading ? "..." : dashboardMetrics?.pending_alerts || 0}
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                        <AlertTriangle className="w-6 h-6 text-orange-600" />
                      </div>
                    </div>
                    <div className="flex items-center mt-2">
                      <span className="text-sm text-gray-500">
                        {dashboardMetrics?.total_suppliers || 0} proveedores
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Upload Section */}
                <div className="lg:col-span-2">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Upload className="w-5 h-5" />
                        Subir Nueva Factura
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div
                        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                          dragActive
                            ? "border-blue-500 bg-blue-50"
                            : "border-blue-300 hover:border-blue-400 hover:bg-blue-50"
                        }`}
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
                      >
                        <Upload
                          className={`w-12 h-12 mx-auto mb-4 ${dragActive ? "text-blue-500" : "text-gray-400"}`}
                        />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">
                          {dragActive ? "Suelta los archivos aquí" : "Arrastra tu factura aquí"}
                        </h3>
                        <p className="text-sm text-gray-500 mb-6">o haz clic para seleccionar (PDF, JPG, PNG, XML)</p>
                        <div className="flex gap-3 justify-center">
                          <Button
                            type="button"
                            className="bg-blue-600 hover:bg-blue-700"
                            onClick={(e) => {
                              e.stopPropagation()
                              fileInputRef.current?.click()
                            }}
                          >
                            <Upload className="w-4 h-4 mr-2" />
                            Seleccionar Archivos
                          </Button>
                          <Button
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation()
                              // Camera functionality would go here
                              alert("Funcionalidad de cámara próximamente")
                            }}
                          >
                            <Camera className="w-4 h-4 mr-2" />
                            Tomar Foto con Cámara
                          </Button>
                        </div>

                        <input
                          ref={fileInputRef}
                          type="file"
                          multiple
                          accept=".pdf,.jpg,.jpeg,.png,.xml"
                          onChange={handleFileInput}
                          className="hidden"
                        />
                      </div>

                      {/* Uploaded Files List */}
                      {uploadedFiles.length > 0 && (
                        <div className="mt-6">
                          <h4 className="text-sm font-medium text-gray-900 mb-3">
                            Archivos subidos ({uploadedFiles.length})
                          </h4>
                          <div className="space-y-3">
                            {uploadedFiles.map((file, index) => (
                              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                <div className="flex items-center gap-3">
                                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                                    <FileIcon className="w-5 h-5 text-blue-600" />
                                  </div>
                                  <div>
                                    <p className="text-sm font-medium text-gray-900">{file.name}</p>
                                    <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                                  </div>
                                </div>

                                <div className="flex items-center gap-2">
                                  {uploadProgress[file.name] !== undefined && (
                                    <div className="flex items-center gap-2">
                                      {uploadProgress[file.name] === 100 ? (
                                        <CheckCircle className="w-5 h-5 text-green-500" />
                                      ) : (
                                        <div className="w-16 bg-gray-200 rounded-full h-2">
                                          <div
                                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                            style={{ width: `${uploadProgress[file.name]}%` }}
                                          ></div>
                                        </div>
                                      )}
                                      <span className="text-xs text-gray-500">{uploadProgress[file.name]}%</span>
                                    </div>
                                  )}

                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => removeFile(file.name)}
                                    className="text-gray-400 hover:text-red-500"
                                  >
                                    <X className="w-4 h-4" />
                                  </Button>
                                </div>
                              </div>
                            ))}
                          </div>

                          {isUploading && (
                            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                              <div className="flex items-center gap-2">
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                                <span className="text-sm text-blue-700">Procesando archivos...</span>
                              </div>
                            </div>
                          )}

                          {uploadedFiles.length > 0 && !isUploading && (
                            <div className="mt-4 flex gap-2">
                              <Button className="bg-green-600 hover:bg-green-700"
                                      onClick={processFiles}
                              >
                                <CheckCircle className="w-4 h-4 mr-2" />
                                Procesar Facturas ({uploadedFiles.length})
                              </Button>
                              <Button
                                variant="outline"
                                onClick={() => {
                                  setUploadedFiles([])
                                  setUploadProgress({})
                                  setUploadedInvoices([])
                                  setInvoiceStatuses({})
                                  setProcessingError(null)
                                }}
                              >
                                Limpiar Todo
                              </Button>
                            </div>
                          )}
                        </div>
                      )}
                      {/* Error display */}
                      {processingError && (
                        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                          <p className="text-sm text-red-600">❌ {processingError}</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Top Products Section */}
                </div>

                {/* Processing Status */}
                {uploadedInvoices.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <FileText className="w-5 h-5" />
                        Estado del Procesamiento ({uploadedInvoices.length})
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {uploadedInvoices.map((invoice, idx) => {
                          const status = invoiceStatuses[invoice.id]
                          return (
                            <div
                              key={invoice.id ?? idx}
                              className={`p-4 bg-gray-50 rounded-lg transition-all duration-200 ${
                                status?.status === 'completed' || status?.status === 'PENDING'
                                  ? "cursor-pointer hover:bg-blue-50 hover:shadow-md border border-green-200" 
                                  : "cursor-default"
                              }`}
                              onClick={() => {
                                const status = invoiceStatuses[invoice.id]
                                if (status){
                                  handleInvoiceClick(invoice, status)
                                }
                              }}
                            >
                              <div className="flex items-center justify-between mb-2">
                                <div>
                                  <p className="font-semibold text-gray-900">{invoice.original_filename}</p>
                                  <p className="text-sm text-gray-600">ID: {invoice.id?.substring(0, 12) ?? '—'}...</p>
                                </div>
                                <div className="flex items-center gap-2">
                                  {status ? (
                                    <>
                                      <Badge
                                        className="text-white text-xs px-3 py-1 font-medium"
                                        style={{ 
                                          backgroundColor: status.status === 'completed' ? '#10B981' :
                                                          status.status === 'processing' ? '#F59E0B' :
                                                          status.status === 'failed' ? '#EF4444' : '#6B7280'
                                        }}
                                      >
                                        {status.status === 'completed' ? 'COMPLETADO' :
                                         status.status === 'processing' ? 'PROCESANDO' :
                                         status.status === 'failed' ? 'ERROR' : (status.status?.toUpperCase() ?? 'PENDIENTE')}
                                      </Badge>
                                      {status.status === 'processing' && (
                                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                                      )}
                                      {status.status === 'completed' && (
                                        <CheckCircle className="w-4 h-4 text-green-500" />
                                      )}
                                    </>
                                  ) : (
                                    <Badge className="text-white text-xs px-3 py-1 bg-gray-500">
                                      INICIANDO...
                                    </Badge>
                                  )}
                                </div>
                              </div>
                              <div className="flex items-center justify-between text-sm text-gray-500">
                                <span>{new Date(invoice.upload_timestamp).toLocaleString('es-CO')}</span>
                                {(status?.status === 'completed' || status?.status === 'PENDING') && (
                                  <span className="text-blue-600 font-medium">🎉 ¡Listo para precios!</span>
                                )}
                                {status?.error_message && (
                                  <span className="text-red-600 text-xs">Error: {status.error_message}</span>
                                )}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>

              {/* Timeline Dashboard */}
              <div className="mt-8">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-xl font-semibold text-gray-900">Panel de Análisis Temporal</h3>
                  <Select value={timePeriod} onValueChange={(v) => setTimePeriod(v as "day" | "week" | "month")}>
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="day">Día</SelectItem>
                      <SelectItem value="week">Semana</SelectItem>
                      <SelectItem value="month">Mes</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Purchase Volume Chart */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <BarChart3 className="w-5 h-5" />
                        Volumen de Compras
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={sliceByPeriod(analyticsData?.purchase_volume ?? [])}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                            <YAxis tick={{ fontSize: 12 }} />
                            <Tooltip
                              formatter={(value) => [`$${Number(value).toLocaleString()}`, "Volumen"]}
                              labelFormatter={(label) => `Período: ${label}`}
                            />
                            <Line
                              type="monotone"
                              dataKey="volume"
                              stroke="#4F63FF"
                              strokeWidth={3}
                              dot={{ fill: "#4F63FF", strokeWidth: 2, r: 4 }}
                              activeDot={{ r: 6, stroke: "#4F63FF", strokeWidth: 2 }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="flex items-center mt-4">
                        <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                        <span className="text-sm text-green-600">+18% vs período anterior</span>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Margin Trend */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <TrendingUp className="w-5 h-5" />
                        Tendencia de Margen
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={sliceByPeriod(analyticsData?.margin_trend ?? [])}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                            <YAxis
                              tick={{ fontSize: 12 }}
                              domain={["dataMin - 2", "dataMax + 2"]}
                              tickFormatter={(value) => `${value}%`}
                            />
                            <Tooltip
                              formatter={(value) => [`${value}%`, "Margen"]}
                              labelFormatter={(label) => `Mes: ${label}`}
                            />
                            <Line
                              type="monotone"
                              dataKey="margin"
                              stroke="#10B981"
                              strokeWidth={3}
                              dot={{ fill: "#10B981", strokeWidth: 2, r: 5 }}
                              activeDot={{ r: 7, stroke: "#10B981", strokeWidth: 2 }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="flex items-center mt-4">
                        <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                        <span className="text-sm text-green-600">Margen promedio: 42.8%</span>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Previous Period Comparison */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <BarChart3 className="w-5 h-5" />
                        Este Mes vs. Anterior
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div>
                            <p className="text-sm text-gray-600">Facturas Procesadas</p>
                            <p className="text-2xl font-bold text-gray-900">
                              {analyticsData?.comparison_metrics?.invoices_processed || 0}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            {(analyticsData?.comparison_metrics?.invoices_change || 0) >= 0 ? (
                              <TrendingUp className="w-4 h-4 text-green-500" />
                            ) : (
                              <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                              </svg>
                            )}
                            <span className={`text-sm font-medium ${(analyticsData?.comparison_metrics?.invoices_change || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {(analyticsData?.comparison_metrics?.invoices_change || 0) >= 0 ? '+' : ''}
                              {analyticsData?.comparison_metrics?.invoices_change || 0}%
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div>
                            <p className="text-sm text-gray-600">Ingresos Totales</p>
                            <p className="text-2xl font-bold text-gray-900">
                              ${analyticsData?.comparison_metrics?.total_revenue?.toLocaleString() || 0}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            {(analyticsData?.comparison_metrics?.revenue_change || 0) >= 0 ? (
                              <TrendingUp className="w-4 h-4 text-green-500" />
                            ) : (
                              <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                              </svg>
                            )}
                            <span className={`text-sm font-medium ${(analyticsData?.comparison_metrics?.revenue_change || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {(analyticsData?.comparison_metrics?.revenue_change || 0) >= 0 ? '+' : ''}
                              {analyticsData?.comparison_metrics?.revenue_change || 0}%
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div>
                            <p className="text-sm text-gray-600">Productos Nuevos</p>
                            <p className="text-2xl font-bold text-gray-900">
                              {analyticsData?.comparison_metrics?.new_products || 0}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            {(analyticsData?.comparison_metrics?.products_change || 0) >= 0 ? (
                              <TrendingUp className="w-4 h-4 text-green-500" />
                            ) : (
                              <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                              </svg>
                            )}
                            <span className={`text-sm font-medium ${(analyticsData?.comparison_metrics?.products_change || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {(analyticsData?.comparison_metrics?.products_change || 0) >= 0 ? '+' : ''}
                              {analyticsData?.comparison_metrics?.products_change || 0}%
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div>
                            <p className="text-sm text-gray-600">Tiempo Promedio</p>
                            <p className="text-2xl font-bold text-gray-900">
                              {analyticsData?.comparison_metrics?.avg_processing_time_minutes || 0} min
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            {(analyticsData?.comparison_metrics?.time_change || 0) >= 0 ? (
                              <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                              </svg>
                            ) : (
                              <TrendingUp className="w-4 h-4 text-green-500" />
                            )}
                            <span className={`text-sm font-medium ${(analyticsData?.comparison_metrics?.time_change || 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                              {analyticsData?.comparison_metrics?.time_change || 0}%
                            </span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Inventory Projection */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Package className="w-5 h-5" />
                        Proyección de Inventario
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={sliceByPeriod(analyticsData?.inventory_projection ?? [])}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="product" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" height={80} />
                            <YAxis tick={{ fontSize: 12 }} />
                            <Tooltip
                              formatter={(value, name) => [
                                `${value} unidades`,
                                name === "current" ? "Stock Actual" : "Proyección 30 días",
                              ]}
                            />
                            <Bar dataKey="current" fill="#4F63FF" name="current" />
                            <Bar dataKey="projected" fill="#10B981" name="projected" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="flex items-center justify-between mt-4">
                        <div className="flex items-center gap-4">
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-blue-600 rounded-full"></div>
                            <span className="text-sm text-gray-600">Stock Actual</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-green-600 rounded-full"></div>
                            <span className="text-sm text-gray-600">Proyección 30 días</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <AlertTriangle className="w-4 h-4 text-orange-500" />
                          <span className="text-sm text-orange-600">3 productos en riesgo</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </>
          )}

          {activeTab === "Facturas" && <InvoiceManagementPage 
            uploadedInvoices={uploadedInvoices} 
            invoiceStatuses={invoiceStatuses} 
            setActiveTab={setActiveTab}
          />}
          {activeTab === "Inventario" && <InventoryPage />}
          {activeTab === "Proveedores" && <SupplierManagementPage />}
          {activeTab === "Reportes" && <ReportsAnalyticsPage />}
          {activeTab === "Recomendaciones" && <RecommendationsPage />}
          {activeTab === "Configuración" && <ConfigurationPage />}

          {/* Invoice Edit Modal */}
          {isInvoiceModalOpen && selectedInvoice && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
              <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] overflow-hidden">
                {/* Modal Header */}
                <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-xl font-bold text-gray-900">{selectedInvoice.id}</h2>
                      <p className="text-sm text-gray-600">{selectedInvoice.supplier}</p>
                    </div>
                    <button
                      onClick={handleCancelChanges}
                      className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      <X className="w-6 h-6" />
                    </button>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                    <div>
                      <p className="text-xs text-gray-500">Total</p>
                      <p className="font-semibold text-gray-900">{formatCurrency(selectedInvoice.total)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Productos</p>
                      <p className="font-semibold text-gray-900">{selectedInvoice.items}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Fecha</p>
                      <p className="font-semibold text-gray-900">{selectedInvoice.date}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Estado</p>
                      <Badge
                        className="text-white text-xs px-2 py-1"
                        style={{ backgroundColor: selectedInvoice.statusColor }}
                      >
                        {selectedInvoice.status}
                      </Badge>
                    </div>
                  </div>
                </div>

                {/* Modal Body */}
                <div className="p-6 overflow-y-auto max-h-[60vh]">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">Productos Extraídos</h3>
                    {/* Configuración de Markup */}
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2">
                        <Calculator className="w-4 h-4 text-gray-600" />
                        <label className="text-sm font-medium">Markup:</label>
                        <Input
                          type="number"
                          value={markupPercentage}
                          onChange={(e) => setMarkupPercentage(Number(e.target.value) || 30)}
                          className="w-16 text-sm"
                          min="0"
                          max="200"
                        />
                        <span className="text-sm text-gray-500">%</span>
                      </div>
                      <Button onClick={applyMarkupToAll} className="bg-blue-600 hover:bg-blue-700 text-sm">
                      Aplicar a Todos
                      </Button>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse border border-gray-200">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="border border-gray-200 px-3 py-2 text-left text-sm font-semibold text-gray-900">
                            Código
                          </th>
                          <th className="border border-gray-200 px-3 py-2 text-left text-sm font-semibold text-gray-900">
                            Descripción
                          </th>
                          <th className="border border-gray-200 px-3 py-2 text-center text-sm font-semibold text-gray-900">
                            Cantidad
                          </th>
                          <th className="border border-gray-200 px-3 py-2 text-right text-sm font-semibold text-gray-900">
                            Precio Compra
                          </th>
                          <th className="border border-gray-200 px-3 py-2 text-right text-sm font-semibold text-gray-900">
                            Precio Sugerido
                          </th>
                          <th className="border border-gray-200 px-3 py-2 text-right text-sm font-semibold text-gray-900">
                            Precio Final
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {editedProducts.map((product, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            <td className="border border-gray-200 px-3 py-2">
                              <Input
                                value={product.code}
                                onChange={(e) => handleProductChange(index, "code", e.target.value)}
                                className="w-full text-sm"
                              />
                            </td>
                            <td className="border border-gray-200 px-3 py-2">
                              <Input
                                value={product.description}
                                onChange={(e) => handleProductChange(index, "description", e.target.value)}
                                className="w-full text-sm"
                              />
                            </td>
                            <td className="border border-gray-200 px-3 py-2">
                              <Input
                                type="number"
                                value={product.quantity}
                                onChange={(e) =>
                                  handleProductChange(index, "quantity", Number.parseInt(e.target.value) || 0)
                                }
                                className="w-full text-sm text-center"
                                min="1"
                              />
                            </td>
                            <td className="border border-gray-200 px-3 py-2 text-right">
                              <span className="text-sm font-medium text-gray-900">
                                {formatCurrency(product.purchasePrice)}
                              </span>
                            </td>
                            <td className="border border-gray-200 px-3 py-2">
                              <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-gray-900">
                                  {formatCurrency(product.suggestedPrice)}
                                </span>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => applySuggestedPrice(index)}
                                  className="ml-2 text-xs px-2 py-1 h-6"
                                >
                                  Aplicar
                                </Button>
                              </div>
                            </td>
                            <td className="border border-gray-200 px-3 py-2">
                              <div>
                                <Input
                                  type="number"
                                  value={product.finalPrice}
                                  onChange={(e) =>
                                    handleProductChange(index, "finalPrice", Number.parseInt(e.target.value) || 0)
                                  }
                                  className={`w-full text-sm text-right ${
                                    validationErrors[`${index}-finalPrice`] ? "border-red-500" : ""
                                  }`}
                                  min={product.purchasePrice}
                                />
                                {validationErrors[`${index}-finalPrice`] && (
                                  <p className="text-xs text-red-500 mt-1">{validationErrors[`${index}-finalPrice`]}</p>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Modal Footer */}
                <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
                  <div className="flex flex-col sm:flex-row gap-3 justify-end">
                    <Button variant="outline" onClick={handleCancelChanges} className="bg-transparent" disabled={isConfirming}>
                      Cancelar
                    </Button>
                    <Button
                      onClick={handleSaveChanges}
                      className="bg-gray-600 hover:bg-gray-700"
                      disabled={Object.keys(validationErrors).length > 0 || isConfirming}
                    >
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Guardar Precios
                    </Button>
                    <Button
                      onClick={handleConfirmAndSend}
                      className="bg-green-600 hover:bg-green-700"
                      disabled={Object.keys(validationErrors).length > 0 || isConfirming}
                    >
                      <CheckCircle className="w-4 h-4 mr-2" />
                      {isConfirming ? "Confirmando..." : "Confirmar y Enviar a Alegra"}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* ── Bottom nav móvil ── */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-slate-800 border-t border-slate-700 flex justify-around py-2 z-40">
        {sidebarItems.map((item) => (
          <button
            key={item.name}
            onClick={() => setActiveTab(item.name)}
            className={`flex flex-col items-center gap-0.5 px-2 py-1 rounded-lg transition-colors ${
              item.active ? "text-blue-400" : "text-gray-400 hover:text-white"
            }`}
          >
            <item.icon className="w-5 h-5" />
            <span className="text-[10px] leading-tight">{item.name.slice(0, 6)}</span>
          </button>
        ))}
      </nav>

      {/* Upgrade modal — shown when invoice limit is reached */}
      <UpgradeModal
        open={upgradeModalOpen}
        onClose={() => setUpgradeModalOpen(false)}
        currentPlan={currentPlan}
        reason={upgradeReason}
      />
    </div>
  )
}
