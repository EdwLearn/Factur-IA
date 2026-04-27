"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { apiClient } from "@/src/lib/api/client"
import { getUsage, PLAN_LABELS, type UsageInfo } from "@/src/lib/api/endpoints/subscriptions"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  Building2,
  Plug,
  Users,
  Bell,
  CheckCircle,
  XCircle,
  Plus,
  Trash2,
  Save,
  RefreshCw,
  Loader2,
  Upload,
  Crown,
  AlertTriangle,
  Zap,
  Clock,
} from "lucide-react"

// ─── Types ────────────────────────────────────────────────────────────────────

interface User {
  id: string
  name: string
  email: string
  role: "Admin" | "Usuario"
  status: "active" | "inactive"
}

interface CompanyForm {
  name: string
  nit: string
  phone: string
  email: string
  address: string
}

interface AlegraInfo {
  businessName: string
  connectedAt: string
  syncedItems: number
  lastSync: string
}

interface SyncResult {
  pushed: number
  updated: number
  pulled: number
  contacts: number
  errors: string[]
}

// ─── Tabs ─────────────────────────────────────────────────────────────────────

const tabs = [
  { id: "empresa",        label: "Mi Empresa",    icon: Building2 },
  { id: "integraciones",  label: "Integraciones", icon: Plug },
  { id: "usuarios",       label: "Usuarios",      icon: Users },
  { id: "notificaciones", label: "Notificaciones",icon: Bell },
] as const

type TabId = typeof tabs[number]["id"]

// ─── Component ────────────────────────────────────────────────────────────────

export function ConfigurationPage() {
  const [activeTab, setActiveTab]   = useState<TabId>("empresa")
  const [isDirty,   setIsDirty]     = useState(false)

  // ── Company form ──
  const [company, setCompany] = useState<CompanyForm>({
    name: "", nit: "", phone: "", email: "", address: "",
  })
  const [logoPreview, setLogoPreview] = useState<string | null>(null)
  const logoInputRef = useRef<HTMLInputElement>(null)

  // ── Plan ──
  const [usage, setUsage] = useState<UsageInfo | null>(null)

  // ── Alegra ──
  const [alegraConnected,   setAlegraConnected]   = useState(false)
  const [alegraConnectOpen, setAlegraConnectOpen] = useState(false)
  const [alegraConfigOpen,  setAlegraConfigOpen]  = useState(false)
  const [alegraEmail,       setAlegraEmail]       = useState("")
  const [alegraToken,       setAlegraToken]       = useState("")
  const [alegraConnecting,  setAlegraConnecting]  = useState(false)
  const [alegraSyncing,     setAlegraSyncing]     = useState(false)
  const [alegraError,       setAlegraError]       = useState<string | null>(null)
  const [alegraSyncResult,  setAlegraSyncResult]  = useState<SyncResult | null>(null)
  const [alegraInfo,        setAlegraInfo]        = useState<AlegraInfo>({
    businessName: "", connectedAt: "", syncedItems: 0, lastSync: "",
  })

  // ── Users ──
  const [users,        setUsers]        = useState<User[]>([])
  const [usersLoading, setUsersLoading] = useState(false)
  const [inviteOpen,   setInviteOpen]   = useState(false)
  const [inviteEmail,  setInviteEmail]  = useState("")
  const [inviteRole,   setInviteRole]   = useState<"Admin" | "Usuario">("Usuario")

  // ── Notifications ──
  const [notifs, setNotifs] = useState({
    newInvoices:  true,
    procErrors:   true,
    lowStock:     true,
    weeklyReport: false,
    monthlyReport:true,
  })

  // ─── Load Alegra status ────────────────────────────────────────────────────

  const loadProfile = useCallback(async () => {
    try {
      const res = await apiClient.get("/auth/me")
      if (res.success && res.data) {
        const d = res.data as any
        setCompany({
          name:    d.company_name ?? "",
          nit:     d.nit         ?? "",
          phone:   d.phone       ?? "",
          email:   d.email       ?? "",
          address: "",
        })
      }
    } catch { /* silencioso */ }
  }, [])

  const loadUsage = useCallback(async () => {
    try {
      const data = await getUsage()
      setUsage(data)
    } catch { /* silencioso */ }
  }, [])

  const loadAlegraStatus = useCallback(async () => {
    try {
      const res = await apiClient.get("/integrations/alegra/status")
      if (res.success && res.data?.connected) {
        setAlegraConnected(true)
        setAlegraInfo({
          businessName: res.data.email ?? "Cuenta Alegra",
          connectedAt:  res.data.connected_at
            ? new Date(res.data.connected_at).toLocaleDateString("es-CO")
            : "",
          syncedItems: res.data.synced_items ?? 0,
          lastSync:    res.data.last_sync
            ? new Date(res.data.last_sync).toLocaleString("es-CO")
            : "",
        })
      }
    } catch { /* silencioso */ }
  }, [])

  // ─── Load users ───────────────────────────────────────────────────────────

  const loadUsers = useCallback(async () => {
    setUsersLoading(true)
    try {
      const res = await apiClient.get("/users")
      if (res.success && Array.isArray(res.data)) {
        setUsers(res.data)
      }
    } catch { /* endpoint puede no existir aún */ }
    finally { setUsersLoading(false) }
  }, [])

  useEffect(() => {
    loadProfile()
    loadUsage()
    loadAlegraStatus()
    loadUsers()
  }, [loadProfile, loadUsage, loadAlegraStatus, loadUsers])

  // ─── Handlers ─────────────────────────────────────────────────────────────

  function markDirty() { setIsDirty(true) }

  function handleCompanyChange(field: keyof CompanyForm, value: string) {
    setCompany(prev => ({ ...prev, [field]: value }))
    markDirty()
  }

  function handleLogoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = ev => setLogoPreview(ev.target?.result as string)
    reader.readAsDataURL(file)
    markDirty()
  }

  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  async function handleSave() {
    setSaving(true)
    setSaveError(null)
    try {
      const res = await apiClient.request("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({
          company_name: company.name   || undefined,
          nit:          company.nit    || undefined,
          email:        company.email  || undefined,
          phone:        company.phone  || undefined,
        }),
      })
      if (!res.success) throw new Error(res.error?.message ?? "Error al guardar")
      setIsDirty(false)
    } catch (err: any) {
      setSaveError(err.message ?? "Error al guardar")
    } finally {
      setSaving(false)
    }
  }

  async function handleAlegraSync() {
    setAlegraSyncing(true)
    setAlegraSyncResult(null)
    try {
      const res = await apiClient.post("/integrations/alegra/sync-items")
      if (!res.success) throw new Error(res.error?.message ?? "Error al sincronizar")
      const d = res.data
      setAlegraSyncResult({
        pushed:   d?.pushed_items    ?? 0,
        updated:  d?.updated_items   ?? 0,
        pulled:   d?.pulled_items    ?? 0,
        contacts: d?.synced_contacts ?? 0,
        errors:   d?.errors          ?? [],
      })
      setAlegraInfo(prev => ({
        ...prev,
        syncedItems: d?.synced_items ?? prev.syncedItems,
        lastSync:    d?.synced_at
          ? new Date(d.synced_at).toLocaleString("es-CO")
          : prev.lastSync,
      }))
    } catch (err) {
      setAlegraSyncResult({
        pushed: 0, updated: 0, pulled: 0, contacts: 0,
        errors: [err instanceof Error ? err.message : "Error desconocido"],
      })
    } finally {
      setAlegraSyncing(false)
    }
  }

  async function handleAlegraConnect() {
    setAlegraConnecting(true)
    setAlegraError(null)
    try {
      const res = await apiClient.post("/integrations/alegra/connect", {
        email: alegraEmail,
        token: alegraToken,
      })
      if (!res.success) {
        const detail = (res.error as any)?.detail ?? res.error?.message
        const msg =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
            ? detail.map((d: any) => d.msg ?? JSON.stringify(d)).join(", ")
            : "No se pudo conectar con Alegra"
        throw new Error(msg)
      }
      setAlegraInfo({
        businessName: res.data?.user?.email ?? "Cuenta Alegra",
        connectedAt:  res.data?.connected_at
          ? new Date(res.data.connected_at).toLocaleDateString("es-CO")
          : new Date().toLocaleDateString("es-CO"),
        syncedItems: 0,
        lastSync: "",
      })
      setAlegraConnected(true)
      setAlegraConnectOpen(false)
      setAlegraEmail("")
      setAlegraToken("")
    } catch (err) {
      setAlegraError(err instanceof Error ? err.message : "Error desconocido")
    } finally {
      setAlegraConnecting(false)
    }
  }

  async function handleAlegraDisconnect() {
    await apiClient.delete("/integrations/alegra/disconnect")
    setAlegraConnected(false)
    setAlegraInfo({ businessName: "", connectedAt: "", syncedItems: 0, lastSync: "" })
    setAlegraSyncResult(null)
    setAlegraConfigOpen(false)
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────

  const planType   = usage?.plan ?? "freemium"
  const planName   = PLAN_LABELS[planType] ?? planType
  const planUsed   = usage?.invoice_count ?? 0
  const planLimit  = usage?.invoice_limit   // null = ilimitado
  const planDays   = usage?.days_until_reset ?? 30

  const planColor: Record<string, string> = {
    freemium: "bg-gray-100 text-gray-700",
    basic:    "bg-blue-100 text-blue-700",
    pro:      "bg-purple-100 text-purple-700",
  }

  const progressPct = planLimit ? Math.min(100, Math.round((planUsed / planLimit) * 100)) : 0
  const progressColor =
    progressPct > 90 ? "bg-red-500"
    : progressPct > 70 ? "bg-yellow-400"
    : "bg-green-500"

  // ─── Render sections ──────────────────────────────────────────────────────

  const renderEmpresa = () => (
    <div className="flex gap-6 items-start">

      {/* Left — Company info (2/3) */}
      <div className="flex-1 bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Información de la empresa</h2>
          <p className="text-sm text-gray-500 mt-0.5">Datos que aparecerán en tus documentos</p>
        </div>

        {/* Logo */}
        <div className="flex items-center gap-4">
          <div
            className="w-16 h-16 rounded-full border-2 border-dashed border-gray-200 flex items-center justify-center overflow-hidden cursor-pointer hover:border-blue-400 transition-colors bg-gray-50"
            onClick={() => logoInputRef.current?.click()}
          >
            {logoPreview
              ? <img src={logoPreview} alt="logo" className="w-full h-full object-cover" />
              : <Building2 className="w-6 h-6 text-gray-400" />
            }
          </div>
          <div>
            <button
              onClick={() => logoInputRef.current?.click()}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
            >
              <Upload className="w-3.5 h-3.5" />
              {logoPreview ? "Cambiar logo" : "Subir logo"}
            </button>
            <p className="text-xs text-gray-400 mt-0.5">PNG o JPG, máx 1 MB</p>
          </div>
          <input
            ref={logoInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleLogoChange}
          />
        </div>

        {/* Fields grid */}
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2 space-y-1">
            <Label className="text-sm text-gray-700">Nombre del negocio</Label>
            <input
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={company.name}
              onChange={e => handleCompanyChange("name", e.target.value)}
            />
          </div>

          <div className="space-y-1">
            <Label className="text-sm text-gray-700">NIT</Label>
            <input
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={company.nit}
              onChange={e => handleCompanyChange("nit", e.target.value)}
            />
          </div>

          <div className="space-y-1">
            <Label className="text-sm text-gray-700">Teléfono</Label>
            <input
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={company.phone}
              onChange={e => handleCompanyChange("phone", e.target.value)}
            />
          </div>

          <div className="col-span-2 space-y-1">
            <Label className="text-sm text-gray-700">Email de contacto</Label>
            <input
              type="email"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={company.email}
              onChange={e => handleCompanyChange("email", e.target.value)}
            />
          </div>

          <div className="col-span-2 space-y-1">
            <Label className="text-sm text-gray-700">Dirección</Label>
            <textarea
              rows={2}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              value={company.address}
              onChange={e => handleCompanyChange("address", e.target.value)}
            />
          </div>
        </div>

        {(isDirty || saveError) && (
          <div className="pt-2 space-y-2">
            {saveError && (
              <p className="text-xs text-red-600">{saveError}</p>
            )}
            <button
              onClick={handleSave}
              disabled={saving}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
            >
              {saving
                ? <><Loader2 className="w-4 h-4 animate-spin" />Guardando...</>
                : <><Save className="w-4 h-4" />Guardar cambios</>
              }
            </button>
          </div>
        )}
      </div>

      {/* Right — Plan (1/3) */}
      <div className="w-72 shrink-0 bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Plan actual</h2>
        </div>

        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
            <Crown className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${planColor[planType] ?? planColor.freemium}`}>
              {planName}
            </span>
          </div>
        </div>

        {/* Usage bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Facturas este mes</span>
            <span className="font-medium text-gray-900">{planUsed} / {planLimit ?? "∞"}</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${progressColor}`}
              style={{ width: `${progressPct}%` }}
            />
          </div>
          {progressPct > 80 && (
            <p className="text-xs text-yellow-600 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Estás cerca del límite
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Clock className="w-4 h-4" />
          <span>Se reinicia en <strong className="text-gray-700">{planDays} días</strong></span>
        </div>

        <Separator />

        <button
          className="w-full border border-gray-200 hover:bg-gray-50 text-sm text-gray-700 py-2 rounded-lg transition-colors font-medium"
          onClick={() => window.location.href = "/pricing"}
        >
          Ver planes →
        </button>
      </div>
    </div>
  )

  const renderIntegraciones = () => (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-semibold text-gray-900">Conecta FacturIA con tus herramientas</h2>
        <p className="text-sm text-gray-500 mt-0.5">Sincroniza datos con los sistemas que ya usas</p>
      </div>

      {/* Alegra — full width, prominent */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${alegraConnected ? "bg-orange-100" : "bg-gray-100"}`}>
              <Zap className={`w-6 h-6 ${alegraConnected ? "text-orange-500" : "text-gray-400"}`} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold text-gray-900">Alegra</h3>
                <span className={`flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                  alegraConnected
                    ? "bg-green-100 text-green-700"
                    : "bg-gray-100 text-gray-500"
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${alegraConnected ? "bg-green-500" : "bg-gray-400"}`} />
                  {alegraConnected ? "Conectado" : "No conectado"}
                </span>
              </div>
              <p className="text-sm text-gray-500 mt-0.5">Software contable líder en Colombia</p>
            </div>
          </div>

          {/* Actions */}
          {alegraConnected ? (
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={handleAlegraSync}
                disabled={alegraSyncing}
                className="flex items-center gap-2 text-sm border border-orange-200 text-orange-700 hover:bg-orange-50 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-60"
              >
                {alegraSyncing
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <RefreshCw className="w-4 h-4" />
                }
                {alegraSyncing ? "Sincronizando..." : "Sincronizar catálogo"}
              </button>
              <Dialog open={alegraConfigOpen} onOpenChange={setAlegraConfigOpen}>
                <DialogTrigger asChild>
                  <button className="text-sm border border-gray-200 text-gray-600 hover:bg-gray-50 px-3 py-1.5 rounded-lg transition-colors">
                    Configurar
                  </button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Alegra — Configuración</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-500">Cuenta</p>
                        <p className="text-sm font-medium text-gray-900 truncate">{alegraInfo.businessName}</p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-500">Conectado desde</p>
                        <p className="text-sm font-medium text-gray-900">{alegraInfo.connectedAt || "—"}</p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-500">Ítems sincronizados</p>
                        <p className="text-lg font-bold text-gray-900">{alegraInfo.syncedItems}</p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-500">Última sync</p>
                        <p className="text-sm font-medium text-gray-900">{alegraInfo.lastSync || "—"}</p>
                      </div>
                    </div>

                    {alegraSyncResult && (
                      <div className="bg-blue-50 rounded-lg p-4 text-sm space-y-1">
                        <p className="font-medium text-gray-700 mb-2">Último resultado</p>
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-gray-600">
                          <span>Creados en Alegra</span>
                          <span className="font-medium text-green-700">+{alegraSyncResult.pushed}</span>
                          <span>Actualizados</span>
                          <span className="font-medium text-blue-700">{alegraSyncResult.updated}</span>
                          <span>Precios recibidos</span>
                          <span className="font-medium text-purple-700">{alegraSyncResult.pulled}</span>
                          <span>Contactos</span>
                          <span className="font-medium text-orange-700">{alegraSyncResult.contacts}</span>
                        </div>
                        {alegraSyncResult.errors.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-blue-200">
                            <p className="text-xs text-red-600 font-medium">{alegraSyncResult.errors.length} error(es):</p>
                            <ul className="text-xs text-red-500 mt-1 space-y-0.5 max-h-20 overflow-y-auto">
                              {alegraSyncResult.errors.map((e, i) => (
                                <li key={i} className="truncate">• {e}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}

                    <Separator />
                    <button
                      onClick={handleAlegraDisconnect}
                      className="w-full bg-red-50 text-red-600 hover:bg-red-100 text-sm py-2 rounded-lg flex items-center justify-center gap-2 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                      Desconectar cuenta
                    </button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          ) : (
            <Dialog
              open={alegraConnectOpen}
              onOpenChange={(open) => {
                setAlegraConnectOpen(open)
                setAlegraError(null)
                if (!open) { setAlegraEmail(""); setAlegraToken("") }
              }}
            >
              <DialogTrigger asChild>
                <button className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg transition-colors font-medium shrink-0 flex items-center gap-2">
                  Conectar con Alegra →
                </button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Conectar con Alegra</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-1">
                    <Label className="text-sm text-gray-700">Email de tu cuenta Alegra</Label>
                    <input
                      type="email"
                      placeholder="tu@empresa.com"
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      value={alegraEmail}
                      onChange={e => setAlegraEmail(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-sm text-gray-700">Token de API</Label>
                    <input
                      type="password"
                      placeholder="Pega tu token aquí"
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      value={alegraToken}
                      onChange={e => setAlegraToken(e.target.value)}
                    />
                    <p className="text-xs text-gray-400">
                      Encuéntralo en Alegra → Configuración → Integraciones → API
                    </p>
                  </div>
                  {alegraError && (
                    <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                      <p className="text-sm text-red-700">{alegraError}</p>
                    </div>
                  )}
                  <button
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm py-2.5 rounded-lg transition-colors font-medium flex items-center justify-center gap-2"
                    disabled={alegraConnecting || !alegraEmail.trim() || !alegraToken.trim()}
                    onClick={handleAlegraConnect}
                  >
                    {alegraConnecting
                      ? <><Loader2 className="w-4 h-4 animate-spin" /> Validando...</>
                      : "Conectar"
                    }
                  </button>
                </div>
              </DialogContent>
            </Dialog>
          )}
        </div>

        {/* Connected stats inline */}
        {alegraConnected && (
          <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-400 text-xs">Cuenta</p>
              <p className="font-medium text-gray-800 truncate">{alegraInfo.businessName}</p>
            </div>
            <div>
              <p className="text-gray-400 text-xs">Última sincronización</p>
              <p className="font-medium text-gray-800">{alegraInfo.lastSync || "Nunca"}</p>
            </div>
            <div>
              <p className="text-gray-400 text-xs">Ítems sincronizados</p>
              <p className="font-medium text-gray-800">{alegraInfo.syncedItems}</p>
            </div>
          </div>
        )}
      </div>

      {/* Secondary integrations grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* AWS Textract */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-yellow-600" />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-gray-900">AWS Textract</h4>
                <span className="flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  Activo
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-0.5">Extracción de texto por OCR</p>
            </div>
          </div>
        </div>

        {/* Wompi — coming soon */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 opacity-70">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
              <Plug className="w-5 h-5 text-gray-400" />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-gray-700">Wompi</h4>
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                  Pronto
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">Pagos en línea</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )

  const renderUsuarios = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Usuarios del sistema</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              {users.length} de 3 usuarios permitidos en tu plan
            </p>
          </div>
          <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
            <DialogTrigger asChild>
              <button className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg flex items-center gap-2 transition-colors">
                <Plus className="w-4 h-4" />
                Invitar usuario
              </button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Invitar nuevo usuario</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-1">
                  <Label className="text-sm text-gray-700">Correo electrónico</Label>
                  <input
                    type="email"
                    placeholder="usuario@empresa.com"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    value={inviteEmail}
                    onChange={e => setInviteEmail(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-sm text-gray-700">Rol</Label>
                  <Select value={inviteRole} onValueChange={v => setInviteRole(v as "Admin" | "Usuario")}>
                    <SelectTrigger className="border-gray-200 text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Admin">Admin</SelectItem>
                      <SelectItem value="Usuario">Usuario</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex gap-2">
                  <button
                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-sm py-2 rounded-lg transition-colors"
                    onClick={() => setInviteOpen(false)}
                  >
                    Enviar invitación
                  </button>
                  <button
                    className="border border-gray-200 hover:bg-gray-50 text-sm px-4 py-2 rounded-lg transition-colors"
                    onClick={() => setInviteOpen(false)}
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Table or empty state */}
        {usersLoading ? (
          <div className="flex items-center justify-center py-12 text-gray-400">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            Cargando usuarios...
          </div>
        ) : users.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-400">
            <Users className="w-10 h-10 mb-3 text-gray-300" />
            <p className="text-sm font-medium text-gray-500">No hay usuarios aún</p>
            <p className="text-xs text-gray-400 mt-1">Invita a tu equipo para colaborar</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="bg-gray-50 border-0">
                <TableHead className="text-xs text-gray-500 font-medium">Usuario</TableHead>
                <TableHead className="text-xs text-gray-500 font-medium">Rol</TableHead>
                <TableHead className="text-xs text-gray-500 font-medium">Estado</TableHead>
                <TableHead className="text-xs text-gray-500 font-medium w-20"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id} className="border-gray-100">
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar className="w-8 h-8">
                        <AvatarFallback className="bg-blue-100 text-blue-700 text-xs font-semibold">
                          {user.name.split(" ").map(n => n[0]).join("").slice(0, 2)}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{user.name}</p>
                        <p className="text-xs text-gray-400">{user.email}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      user.role === "Admin"
                        ? "bg-blue-100 text-blue-700"
                        : "bg-gray-100 text-gray-600"
                    }`}>
                      {user.role}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className={`flex items-center gap-1 text-xs font-medium w-fit px-2 py-0.5 rounded-full ${
                      user.status === "active"
                        ? "bg-green-100 text-green-700"
                        : "bg-gray-100 text-gray-500"
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${user.status === "active" ? "bg-green-500" : "bg-gray-400"}`} />
                      {user.status === "active" ? "Activo" : "Inactivo"}
                    </span>
                  </TableCell>
                  <TableCell>
                    <button className="text-gray-400 hover:text-red-500 transition-colors p-1 rounded">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Roles legend */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Permisos por rol</h3>
        <div className="grid grid-cols-3 gap-px bg-gray-100 rounded-lg overflow-hidden text-sm">
          <div className="bg-white px-4 py-3 font-medium text-gray-700">Módulo</div>
          <div className="bg-white px-4 py-3 font-medium text-center text-blue-700">Admin</div>
          <div className="bg-white px-4 py-3 font-medium text-center text-gray-600">Usuario</div>
          {["Facturas", "Inventario", "Reportes", "Configuración"].map(mod => (
            <>
              <div key={mod + "-label"} className="bg-white px-4 py-3 text-gray-600">{mod}</div>
              <div key={mod + "-admin"} className="bg-white px-4 py-3 flex justify-center">
                <CheckCircle className="w-4 h-4 text-green-500" />
              </div>
              <div key={mod + "-user"} className="bg-white px-4 py-3 flex justify-center">
                {mod !== "Configuración"
                  ? <CheckCircle className="w-4 h-4 text-green-500" />
                  : <XCircle className="w-4 h-4 text-gray-300" />
                }
              </div>
            </>
          ))}
        </div>
      </div>
    </div>
  )

  const renderNotificaciones = () => (
    <div className="max-w-2xl space-y-4">
      {/* Alertas operación */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Alertas de operación</h2>
          <p className="text-sm text-gray-500 mt-0.5">Notificaciones por email sobre eventos del sistema</p>
        </div>
        <div className="space-y-3">
          {([
            { key: "newInvoices",  label: "Nuevas facturas procesadas",   desc: "Cuando se completa el procesamiento de una factura" },
            { key: "procErrors",   label: "Errores de procesamiento",      desc: "Cuando una factura no puede procesarse correctamente" },
            { key: "lowStock",     label: "Stock bajo en inventario",      desc: "Cuando un producto cae por debajo del mínimo" },
          ] as { key: keyof typeof notifs; label: string; desc: string }[]).map(({ key, label, desc }) => (
            <div key={key} className="flex items-center justify-between py-1">
              <div>
                <p className="text-sm font-medium text-gray-800">{label}</p>
                <p className="text-xs text-gray-400">{desc}</p>
              </div>
              <Switch
                checked={notifs[key]}
                onCheckedChange={v => setNotifs(prev => ({ ...prev, [key]: v }))}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Reportes periódicos */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Reportes periódicos</h2>
          <p className="text-sm text-gray-500 mt-0.5">Resúmenes automáticos enviados a tu email</p>
        </div>
        <div className="space-y-3">
          {([
            { key: "weeklyReport",  label: "Reporte semanal",  desc: "Resumen de actividad cada lunes" },
            { key: "monthlyReport", label: "Reporte mensual",  desc: "Cierre mensual con métricas clave" },
          ] as { key: keyof typeof notifs; label: string; desc: string }[]).map(({ key, label, desc }) => (
            <div key={key} className="flex items-center justify-between py-1">
              <div>
                <p className="text-sm font-medium text-gray-800">{label}</p>
                <p className="text-xs text-gray-400">{desc}</p>
              </div>
              <Switch
                checked={notifs[key]}
                onCheckedChange={v => setNotifs(prev => ({ ...prev, [key]: v }))}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  // ─── Main render ──────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full bg-gray-50">

      {/* ── Page header ── */}
      <div className="bg-white border-b border-gray-200 px-8 py-6">
        <h1 className="text-2xl font-bold text-gray-900">Configuración</h1>
        <p className="text-sm text-gray-500 mt-1">Gestiona tu cuenta y preferencias de FacturIA</p>
      </div>

      {/* ── Horizontal tabs ── */}
      <div className="bg-white border-b border-gray-200 px-8 overflow-x-auto">
        <nav className="flex gap-8 min-w-max">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center gap-2 py-4 text-sm font-medium
                border-b-2 transition-colors whitespace-nowrap
                ${activeTab === tab.id
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"}
              `}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Content ── */}
      <div className="flex-1 overflow-auto p-8">
        {activeTab === "empresa"        && renderEmpresa()}
        {activeTab === "integraciones"  && renderIntegraciones()}
        {activeTab === "usuarios"       && renderUsuarios()}
        {activeTab === "notificaciones" && renderNotificaciones()}
      </div>

      {/* ── Floating save button ── */}
      {isDirty && (
        <div className="fixed bottom-6 right-6 z-50">
          <button
            onClick={handleSave}
            className="bg-blue-600 text-white px-6 py-3 rounded-full shadow-lg hover:bg-blue-700
                       flex items-center gap-2 transition-all text-sm font-medium"
          >
            <Save className="h-4 w-4" />
            Guardar cambios
          </button>
        </div>
      )}
    </div>
  )
}
