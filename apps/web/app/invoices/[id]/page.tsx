"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { facturaAPI } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowLeft, CheckCircle, AlertCircle, Send } from "lucide-react"

// ── Local types matching the actual backend snake_case responses ──────────────

interface InvoiceLineItemShape {
  description: string
  quantity: number
  unit_price: number
  subtotal: number
  iva_rate?: number | null
  product_code?: string | null
}

interface InvoiceTotalsShape {
  subtotal: number
  iva_amount?: number | null
  rete_renta?: number | null
  rete_iva?: number | null
  rete_ica?: number | null
  total_retenciones?: number | null
  total: number
}

interface InvoiceDataShape {
  invoice_number?: string | null
  issue_date?: string | null
  supplier?: {
    company_name?: string | null
    nit?: string | null
  }
  line_items: InvoiceLineItemShape[]
  totals: InvoiceTotalsShape
}

interface PricingDataShape {
  invoice_number?: string | null
  supplier_name?: string | null
  issue_date?: string | null
  pricing_status: string
  total_amount: number
  priced_items?: number
  total_items?: number
}

interface AlegraResult {
  bill_id?: string
  warning?: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatCOP(amount: number): string {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    minimumFractionDigits: 0,
  }).format(amount)
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "—"
  try {
    return new Date(dateStr).toLocaleDateString("es-CO", {
      year: "numeric",
      month: "long",
      day: "numeric",
    })
  } catch {
    return dateStr
  }
}

function PricingStatusBadge({ status }: { status: string }) {
  switch (status) {
    case "confirmed":
      return <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Confirmada</Badge>
    case "completed":
      return <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">Completada</Badge>
    case "partial":
      return <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">Parcial</Badge>
    case "pending":
      return <Badge className="bg-gray-100 text-gray-700 hover:bg-gray-100">Pendiente</Badge>
    default:
      return <Badge variant="secondary">{status}</Badge>
  }
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>()
  const id = params.id
  const router = useRouter()

  const [invoiceData, setInvoiceData] = useState<InvoiceDataShape | null>(null)
  const [pricingData, setPricingData] = useState<PricingDataShape | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isPolling, setIsPolling] = useState(false)

  const [confirming, setConfirming] = useState(false)
  const [confirmError, setConfirmError] = useState<string | null>(null)
  const [alegraResult, setAlegraResult] = useState<AlegraResult | null>(null)

  const pollingRef = useRef<NodeJS.Timeout | null>(null)
  const pollingStartRef = useRef<number>(0)

  // Cleanup polling timer on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearTimeout(pollingRef.current)
    }
  }, [])

  const fetchInvoiceData = useCallback(async () => {
    const [dataRes, pricingRes] = await Promise.all([
      facturaAPI.getInvoiceData(id),
      facturaAPI.getPricingInfo(id).catch(() => null), // optional — never crashes the page
    ])

    if (!dataRes.success || !dataRes.data) {
      throw new Error(dataRes.error?.message ?? "No se pudo cargar los datos de la factura")
    }

    setInvoiceData(dataRes.data as unknown as InvoiceDataShape)
    if (pricingRes?.success && pricingRes.data) {
      setPricingData(pricingRes.data as unknown as PricingDataShape)
    }
  }, [id])

  const loadData = useCallback(async () => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current)
      pollingRef.current = null
    }
    setIsPolling(false)
    setLoading(true)
    setError(null)

    try {
      // Check processing status before fetching data
      const statusRes = await facturaAPI.getInvoiceStatus(id)
      if (!statusRes.success || !statusRes.data) {
        throw new Error(statusRes.error?.message ?? "No se pudo cargar la factura")
      }

      const currentStatus = (statusRes.data as any).status

      if (currentStatus === "processing" || currentStatus === "uploaded") {
        // Invoice is still being processed — start polling every 2s
        setIsPolling(true)
        setLoading(false)
        pollingStartRef.current = Date.now()

        const poll = async () => {
          if (Date.now() - pollingStartRef.current > 60_000) {
            setIsPolling(false)
            setError("El procesamiento tardó demasiado, intenta de nuevo")
            return
          }

          const res = await facturaAPI.getInvoiceStatus(id)
          const st = (res.data as any)?.status

          if (st === "completed" || st === "failed") {
            setIsPolling(false)
            setLoading(true)
            try {
              await fetchInvoiceData()
            } catch (err) {
              setError(err instanceof Error ? err.message : "Error desconocido")
            } finally {
              setLoading(false)
            }
          } else {
            pollingRef.current = setTimeout(poll, 2000)
          }
        }

        pollingRef.current = setTimeout(poll, 2000)
        return
      }

      // Status is completed or failed — fetch data immediately
      await fetchInvoiceData()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido")
    } finally {
      setLoading(false)
    }
  }, [id, fetchInvoiceData])

  useEffect(() => {
    if (id) loadData()
  }, [id, loadData])

  const handleConfirm = async () => {
    setConfirming(true)
    setConfirmError(null)
    try {
      const res = await facturaAPI.confirmPricing(id)
      if (!res.success) {
        throw new Error(res.error?.message ?? "Error al confirmar la factura")
      }
      const result = (res.data as any)?.result ?? {}
      setAlegraResult({
        bill_id: result?.alegra_bill?.id ?? undefined,
        warning: result?.alegra_warning ?? undefined,
      })
      setPricingData((prev) => prev ? { ...prev, pricing_status: "confirmed" } : prev)
    } catch (err) {
      setConfirmError(err instanceof Error ? err.message : "Error desconocido al confirmar")
    } finally {
      setConfirming(false)
    }
  }

  // ── Polling state (invoice is being processed) ─────────────────────────────

  if (isPolling) {
    return (
      <div className="max-w-5xl mx-auto p-6">
        <Card>
          <CardContent className="p-12 text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Procesando factura...
            </h3>
            <p className="text-sm text-gray-500">
              Esto puede tomar unos segundos
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  // ── Loading state ───────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <Card>
          <CardContent className="p-6 space-y-3">
            <Skeleton className="h-7 w-56" />
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-4 w-32" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6 space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </CardContent>
        </Card>
      </div>
    )
  }

  // ── Error state ─────────────────────────────────────────────────────────────

  if (error) {
    return (
      <div className="max-w-5xl mx-auto p-6">
        <Card>
          <CardContent className="p-12 text-center">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Error al cargar la factura
            </h3>
            <p className="text-sm text-red-600 mb-6">{error}</p>
            <div className="flex gap-3 justify-center">
              <Button variant="outline" onClick={() => router.back()}>
                <ArrowLeft className="w-4 h-4 mr-2" />
                Volver
              </Button>
              <Button onClick={loadData}>Reintentar</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // ── Empty state (API success but empty body) ────────────────────────────────

  if (!invoiceData) {
    return (
      <div className="max-w-5xl mx-auto p-6">
        <Card>
          <CardContent className="p-12 text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Factura no encontrada
            </h3>
            <Button variant="outline" onClick={() => router.back()}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Volver
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // ── Derived values ──────────────────────────────────────────────────────────

  const supplierName =
    pricingData?.supplier_name ??
    invoiceData.supplier?.company_name ??
    "Proveedor desconocido"
  const invoiceNumber =
    pricingData?.invoice_number ?? invoiceData.invoice_number ?? "Sin número"
  const issueDate = invoiceData.issue_date ?? pricingData?.issue_date
  const isConfirmed = pricingData?.pricing_status === "confirmed"
  const hasPricedItems = (pricingData?.priced_items ?? 0) > 0

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">

      {/* Back navigation */}
      <Button
        variant="ghost"
        size="sm"
        className="text-gray-600 -ml-2"
        onClick={() => router.back()}
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Volver a Facturas
      </Button>

      {/* Header */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div className="space-y-1">
              <h1 className="text-2xl font-bold text-gray-900">{invoiceNumber}</h1>
              <p className="text-lg text-gray-700">{supplierName}</p>
              {invoiceData.supplier?.nit && (
                <p className="text-sm text-gray-500">NIT: {invoiceData.supplier.nit}</p>
              )}
              <p className="text-sm text-gray-500">Fecha: {formatDate(issueDate)}</p>
            </div>

            <div className="flex flex-col items-start sm:items-end gap-2">
              {pricingData && <PricingStatusBadge status={pricingData.pricing_status} />}
              {isConfirmed && (
                <div className="flex items-center gap-1 text-sm font-medium text-green-700">
                  <CheckCircle className="w-4 h-4" />
                  Sincronizado con Alegra
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Alegra result feedback (shown after confirming) */}
      {alegraResult && (
        <Card
          className={
            alegraResult.warning
              ? "border-yellow-300 bg-yellow-50"
              : "border-green-300 bg-green-50"
          }
        >
          <CardContent className="p-4">
            {alegraResult.bill_id ? (
              <div className="flex items-center gap-2 text-green-800">
                <CheckCircle className="w-5 h-5 shrink-0" />
                <span>
                  Factura creada en Alegra —{" "}
                  <strong>ID: {alegraResult.bill_id}</strong>
                </span>
              </div>
            ) : alegraResult.warning ? (
              <div className="flex items-center gap-2 text-yellow-800">
                <AlertCircle className="w-5 h-5 shrink-0" />
                <span>{alegraResult.warning}</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-green-800">
                <CheckCircle className="w-5 h-5 shrink-0" />
                <span>
                  Inventario actualizado correctamente (Alegra no configurado en este tenant)
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Line items table */}
      <Card>
        <CardHeader>
          <CardTitle>Ítems de la Factura</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {invoiceData.line_items.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              No hay ítems disponibles en esta factura
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="px-6 py-3 text-left font-medium text-gray-600">
                      Descripción
                    </th>
                    <th className="px-4 py-3 text-right font-medium text-gray-600">
                      Cantidad
                    </th>
                    <th className="px-4 py-3 text-right font-medium text-gray-600">
                      Precio Unit.
                    </th>
                    <th className="px-4 py-3 text-right font-medium text-gray-600">
                      IVA %
                    </th>
                    <th className="px-6 py-3 text-right font-medium text-gray-600">
                      Subtotal
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {invoiceData.line_items.map((item, idx) => (
                    <tr
                      key={idx}
                      className="border-b last:border-0 hover:bg-gray-50 transition-colors"
                    >
                      <td className="px-6 py-3 text-gray-900">
                        {item.description}
                        {item.product_code && (
                          <span className="ml-2 text-xs text-gray-400">
                            ({item.product_code})
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-700">
                        {Number(item.quantity)}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-700">
                        {formatCOP(Number(item.unit_price))}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-500">
                        {item.iva_rate != null ? `${Number(item.iva_rate)}%` : "—"}
                      </td>
                      <td className="px-6 py-3 text-right font-medium text-gray-900">
                        {formatCOP(Number(item.subtotal))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Totals + Confirm action */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

        {/* Totals */}
        <Card>
          <CardHeader>
            <CardTitle>Resumen</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Subtotal</span>
              <span className="font-medium">
                {formatCOP(Number(invoiceData.totals.subtotal))}
              </span>
            </div>

            {invoiceData.totals.iva_amount != null && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">IVA</span>
                <span className="font-medium">
                  {formatCOP(Number(invoiceData.totals.iva_amount))}
                </span>
              </div>
            )}

            {invoiceData.totals.rete_renta != null && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Retención en la Fuente</span>
                <span className="font-medium text-red-600">
                  − {formatCOP(Number(invoiceData.totals.rete_renta))}
                </span>
              </div>
            )}

            {invoiceData.totals.rete_iva != null && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">ReteIVA</span>
                <span className="font-medium text-red-600">
                  − {formatCOP(Number(invoiceData.totals.rete_iva))}
                </span>
              </div>
            )}

            {invoiceData.totals.rete_ica != null && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">ReteICA</span>
                <span className="font-medium text-red-600">
                  − {formatCOP(Number(invoiceData.totals.rete_ica))}
                </span>
              </div>
            )}

            {(invoiceData.totals.total_retenciones ?? 0) > 0 && (
              <div className="flex justify-between text-xs text-gray-400">
                <span>Total retenciones</span>
                <span>
                  − {formatCOP(Number(invoiceData.totals.total_retenciones))}
                </span>
              </div>
            )}

            <Separator />

            <div className="flex justify-between text-base font-bold">
              <span>Total</span>
              <span>{formatCOP(Number(invoiceData.totals.total))}</span>
            </div>
          </CardContent>
        </Card>

        {/* Confirm action — only shown when pricing data is available */}
        <Card>
          <CardHeader>
            <CardTitle>Confirmación</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {!pricingData ? (
              <p className="text-sm text-gray-400">Datos de precios no disponibles.</p>
            ) : isConfirmed ? (
              <div className="flex items-start gap-3 p-4 bg-green-50 rounded-lg border border-green-200">
                <CheckCircle className="w-5 h-5 text-green-600 shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-green-800">Factura confirmada</p>
                  <p className="text-sm text-green-700 mt-1">
                    El inventario ha sido actualizado y la factura fue enviada a Alegra.
                  </p>
                </div>
              </div>
            ) : !hasPricedItems ? (
              <div className="flex items-start gap-3 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                <AlertCircle className="w-5 h-5 text-yellow-600 shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-yellow-800">Sin precios asignados</p>
                  <p className="text-sm text-yellow-700 mt-1">
                    Asigna precios de venta a los ítems desde el dashboard antes de confirmar.
                  </p>
                </div>
              </div>
            ) : (
              <>
                <p className="text-sm text-gray-600">
                  Al confirmar, los precios de venta se guardarán en el inventario
                  y la factura se enviará a Alegra.
                </p>

                {pricingData.priced_items !== undefined && pricingData.total_items !== undefined &&
                  pricingData.priced_items < pricingData.total_items && (
                  <div className="flex items-start gap-2 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                    <AlertCircle className="w-5 h-5 text-yellow-500 shrink-0 mt-0.5" />
                    <p className="text-sm text-yellow-700">
                      {pricingData.priced_items} de {pricingData.total_items} ítems tienen precio asignado.
                      Solo se confirmarán los ítems con precio.
                    </p>
                  </div>
                )}

                {confirmError && (
                  <div className="flex items-start gap-2 p-3 bg-red-50 rounded-lg border border-red-200">
                    <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                    <p className="text-sm text-red-700">{confirmError}</p>
                  </div>
                )}

                <Button
                  className="w-full bg-blue-600 hover:bg-blue-700"
                  onClick={handleConfirm}
                  disabled={confirming}
                >
                  {confirming ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                      Procesando...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4 mr-2" />
                      Confirmar y enviar a Alegra
                    </>
                  )}
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
