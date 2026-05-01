import { apiClient } from '../client'

export interface LoginRequest {
  tenant_id: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  tenant_id: string
  company_name: string
}

export interface RegisterRequest {
  company_name: string
  email: string
  password: string
  nit?: string
  invitation_code?: string
}

export interface InviteValidationResponse {
  valid: boolean
  plan: string
  duration_days: number
  message: string
}

export function generateTenantId(companyName: string): string {
  return companyName
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .substring(0, 50)
}

export async function validateInviteCode(code: string): Promise<InviteValidationResponse> {
  const raw = await apiClient.get<InviteValidationResponse>(
    `/auth/validate-invite?code=${encodeURIComponent(code)}`
  ) as any
  if (raw.success === false) {
    throw new Error(raw.error?.message || 'Código inválido')
  }
  const response: InviteValidationResponse = raw.data
  if (!response?.valid) {
    throw new Error('Código inválido')
  }
  return response
}

export async function register(data: RegisterRequest): Promise<LoginResponse> {
  const tenant_id = generateTenantId(data.company_name)
  const raw = await apiClient.post<LoginResponse>('/auth/register', {
    tenant_id,
    company_name: data.company_name,
    email: data.email,
    password: data.password,
    nit: data.nit || undefined,
    plan: 'freemium',
    invitation_code: data.invitation_code || undefined,
  }) as any

  if (raw.success === false) {
    throw new Error(raw.error?.message || 'Error al crear la cuenta')
  }

  const response: LoginResponse = raw.access_token ? raw : raw.data
  if (!response?.access_token) {
    throw new Error('Error al crear la cuenta')
  }

  localStorage.setItem('auth_token', response.access_token)
  localStorage.setItem('tenant_id', response.tenant_id)
  localStorage.setItem('company_name', response.company_name)
  apiClient.setTenantId(response.tenant_id)

  return response
}

export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  // El endpoint /auth/login devuelve el token directamente (no envuelto en {success, data})
  const raw = await apiClient.post<LoginResponse>('/auth/login', credentials) as any

  // Si el cliente detectó un error de red o HTTP
  if (raw.success === false) {
    throw new Error(raw.error?.message || 'Credenciales inválidas')
  }

  // Puede venir como raw.access_token (respuesta directa) o raw.data.access_token (envuelta)
  const data: LoginResponse = raw.access_token ? raw : raw.data
  if (!data?.access_token) {
    throw new Error('Credenciales inválidas')
  }

  // Persist session
  localStorage.setItem('auth_token', data.access_token)
  localStorage.setItem('tenant_id', data.tenant_id)
  localStorage.setItem('company_name', data.company_name)
  apiClient.setTenantId(data.tenant_id)

  return data
}

export function logout() {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('tenant_id')
  localStorage.removeItem('company_name')
}

export function getStoredTenantId(): string | null {
  return typeof window !== 'undefined' ? localStorage.getItem('tenant_id') : null
}

export function isAuthenticated(): boolean {
  return typeof window !== 'undefined' && !!localStorage.getItem('auth_token')
}
