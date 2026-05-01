/**
 * FacturIA API Client
 * Wrapper around the main API client for backward compatibility
 */

import { apiClient } from '../../src/lib/api/client'
import { invoicesApi } from '../../src/lib/api/endpoints/invoices'
import { dashboardApi } from '../../src/lib/api/endpoints/dashboard'

export const facturaAPI = {
  // Invoice operations
  uploadInvoice: invoicesApi.uploadInvoice,
  uploadPhoto: invoicesApi.uploadPhoto,
  uploadMultipage: invoicesApi.uploadMultipage,
  mergeInvoices: invoicesApi.mergeInvoices,
  getInvoiceStatus: invoicesApi.getStatus,
  getInvoiceData: invoicesApi.getData,
  getPricingData: invoicesApi.getPricingData,
  getPricingInfo: invoicesApi.getPricingData, // alias
  setPricing: invoicesApi.setPricing,
  confirmPricing: invoicesApi.confirmPricing,

  // List operations — acepta (limit, offset) o ({ limit, offset })
  listInvoices: async (limitOrParams?: number | { page?: number; limit?: number; status?: string }, offset?: number) => {
    let params: { limit?: number; offset?: number; status?: string } = {}
    if (typeof limitOrParams === 'number') {
      params = { limit: limitOrParams, offset: offset ?? 0 }
    } else if (limitOrParams && typeof limitOrParams === 'object') {
      params = { limit: limitOrParams.limit, offset: limitOrParams.page, status: limitOrParams.status }
    }
    const query = new URLSearchParams(params as any).toString()
    return apiClient.get(`/invoices/${query ? `?${query}` : ''}`)
  },
  deleteInvoice: invoicesApi.delete,
  getDownloadUrl: async (invoiceId: string) => {
    return apiClient.get<{ url: string; filename: string }>(`/invoices/${invoiceId}/download`)
  },

  // Inventory operations
  listProducts: async (params?: { limit?: number; offset?: number; search?: string; stock_status?: string }) => {
    const filteredParams = Object.fromEntries(
      Object.entries(params || {}).filter(([_, v]) => v != null && v !== '')
    )
    const query = new URLSearchParams(filteredParams as any).toString()
    return apiClient.get(`/inventory/products${query ? `?${query}` : ''}`)
  },
  getInventoryStats: async () => {
    return apiClient.get('/inventory/stats')
  },
  updateProduct: async (productId: string, data: Record<string, unknown>) => {
    return apiClient.put(`/inventory/products/${productId}`, data)
  },
  getProductMovements: async (productId: string, limit = 50) => {
    return apiClient.get(`/inventory/movements?product_id=${productId}&limit=${limit}`)
  },

  // Suppliers
  getSupplierInvoices: async (nit: string, limit = 100) => {
    return apiClient.get(`/suppliers/${encodeURIComponent(nit)}/invoices?limit=${limit}`)
  },
  updateSupplier: async (nit: string, data: Record<string, unknown>) => {
    return apiClient.put(`/suppliers/${encodeURIComponent(nit)}`, data)
  },
  getSuppliers: async (params?: { search?: string; city?: string; status?: string }) => {
    const filteredParams = Object.fromEntries(
      Object.entries(params || {}).filter(([, v]) => v != null && v !== '' && v !== 'all')
    )
    const query = new URLSearchParams(filteredParams as any).toString()
    const response = await apiClient.get(`/suppliers${query ? `?${query}` : ''}`)
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to fetch suppliers')
    }
    return response.data as {
      suppliers: Array<{
        id: string
        name: string
        vatNumber: string
        email?: string | null
        phone?: string | null
        city?: string | null
        address?: string | null
        status: 'active' | 'inactive'
        totalInvoices: number
        totalAmount: number
        lastInvoiceDate?: string | null
        joinDate: string
      }>
      total: number
      metrics: {
        total_suppliers: number
        active_suppliers: number
        new_this_month: number
      }
    }
  },

  // Dashboard operations
  getDashboardMetrics: dashboardApi.getMetrics,
  getRecentInvoices: dashboardApi.getRecentInvoices,
  getDashboardAnalytics: dashboardApi.getAnalytics,
  getReports: dashboardApi.getReports,
  getTopSuppliers: dashboardApi.getTopSuppliers,
  getTopProducts: dashboardApi.getTopProducts,
  getPriceEvolution: dashboardApi.getPriceEvolution,
  getPriceAlerts: dashboardApi.getPriceAlerts,
  getPurchaseVolume: dashboardApi.getPurchaseVolume,
  getSalesReport: dashboardApi.getSalesReport,

  // Inventory rotation
  syncSales: async (dateStart?: string) => {
    return apiClient.post('/inventory/sync-sales', { date_start: dateStart ?? null })
  },
  getInventoryRotation: async (days = 30) => {
    return apiClient.get(`/inventory/rotation?days=${days}`)
  },

  // Recommendations
  getRecommendations: async () => {
    return apiClient.get('/recommendations/')
  },

  // Configuration
  setTenantId: (tenantId: string) => apiClient.setTenantId(tenantId),
}

export default facturaAPI
