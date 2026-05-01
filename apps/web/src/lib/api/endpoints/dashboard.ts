/**
 * Dashboard API endpoints
 */

import { apiClient, ApiResponse } from '../client'

export interface DashboardMetrics {
  total_invoices_month: number
  total_inventory_value: number
  pending_alerts: number
  total_suppliers: number
  total_products: number
  month_over_month_invoices: number
  month_over_month_inventory: number
  avg_margin: number | null
}

export interface RecentInvoice {
  id: string
  supplier_name: string
  status: string
  total: number
  items_count: number
  upload_timestamp: string
  processing_duration_seconds?: number
}

export interface PurchaseVolumeData {
  period: string
  volume: number
}

export interface MarginTrendData {
  month: string
  margin: number
}

export interface InventoryProjectionData {
  product: string
  current: number
  projected: number
}

export interface ComparisonMetrics {
  invoices_processed: number
  invoices_change: number
  total_revenue: number
  revenue_change: number
  new_products: number
  products_change: number
  avg_processing_time_minutes: number
  time_change: number
}

export interface AnalyticsData {
  purchase_volume: PurchaseVolumeData[]
  margin_trend: MarginTrendData[]
  inventory_projection: InventoryProjectionData[]
  comparison_metrics: ComparisonMetrics
}

export interface MonthlyInvoiceData {
  month: string
  invoices: number
  value: number
}

export interface TopSupplierData {
  name: string
  invoices: number
  volume: number
}

export interface TopProductData {
  product_code: string
  description: string
  quantity: number
  sale_price: number
  cost_price: number
  inventory_value: number
  margin: number | null
}

export interface ReportsData {
  monthly_invoices: MonthlyInvoiceData[]
  top_suppliers: TopSupplierData[]
  top_products: TopProductData[]
}

// ─── New chart types ──────────────────────────────────────────────────────────

export interface TopSupplierItem {
  name: string
  nit: string | null
  total_gasto: number
  num_facturas: number
}

export interface TopSuppliersResponse {
  suppliers: TopSupplierItem[]
}

export interface TopProductItem {
  description: string
  product_code: string | null
  cantidad_total: number
  gasto_total: number
  num_facturas: number
}

export interface TopProductsResponse {
  products: TopProductItem[]
}

export interface PriceEvolutionPoint {
  semana: string
  precio_promedio: number
  precio_min: number
  precio_max: number
  supplier: string | null
}

export interface PriceEvolutionResponse {
  product: string
  evolution: PriceEvolutionPoint[]
}

export interface PriceAlertItem {
  description: string
  product_code: string | null
  precio_actual: number
  precio_anterior: number
  variacion_pct: number
  supplier: string | null
  subio: boolean
}

export interface PriceAlertsResponse {
  alerts: PriceAlertItem[]
}

export interface PurchaseVolumePoint {
  semana: string
  volumen: number
  num_facturas: number
}

export interface PurchaseVolumeResponse {
  data: PurchaseVolumePoint[]
}

// ─── Sales report (Alegra → inventory_movements) ──────────────────────────────

export type SalesPeriod = "current_month" | "last_30_days" | "month_comparison"

export interface SalesKPIs {
  total_revenue: number
  total_units_sold: number
  total_orders: number
  avg_ticket: number
}

export interface RevenuePoint {
  date: string
  revenue: number
  units: number
}

export interface TopSalesProduct {
  name: string
  units_sold: number
  revenue: number
  revenue_pct: number
}

export interface SalesComparison {
  current_month_revenue: number
  previous_month_revenue: number
  change_pct: number
}

export interface SalesReportResponse {
  kpis: SalesKPIs
  revenue_over_time: RevenuePoint[]
  top_products: TopSalesProduct[]
  comparison: SalesComparison | null
}

export const dashboardApi = {
  /**
   * Get dashboard metrics (main stats)
   */
  getMetrics: async (): Promise<DashboardMetrics> => {
    const response = await apiClient.get<DashboardMetrics>('/dashboard/metrics')
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to fetch dashboard metrics')
    }
    return response.data
  },

  /**
   * Get recent invoices
   */
  getRecentInvoices: async (limit: number = 10): Promise<RecentInvoice[]> => {
    const response = await apiClient.get<RecentInvoice[]>(
      `/dashboard/recent-invoices?limit=${limit}`
    )
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to fetch recent invoices')
    }
    return response.data
  },

  /**
   * Get analytics data for charts
   */
  getAnalytics: async (months: number = 8): Promise<AnalyticsData> => {
    const response = await apiClient.get<AnalyticsData>(`/dashboard/analytics?months=${months}`)
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to fetch analytics data')
    }
    return response.data
  },

  /**
   * Get reports data: monthly history, top suppliers, top products
   */
  getReports: async (days: number = 365): Promise<ReportsData> => {
    const response = await apiClient.get<ReportsData>(`/dashboard/reports?days=${days}`)
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to fetch reports data')
    }
    return response.data
  },

  /**
   * Top 5 suppliers by spend this month
   */
  getTopSuppliers: async (): Promise<TopSuppliersResponse> => {
    const response = await apiClient.get<TopSuppliersResponse>('/dashboard/top-suppliers')
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to fetch top suppliers')
    }
    return response.data
  },

  /**
   * Top 8 products by quantity purchased this month
   */
  getTopProducts: async (): Promise<TopProductsResponse> => {
    const response = await apiClient.get<TopProductsResponse>('/dashboard/top-products')
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to fetch top products')
    }
    return response.data
  },

  /**
   * Price evolution for a product over the last 6 months
   */
  getPriceEvolution: async (search: string): Promise<PriceEvolutionResponse> => {
    const response = await apiClient.get<PriceEvolutionResponse>(
      `/dashboard/price-evolution?description=${encodeURIComponent(search)}`
    )
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to fetch price evolution')
    }
    return response.data
  },

  /**
   * Products with >10% price variation vs previous purchase
   */
  getPriceAlerts: async (): Promise<PriceAlertsResponse> => {
    const response = await apiClient.get<PriceAlertsResponse>('/dashboard/price-alerts')
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to fetch price alerts')
    }
    return response.data
  },

  /**
   * Weekly purchase volume for the last 60 days
   */
  getPurchaseVolume: async (): Promise<PurchaseVolumeResponse> => {
    const response = await apiClient.get<PurchaseVolumeResponse>('/dashboard/purchase-volume')
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to fetch purchase volume')
    }
    return response.data
  },

  getSalesReport: async (period: SalesPeriod): Promise<SalesReportResponse> => {
    const response = await apiClient.get<SalesReportResponse>(
      `/dashboard/reports/sales?period=${period}`
    )
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to fetch sales report')
    }
    return response.data
  },
}
