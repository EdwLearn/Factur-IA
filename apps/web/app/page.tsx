"use client"

import type React from "react"

import { useState, useCallback, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Search,
  FileText,
  Package,
  Users,
  BarChart3,
  Settings,
  Upload,
  Camera,
  TrendingUp,
  AlertTriangle,
  Archive,
  X,
  CheckCircle,
  FileIcon,
} from "lucide-react"
import { InventoryPage } from "@/components/inventory-page"
import { InvoiceManagementPage } from "@/components/invoice-management-page"
import { SupplierManagementPage } from "@/components/supplier-management-page"
import { ReportsAnalyticsPage } from "@/components/reports-analytics-page"
import { ConfigurationPage } from "@/components/configuration-page"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

export default function FacturIADashboard() {
  const [activeTab, setActiveTab] = useState("Dashboard")
  const [dragActive, setDragActive] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({})
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [selectedInvoice, setSelectedInvoice] = useState<any>(null)
  const [isInvoiceModalOpen, setIsInvoiceModalOpen] = useState(false)
  const [editedProducts, setEditedProducts] = useState<any[]>([])
  const [validationErrors, setValidationErrors] = useState<{ [key: string]: string }>({})

  const sidebarItems = [
    { name: "Dashboard", icon: BarChart3, active: activeTab === "Dashboard" },
    { name: "Facturas", icon: FileText, active: activeTab === "Facturas" },
    { name: "Inventario", icon: Package, active: activeTab === "Inventario" },
    { name: "Proveedores", icon: Users, active: activeTab === "Proveedores" },
    { name: "Reportes", icon: BarChart3, active: activeTab === "Reportes" },
    { name: "Configuración", icon: Settings, active: activeTab === "Configuración" },
  ]

  const recentInvoices = [
    {
      id: "FAC-2024-001",
      supplier: "Textiles Medellín S.A.S",
      status: "PENDING",
      statusColor: "#F59E0B",
      elapsedTime: "hace 15 min",
      total: 2450000,
      items: 8,
      date: "2024-01-15",
      products: [
        {
          code: "TEX001",
          description: "Camiseta Polo Básica Blanca Talla M",
          quantity: 25,
          purchasePrice: 25000,
          suggestedPrice: 45000,
          finalPrice: 45000,
        },
        {
          code: "TEX002",
          description: "Short Deportivo Negro Talla L",
          quantity: 15,
          purchasePrice: 35000,
          suggestedPrice: 62000,
          finalPrice: 62000,
        },
        {
          code: "TEX003",
          description: "Vestido Casual Azul Talla S",
          quantity: 12,
          purchasePrice: 55000,
          suggestedPrice: 98000,
          finalPrice: 98000,
        },
        {
          code: "TEX004",
          description: "Camisa Formal Blanca Talla M",
          quantity: 20,
          purchasePrice: 42000,
          suggestedPrice: 75000,
          finalPrice: 75000,
        },
      ],
    },
    {
      id: "FAC-2024-002",
      supplier: "Confecciones Antioquia Ltda",
      status: "PROCESSING",
      statusColor: "#3B82F6",
      elapsedTime: "hace 2 horas",
      total: 1850000,
      items: 6,
      date: "2024-01-14",
      products: [],
    },
    {
      id: "FAC-2024-003",
      supplier: "Moda Femenina S.A.S",
      status: "COMPLETED",
      statusColor: "#10B981",
      elapsedTime: "hace 1 día",
      total: 890000,
      items: 4,
      date: "2024-01-13",
      products: [],
    },
    {
      id: "FAC-2024-004",
      supplier: "Distribuidora Bogotá",
      status: "ERROR",
      statusColor: "#EF4444",
      elapsedTime: "hace 3 horas",
      total: 0,
      items: 0,
      date: "2024-01-12",
      products: [],
    },
  ]

  const purchaseVolumeData = [
    { period: "Sem 1", volume: 125000 },
    { period: "Sem 2", volume: 142000 },
    { period: "Sem 3", volume: 138000 },
    { period: "Sem 4", volume: 165000 },
    { period: "Sem 5", volume: 158000 },
    { period: "Sem 6", volume: 195000 },
    { period: "Sem 7", volume: 182000 },
    { period: "Sem 8", volume: 201000 },
  ]

  const marginTrendData = [
    { month: "Ene", margin: 38.5 },
    { month: "Feb", margin: 41.2 },
    { month: "Mar", margin: 39.8 },
    { month: "Abr", margin: 43.1 },
    { month: "May", margin: 44.7 },
    { month: "Jun", margin: 42.3 },
    { month: "Jul", margin: 45.2 },
    { month: "Ago", margin: 43.8 },
  ]

  const inventoryProjectionData = [
    { product: "Camisetas", current: 45, projected: 28 },
    { product: "Jeans", current: 32, projected: 15 },
    { product: "Zapatos", current: 8, projected: 2 },
    { product: "Accesorios", current: 28, projected: 35 },
    { product: "Blusas", current: 5, projected: 1 },
  ]

  const validateFile = (file: File): boolean => {
    const allowedTypes = ["application/pdf", "image/jpeg", "image/jpg", "image/png"]
    const maxSize = 10 * 1024 * 1024 // 10MB

    if (!allowedTypes.includes(file.type)) {
      alert(`Tipo de archivo no permitido: ${file.type}. Solo se permiten PDF, JPG y PNG.`)
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
      simulateUpload(validFiles)
    }
  }, [])

  const simulateUpload = (files: File[]) => {
    setIsUploading(true)

    files.forEach((file) => {
      let progress = 0
      const interval = setInterval(() => {
        progress += Math.random() * 30
        if (progress >= 100) {
          progress = 100
          clearInterval(interval)
          setUploadProgress((prev) => ({ ...prev, [file.name]: 100 }))

          // Check if all files are uploaded
          setTimeout(() => {
            setIsUploading(false)
          }, 500)
        } else {
          setUploadProgress((prev) => ({ ...prev, [file.name]: Math.round(progress) }))
        }
      }, 200)
    })
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
        return "Bienvenido, Almacén Medellín JA"
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      minimumFractionDigits: 0,
    }).format(amount)
  }

  const handleInvoiceClick = (invoice: any) => {
    if (invoice.status === "PENDING") {
      setSelectedInvoice(invoice)
      setEditedProducts([...invoice.products])
      setIsInvoiceModalOpen(true)
      setValidationErrors({})
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
    handleProductChange(index, "finalPrice", editedProducts[index].suggestedPrice)
  }

  const applyAllSuggestedPrices = () => {
    const updatedProducts = editedProducts.map((product) => ({
      ...product,
      finalPrice: product.suggestedPrice,
    }))
    setEditedProducts(updatedProducts)
    setValidationErrors({})
  }

  const handleSaveChanges = () => {
    // Check for validation errors
    const hasErrors = Object.keys(validationErrors).length > 0
    if (hasErrors) {
      alert("Por favor corrige los errores antes de guardar")
      return
    }

    // Here you would typically save to backend
    alert("Cambios guardados exitosamente")
    setIsInvoiceModalOpen(false)
  }

  const handleCancelChanges = () => {
    setIsInvoiceModalOpen(false)
    setEditedProducts([])
    setValidationErrors({})
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-slate-800 text-white flex flex-col">
        <div className="p-6">
          <h1 className="text-xl font-bold text-blue-400">FacturIA</h1>
        </div>

        <nav className="flex-1 px-4">
          {sidebarItems.map((item) => (
            <button
              key={item.name}
              onClick={() => setActiveTab(item.name)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-2 text-left transition-colors ${
                item.active ? "bg-blue-600 text-white" : "text-gray-300 hover:bg-slate-700 hover:text-white"
              }`}
            >
              <item.icon className="w-5 h-5" />
              {item.name}
            </button>
          ))}
        </nav>

        <div className="p-4">
          <Button variant="outline" className="w-full text-white border-gray-600 hover:bg-slate-700 bg-transparent">
            Cerrar Sesión
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-800">{getPageTitle()}</h2>

            <div className="flex items-center gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input placeholder="Buscar facturas, productos..." className="pl-10 w-80" />
              </div>

              <div className="flex items-center gap-2">
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">Juan Pérez</p>
                  <p className="text-xs text-gray-500">Administrador</p>
                </div>
                <Avatar>
                  <AvatarFallback className="bg-blue-600 text-white">JA</AvatarFallback>
                </Avatar>
              </div>
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <main className="flex-1 p-6 overflow-auto">
          {activeTab === "Dashboard" && (
            <>
              {/* Metrics Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600 mb-1">Total este mes</p>
                        <p className="text-2xl font-bold text-gray-900">$6,159</p>
                      </div>
                      <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                        <FileText className="w-6 h-6 text-blue-600" />
                      </div>
                    </div>
                    <div className="flex items-center mt-2">
                      <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                      <span className="text-sm text-green-600">+10%</span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600 mb-1">Total inventario</p>
                        <p className="text-2xl font-bold text-gray-900">$3,159</p>
                      </div>
                      <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                        <Archive className="w-6 h-6 text-green-600" />
                      </div>
                    </div>
                    <div className="flex items-center mt-2">
                      <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                      <span className="text-sm text-green-600">+8%</span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600 mb-1">Alertas pendientes</p>
                        <p className="text-2xl font-bold text-gray-900">$6,159</p>
                      </div>
                      <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                        <AlertTriangle className="w-6 h-6 text-orange-600" />
                      </div>
                    </div>
                    <div className="flex items-center mt-2">
                      <span className="text-sm text-red-600">-2%</span>
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
                        <p className="text-sm text-gray-500 mb-6">o haz clic para seleccionar (PDF, JPG, PNG)</p>
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
                          accept=".pdf,.jpg,.jpeg,.png"
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
                              <Button className="bg-green-600 hover:bg-green-700">
                                <CheckCircle className="w-4 h-4 mr-2" />
                                Procesar Facturas ({uploadedFiles.length})
                              </Button>
                              <Button
                                variant="outline"
                                onClick={() => {
                                  setUploadedFiles([])
                                  setUploadProgress({})
                                }}
                              >
                                Limpiar Todo
                              </Button>
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Top Products Section */}
                </div>

                {/* Recent Invoices */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="w-5 h-5" />
                      Facturas
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {recentInvoices.map((invoice, index) => (
                        <div
                          key={index}
                          className={`p-4 bg-gray-50 rounded-lg transition-all duration-200 ${
                            invoice.status === "PENDING"
                              ? "cursor-pointer hover:bg-blue-50 hover:shadow-md"
                              : "cursor-default"
                          }`}
                          onClick={() => handleInvoiceClick(invoice)}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div>
                              <p className="font-semibold text-gray-900">{invoice.id}</p>
                              <p className="text-sm text-gray-600">{invoice.supplier}</p>
                            </div>
                            <Badge
                              className="text-white text-xs px-3 py-1 font-medium"
                              style={{ backgroundColor: invoice.statusColor }}
                            >
                              {invoice.status}
                            </Badge>
                          </div>
                          <div className="flex items-center justify-between text-sm text-gray-500">
                            <span>{invoice.elapsedTime}</span>
                            {invoice.status === "PENDING" && (
                              <span className="text-blue-600 font-medium">Click para editar</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Timeline Dashboard */}
              <div className="mt-8">
                <h3 className="text-xl font-semibold text-gray-900 mb-6">Panel de Análisis Temporal</h3>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Purchase Volume Chart */}
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-2">
                          <BarChart3 className="w-5 h-5" />
                          Volumen de Compras
                        </CardTitle>
                        <Select defaultValue="week">
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
                    </CardHeader>
                    <CardContent>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={purchaseVolumeData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                            <YAxis tick={{ fontSize: 12 }} />
                            <Tooltip
                              formatter={(value) => [`$${value.toLocaleString()}`, "Volumen"]}
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
                          <LineChart data={marginTrendData}>
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
                            <p className="text-2xl font-bold text-gray-900">85</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-green-500" />
                            <span className="text-sm font-medium text-green-600">+12%</span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div>
                            <p className="text-sm text-gray-600">Ingresos Totales</p>
                            <p className="text-2xl font-bold text-gray-900">$8,450</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-green-500" />
                            <span className="text-sm font-medium text-green-600">+8%</span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div>
                            <p className="text-sm text-gray-600">Productos Nuevos</p>
                            <p className="text-2xl font-bold text-gray-900">23</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M19 14l-7 7m0 0l-7-7m7 7V3"
                              />
                            </svg>
                            <span className="text-sm font-medium text-red-600">-5%</span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div>
                            <p className="text-sm text-gray-600">Tiempo Promedio</p>
                            <p className="text-2xl font-bold text-gray-900">2.1 min</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M19 14l-7 7m0 0l-7-7m7 7V3"
                              />
                            </svg>
                            <span className="text-sm font-medium text-red-600">-15%</span>
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
                          <BarChart data={inventoryProjectionData}>
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

          {activeTab === "Facturas" && <InvoiceManagementPage />}
          {activeTab === "Inventario" && <InventoryPage />}
          {activeTab === "Proveedores" && <SupplierManagementPage />}
          {activeTab === "Reportes" && <ReportsAnalyticsPage />}
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
                    <Button onClick={applyAllSuggestedPrices} className="bg-blue-600 hover:bg-blue-700 text-sm">
                      Aplicar Precios Sugeridos a Todos
                    </Button>
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
                    <Button variant="outline" onClick={handleCancelChanges} className="bg-transparent">
                      Cancelar
                    </Button>
                    <Button
                      onClick={handleSaveChanges}
                      className="bg-green-600 hover:bg-green-700"
                      disabled={Object.keys(validationErrors).length > 0}
                    >
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Guardar Cambios
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
