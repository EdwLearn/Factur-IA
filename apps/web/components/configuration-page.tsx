"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  Building2,
  Receipt,
  Plug,
  Users,
  Bell,
  Database,
  Upload,
  Phone,
  Crown,
  CheckCircle,
  XCircle,
  Clock,
  Plus,
  Edit,
  Trash2,
  Download,
  Settings,
  Shield,
  Eye,
  Save,
  AlertTriangle,
  Info,
} from "lucide-react"

interface User {
  id: string
  name: string
  email: string
  role: "Administrator" | "User" | "Read-only"
  status: "active" | "inactive"
  lastActivity: string
  permissions: {
    invoices: boolean
    inventory: boolean
    reports: boolean
    configuration: boolean
  }
}

const sampleUsers: User[] = [
  {
    id: "1",
    name: "Juan Pérez",
    email: "juan.perez@almacenmedellinja.com",
    role: "Administrator",
    status: "active",
    lastActivity: "2024-01-15 14:30",
    permissions: { invoices: true, inventory: true, reports: true, configuration: true },
  },
  {
    id: "2",
    name: "María González",
    email: "maria.gonzalez@almacenmedellinja.com",
    role: "User",
    status: "active",
    lastActivity: "2024-01-15 12:15",
    permissions: { invoices: true, inventory: true, reports: true, configuration: false },
  },
  {
    id: "3",
    name: "Carlos Rodríguez",
    email: "carlos.rodriguez@almacenmedellinja.com",
    role: "Read-only",
    status: "inactive",
    lastActivity: "2024-01-10 09:45",
    permissions: { invoices: false, inventory: false, reports: true, configuration: false },
  },
]

export function ConfigurationPage() {
  const [activeTab, setActiveTab] = useState("company")
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false)
  const [autoSave, setAutoSave] = useState(true)

  const tabs = [
    { id: "company", label: "Perfil de Empresa", icon: Building2 },
    { id: "tax", label: "Configuración Fiscal", icon: Receipt },
    { id: "integrations", label: "Integraciones", icon: Plug },
    { id: "users", label: "Usuarios y Permisos", icon: Users },
    { id: "notifications", label: "Notificaciones", icon: Bell },
    { id: "backup", label: "Respaldo y Exportación", icon: Database },
  ]

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "connected":
        return (
          <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
            <CheckCircle className="w-3 h-3 mr-1" />
            Conectado
          </Badge>
        )
      case "disconnected":
        return (
          <Badge className="bg-red-100 text-red-800 hover:bg-red-100">
            <XCircle className="w-3 h-3 mr-1" />
            Desconectado
          </Badge>
        )
      case "pending":
        return (
          <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">
            <Clock className="w-3 h-3 mr-1" />
            Pendiente
          </Badge>
        )
      default:
        return null
    }
  }

  const getRoleBadge = (role: User["role"]) => {
    const colors = {
      Administrator: "bg-blue-100 text-blue-800",
      User: "bg-green-100 text-green-800",
      "Read-only": "bg-gray-100 text-gray-800",
    }
    return <Badge className={`${colors[role]} hover:${colors[role]}`}>{role}</Badge>
  }

  const renderCompanyProfile = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="w-5 h-5" />
            Información de la Empresa
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="company-name">Nombre de la Empresa</Label>
              <Input id="company-name" defaultValue="Almacén Medellín JA" />
            </div>
            <div>
              <Label htmlFor="nit">NIT</Label>
              <Input id="nit" defaultValue="900123456-1" placeholder="Ej: 900123456-1" />
            </div>
            <div>
              <Label htmlFor="business-name">Razón Social</Label>
              <Input id="business-name" defaultValue="Almacén Medellín JA S.A.S" />
            </div>
            <div>
              <Label htmlFor="phone">Teléfono</Label>
              <Input id="phone" defaultValue="+57 4 123-4567" />
            </div>
            <div>
              <Label htmlFor="email">Correo Electrónico</Label>
              <Input id="email" type="email" defaultValue="contacto@almacenmedellinja.com" />
            </div>
            <div>
              <Label htmlFor="website">Sitio Web</Label>
              <Input id="website" defaultValue="www.almacenmedellinja.com" />
            </div>
          </div>

          <div>
            <Label htmlFor="address">Dirección Completa</Label>
            <Textarea
              id="address"
              defaultValue="Carrera 70 #45-23, El Poblado, Medellín, Antioquia, Colombia"
              rows={3}
            />
          </div>

          <div>
            <Label>Logo de la Empresa</Label>
            <div className="mt-2 flex items-center gap-4">
              <div className="w-20 h-20 bg-blue-100 rounded-lg flex items-center justify-center">
                <Building2 className="w-8 h-8 text-blue-600" />
              </div>
              <Button variant="outline">
                <Upload className="w-4 h-4 mr-2" />
                Subir Logo
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Crown className="w-5 h-5" />
            Plan Actual
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-lg">Plan Premium</h3>
              <p className="text-sm text-gray-600">Facturación ilimitada y funciones avanzadas</p>
            </div>
            <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">Activo</Badge>
          </div>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Facturas procesadas este mes</span>
                <span>85 / Ilimitadas</span>
              </div>
              <Progress value={85} className="h-2" />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Usuarios activos</span>
                <span>3 / 10</span>
              </div>
              <Progress value={30} className="h-2" />
            </div>
          </div>

          <Button variant="outline" className="w-full bg-transparent">
            Gestionar Plan
          </Button>
        </CardContent>
      </Card>
    </div>
  )

  const renderTaxSettings = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Receipt className="w-5 h-5" />
            Régimen Tributario
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="tax-regime">Tipo de Régimen</Label>
              <Select defaultValue="ordinary">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="simplified">Régimen Simplificado</SelectItem>
                  <SelectItem value="ordinary">Régimen Ordinario</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="tax-period">Período Fiscal</Label>
              <Select defaultValue="monthly">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="monthly">Mensual</SelectItem>
                  <SelectItem value="bimonthly">Bimestral</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Configuración de IVA</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="vat-rate">Tarifa de IVA (%)</Label>
              <Select defaultValue="19">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">0% - Exento</SelectItem>
                  <SelectItem value="5">5%</SelectItem>
                  <SelectItem value="19">19% - General</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="withholding-rate">Retención en la Fuente (%)</Label>
              <Input id="withholding-rate" defaultValue="3.5" />
            </div>
            <div>
              <Label htmlFor="ica-rate">Retención ICA (%)</Label>
              <Input id="ica-rate" defaultValue="0.966" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Numeración de Facturas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="invoice-prefix">Prefijo</Label>
              <Input id="invoice-prefix" defaultValue="FAC" />
            </div>
            <div>
              <Label htmlFor="next-number">Próximo Número</Label>
              <Input id="next-number" defaultValue="2024-013" />
            </div>
          </div>
          <div className="bg-blue-50 p-3 rounded-lg">
            <p className="text-sm text-blue-800">
              <Info className="w-4 h-4 inline mr-1" />
              Próxima factura: <strong>FAC-2024-013</strong>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )

  const renderIntegrations = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plug className="w-5 h-5" />
            Sistemas POS
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <Settings className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <h4 className="font-medium">Mayasis POS</h4>
                <p className="text-sm text-gray-600">Sistema de punto de venta</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {getStatusBadge("connected")}
              <Button variant="outline" size="sm">
                Configurar
              </Button>
            </div>
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                <Settings className="w-5 h-5 text-gray-600" />
              </div>
              <div>
                <h4 className="font-medium">Siigo</h4>
                <p className="text-sm text-gray-600">Software contable</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {getStatusBadge("disconnected")}
              <Button variant="outline" size="sm">
                Conectar
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Configuración de Email</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="smtp-server">Servidor SMTP</Label>
              <Input id="smtp-server" defaultValue="smtp.gmail.com" />
            </div>
            <div>
              <Label htmlFor="smtp-port">Puerto</Label>
              <Input id="smtp-port" defaultValue="587" />
            </div>
            <div>
              <Label htmlFor="smtp-user">Usuario</Label>
              <Input id="smtp-user" defaultValue="facturas@almacenmedellinja.com" />
            </div>
            <div>
              <Label htmlFor="smtp-password">Contraseña</Label>
              <Input id="smtp-password" type="password" defaultValue="••••••••" />
            </div>
          </div>
          <Button variant="outline">
            <CheckCircle className="w-4 h-4 mr-2" />
            Probar Conexión
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AWS Textract</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="aws-region">Región</Label>
              <Select defaultValue="us-east-1">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="us-east-1">US East (N. Virginia)</SelectItem>
                  <SelectItem value="us-west-2">US West (Oregon)</SelectItem>
                  <SelectItem value="sa-east-1">South America (São Paulo)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="aws-key">Access Key ID</Label>
              <Input id="aws-key" defaultValue="AKIA••••••••••••••••" />
            </div>
          </div>
          <div className="flex items-center gap-3">
            {getStatusBadge("connected")}
            <span className="text-sm text-gray-600">Última sincronización: hace 2 horas</span>
          </div>
        </CardContent>
      </Card>
    </div>
  )

  const renderUsersPermissions = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              Usuarios del Sistema
            </div>
            <Dialog open={isInviteModalOpen} onOpenChange={setIsInviteModalOpen}>
              <DialogTrigger asChild>
                <Button className="bg-blue-600 hover:bg-blue-700">
                  <Plus className="w-4 h-4 mr-2" />
                  Invitar Usuario
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Invitar Nuevo Usuario</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="invite-email">Correo Electrónico</Label>
                    <Input id="invite-email" type="email" placeholder="usuario@empresa.com" />
                  </div>
                  <div>
                    <Label htmlFor="invite-role">Rol</Label>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="Seleccionar rol" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="administrator">Administrador</SelectItem>
                        <SelectItem value="user">Usuario</SelectItem>
                        <SelectItem value="readonly">Solo Lectura</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex gap-2">
                    <Button className="bg-blue-600 hover:bg-blue-700 flex-1">Enviar Invitación</Button>
                    <Button variant="outline" onClick={() => setIsInviteModalOpen(false)}>
                      Cancelar
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-gray-50">
                <TableHead>Usuario</TableHead>
                <TableHead>Rol</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Última Actividad</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sampleUsers.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar className="w-8 h-8">
                        <AvatarFallback className="bg-blue-600 text-white text-xs">
                          {user.name
                            .split(" ")
                            .map((n) => n[0])
                            .join("")}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <p className="font-medium">{user.name}</p>
                        <p className="text-sm text-gray-600">{user.email}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>{getRoleBadge(user.role)}</TableCell>
                  <TableCell>
                    <Badge
                      className={
                        user.status === "active"
                          ? "bg-green-100 text-green-800 hover:bg-green-100"
                          : "bg-gray-100 text-gray-800 hover:bg-gray-100"
                      }
                    >
                      {user.status === "active" ? "Activo" : "Inactivo"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">{user.lastActivity}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm">
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Permisos por Módulo
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="font-medium">Módulo</div>
              <div className="font-medium text-center">Administrador</div>
              <div className="font-medium text-center">Usuario</div>
              <div className="font-medium text-center">Solo Lectura</div>
            </div>
            <Separator />
            {["Facturas", "Inventario", "Reportes", "Configuración"].map((module) => (
              <div key={module} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
                <div>{module}</div>
                <div className="text-center">
                  <CheckCircle className="w-5 h-5 text-green-600 mx-auto" />
                </div>
                <div className="text-center">
                  {module !== "Configuración" ? (
                    <CheckCircle className="w-5 h-5 text-green-600 mx-auto" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-600 mx-auto" />
                  )}
                </div>
                <div className="text-center">
                  {module === "Reportes" ? (
                    <Eye className="w-5 h-5 text-blue-600 mx-auto" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-600 mx-auto" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )

  const renderNotifications = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5" />
            Notificaciones por Email
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {[
            { label: "Nuevas facturas procesadas", enabled: true },
            { label: "Errores de procesamiento", enabled: true },
            { label: "Stock bajo en inventario", enabled: true },
            { label: "Reportes semanales", enabled: false },
            { label: "Actualizaciones del sistema", enabled: true },
          ].map((notification, index) => (
            <div key={index} className="flex items-center justify-between">
              <div>
                <p className="font-medium">{notification.label}</p>
                <p className="text-sm text-gray-600">{notification.enabled ? "Activado" : "Desactivado"}</p>
              </div>
              <Switch defaultChecked={notification.enabled} />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="w-5 h-5" />
            Notificaciones SMS
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="sms-number">Número de Teléfono</Label>
            <Input id="sms-number" defaultValue="+57 300 123 4567" />
          </div>
          {[
            { label: "Alertas críticas del sistema", enabled: true },
            { label: "Confirmaciones de procesamiento", enabled: false },
            { label: "Recordatorios de vencimiento", enabled: true },
          ].map((notification, index) => (
            <div key={index} className="flex items-center justify-between">
              <div>
                <p className="font-medium">{notification.label}</p>
              </div>
              <Switch defaultChecked={notification.enabled} />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Frecuencia de Notificaciones</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="email-frequency">Email</Label>
              <Select defaultValue="immediate">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="immediate">Inmediato</SelectItem>
                  <SelectItem value="daily">Diario</SelectItem>
                  <SelectItem value="weekly">Semanal</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="sms-frequency">SMS</Label>
              <Select defaultValue="immediate">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="immediate">Inmediato</SelectItem>
                  <SelectItem value="daily">Diario</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="dashboard-frequency">Dashboard</Label>
              <Select defaultValue="realtime">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="realtime">Tiempo Real</SelectItem>
                  <SelectItem value="hourly">Cada Hora</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )

  const renderBackupExport = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Download className="w-5 h-5" />
            Exportar Datos
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Button variant="outline" className="h-20 flex flex-col gap-2 bg-transparent">
              <Download className="w-6 h-6" />
              <span>Exportar CSV</span>
            </Button>
            <Button variant="outline" className="h-20 flex flex-col gap-2 bg-transparent">
              <Download className="w-6 h-6" />
              <span>Exportar Excel</span>
            </Button>
            <Button variant="outline" className="h-20 flex flex-col gap-2 bg-transparent">
              <Download className="w-6 h-6" />
              <span>Exportar PDF</span>
            </Button>
          </div>
          <div className="bg-yellow-50 p-3 rounded-lg">
            <p className="text-sm text-yellow-800">
              <AlertTriangle className="w-4 h-4 inline mr-1" />
              La exportación puede tardar varios minutos dependiendo del volumen de datos.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            Respaldo Automático
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Respaldo Automático</p>
              <p className="text-sm text-gray-600">Crear copias de seguridad automáticamente</p>
            </div>
            <Switch defaultChecked={true} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="backup-frequency">Frecuencia</Label>
              <Select defaultValue="daily">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Diario</SelectItem>
                  <SelectItem value="weekly">Semanal</SelectItem>
                  <SelectItem value="monthly">Mensual</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="backup-time">Hora</Label>
              <Input id="backup-time" type="time" defaultValue="02:00" />
            </div>
          </div>

          <div>
            <Label htmlFor="backup-retention">Retención (días)</Label>
            <Input id="backup-retention" type="number" defaultValue="30" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Historial de Respaldos</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-gray-50">
                <TableHead>Fecha</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Tamaño</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[
                { date: "2024-01-15 02:00", type: "Automático", size: "45.2 MB", status: "Completado" },
                { date: "2024-01-14 02:00", type: "Automático", size: "44.8 MB", status: "Completado" },
                { date: "2024-01-13 14:30", type: "Manual", size: "44.1 MB", status: "Completado" },
                { date: "2024-01-13 02:00", type: "Automático", size: "43.9 MB", status: "Completado" },
              ].map((backup, index) => (
                <TableRow key={index}>
                  <TableCell>{backup.date}</TableCell>
                  <TableCell>
                    <Badge
                      className={
                        backup.type === "Automático"
                          ? "bg-blue-100 text-blue-800 hover:bg-blue-100"
                          : "bg-green-100 text-green-800 hover:bg-green-100"
                      }
                    >
                      {backup.type}
                    </Badge>
                  </TableCell>
                  <TableCell>{backup.size}</TableCell>
                  <TableCell>
                    <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      {backup.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm">
                        <Download className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        Restaurar
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )

  return (
    <div className="flex h-full bg-gray-50">
      {/* Sidebar */}
      <div className="w-80 bg-gray-900 text-white flex flex-col">
        <div className="p-6">
          <h1 className="text-xl font-bold text-blue-400">Configuración</h1>
          <p className="text-sm text-gray-400 mt-1">Gestiona tu cuenta y preferencias</p>
        </div>

        <nav className="flex-1 px-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-2 text-left transition-colors ${
                activeTab === tab.id ? "bg-blue-600 text-white" : "text-gray-300 hover:bg-gray-800 hover:text-white"
              }`}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="p-4">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${autoSave ? "bg-green-500" : "bg-gray-500"}`}></div>
              <span>{autoSave ? "Guardado automático activado" : "Guardado manual"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Content Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-800">{tabs.find((tab) => tab.id === activeTab)?.label}</h2>
              <p className="text-sm text-gray-600 mt-1">
                {activeTab === "company" && "Información básica de tu empresa"}
                {activeTab === "tax" && "Configuración fiscal y tributaria"}
                {activeTab === "integrations" && "Conecta con sistemas externos"}
                {activeTab === "users" && "Gestiona usuarios y permisos"}
                {activeTab === "notifications" && "Configura alertas y notificaciones"}
                {activeTab === "backup" && "Respaldo y exportación de datos"}
              </p>
            </div>
            <Button className="bg-blue-600 hover:bg-blue-700">
              <Save className="w-4 h-4 mr-2" />
              Guardar Cambios
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-6 overflow-auto">
          {activeTab === "company" && renderCompanyProfile()}
          {activeTab === "tax" && renderTaxSettings()}
          {activeTab === "integrations" && renderIntegrations()}
          {activeTab === "users" && renderUsersPermissions()}
          {activeTab === "notifications" && renderNotifications()}
          {activeTab === "backup" && renderBackupExport()}
        </div>
      </div>
    </div>
  )
}
