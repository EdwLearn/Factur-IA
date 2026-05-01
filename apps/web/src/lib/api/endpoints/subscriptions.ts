import { apiClient } from '../client'

// ---------------------------------------------------------------------------
// Types (mirror del backend)
// ---------------------------------------------------------------------------

export interface PlanDetails {
  name: string
  display_name: string
  price_cop: number
  invoice_limit: number | null   // null = ilimitado
  supplier_limit: number | null
  history_days: number | null
  max_users: number
  can_export: boolean
  can_inventory: boolean
  can_alerts: boolean
  support_level: 'email' | 'email_priority' | 'chat_email'
}

export interface CurrentSubscription {
  tenant_id: string
  plan: string
  plan_details: PlanDetails
  billing_period_start: string | null
}

export interface UsageInfo {
  invoice_count: number
  invoice_limit: number | null
  days_until_reset: number
  plan: string
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

export async function getPlans(): Promise<PlanDetails[]> {
  const res = await apiClient.request<PlanDetails[]>('/subscriptions/plans')
  if (!res.success) throw new Error('No se pudieron cargar los planes')
  return res.data as PlanDetails[]
}

export async function getCurrentSubscription(): Promise<CurrentSubscription> {
  const res = await apiClient.request<CurrentSubscription>('/subscriptions/current')
  if (!res.success) throw new Error('No se pudo obtener la suscripción actual')
  return res.data as CurrentSubscription
}

export async function getUsage(): Promise<UsageInfo> {
  const res = await apiClient.request<UsageInfo>('/subscriptions/usage')
  if (!res.success) throw new Error('No se pudo obtener el uso')
  return res.data as UsageInfo
}

export async function upgradePlan(newPlan: string): Promise<void> {
  const res = await apiClient.post('/subscriptions/upgrade', { new_plan: newPlan })
  if (!res.success) {
    throw new Error((res as any).detail || 'No se pudo actualizar el plan')
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function formatPriceCOP(amount: number): string {
  if (amount === 0) return 'Gratis'
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
  }).format(amount)
}

export function usagePercent(usage: UsageInfo): number {
  if (usage.invoice_limit === null) return 0
  return Math.min(100, Math.round((usage.invoice_count / usage.invoice_limit) * 100))
}

export const PLAN_LABELS: Record<string, string> = {
  freemium: 'Freemium',
  basic: 'Básico',
  pro: 'Pro',
}

export const PLAN_COLORS: Record<string, string> = {
  freemium: 'bg-gray-200 text-gray-800',
  basic: 'bg-blue-500 text-white',
  pro: 'bg-purple-600 text-white',
}
