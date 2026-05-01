/**
 * Invoice API endpoints
 */

import { apiClient, ApiResponse } from '../client'
import type {
  Invoice,
  InvoiceUploadResponse,
  InvoiceStatusResponse,
  InvoicePricingData,
  SetPricingRequest,
} from '@facturia/shared-types'

export const invoicesApi = {
  /**
   * Upload invoice (PDF or photo)
   */
  uploadInvoice: async (file: File): Promise<ApiResponse<InvoiceUploadResponse>> => {
    return apiClient.uploadFile('/invoices/upload', file)
  },

  /**
   * Upload photo of invoice (with image enhancement)
   */
  uploadPhoto: async (file: File): Promise<ApiResponse<InvoiceUploadResponse>> => {
    return apiClient.uploadFile('/invoices/upload-photo', file)
  },

  /**
   * Get invoice processing status
   */
  getStatus: async (invoiceId: string): Promise<ApiResponse<InvoiceStatusResponse>> => {
    return apiClient.get(`/invoices/${invoiceId}/status`)
  },

  /**
   * Get invoice data with line items
   */
  getData: async (invoiceId: string): Promise<ApiResponse<Invoice>> => {
    return apiClient.get(`/invoices/${invoiceId}/data`)
  },

  /**
   * Get pricing data for invoice
   */
  getPricingData: async (invoiceId: string): Promise<ApiResponse<InvoicePricingData>> => {
    return apiClient.get(`/invoices/${invoiceId}/pricing`)
  },

  /**
   * Set sale prices for line items
   */
  setPricing: async (
    invoiceId: string,
    data: SetPricingRequest
  ): Promise<ApiResponse<void>> => {
    return apiClient.post(`/invoices/${invoiceId}/pricing`, data)
  },

  /**
   * Confirm pricing and update inventory.
   * Optionally receives edited line items to override Textract-extracted prices.
   */
  confirmPricing: async (
    invoiceId: string,
    data?: { line_items?: unknown[] }
  ): Promise<ApiResponse<void>> => {
    return apiClient.post(`/invoices/${invoiceId}/confirm-pricing`, data)
  },

  /**
   * List invoices for tenant
   */
  list: async (params?: {
    page?: number
    limit?: number
    status?: string
  }): Promise<ApiResponse<Invoice[]>> => {
    const query = new URLSearchParams(params as any).toString()
    return apiClient.get(`/invoices${query ? `?${query}` : ''}`)
  },

  /**
   * Delete invoice
   */
  delete: async (invoiceId: string): Promise<ApiResponse<void>> => {
    return apiClient.delete(`/invoices/${invoiceId}`)
  },

  /**
   * Upload multiple files as pages of the same invoice.
   * Returns parent_invoice_id + per-page status.
   */
  uploadMultipage: async (files: File[]): Promise<ApiResponse<{
    parent_invoice_id: string
    total_pages: number
    pages: Array<{ id: string; page: number; filename: string; status: string }>
    message: string
  }>> => {
    const formData = new FormData()
    for (const file of files) {
      formData.append('files', file)
    }

    const headers: HeadersInit = {}
    const tenantId = typeof window !== 'undefined' ? localStorage.getItem('tenant_id') : null
    if (tenantId) headers['x-tenant-id'] = tenantId
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
    if (token) headers['Authorization'] = `Bearer ${token}`

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1'}/invoices/upload-multipage`,
        { method: 'POST', headers, body: formData }
      )
      const data = await response.json()
      if (!response.ok) return { success: false, error: data.error ?? { code: 'UPLOAD_ERROR', message: data.detail ?? 'Error' } }
      return { success: true, data }
    } catch (error) {
      return { success: false, error: { code: 'NETWORK_ERROR', message: String(error) } }
    }
  },

  /**
   * Merge secondary invoices into a primary one.
   */
  mergeInvoices: async (
    primaryInvoiceId: string,
    secondaryInvoiceIds: string[]
  ): Promise<ApiResponse<{
    message: string
    primary_invoice_id: string
    merged_invoice_ids: string[]
    total_items: number
    new_total_amount: number
    warnings: string[]
  }>> => {
    const headers: HeadersInit = { 'Content-Type': 'application/json' }
    const tenantId = typeof window !== 'undefined' ? localStorage.getItem('tenant_id') : null
    if (tenantId) headers['x-tenant-id'] = tenantId
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
    if (token) headers['Authorization'] = `Bearer ${token}`

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1'}/invoices/merge`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ primary_invoice_id: primaryInvoiceId, secondary_invoice_ids: secondaryInvoiceIds }),
        }
      )
      const data = await response.json()
      if (!response.ok) return { success: false, error: data.error ?? { code: 'MERGE_ERROR', message: data.detail ?? 'Error' } }
      return { success: true, data }
    } catch (error) {
      return { success: false, error: { code: 'NETWORK_ERROR', message: String(error) } }
    }
  },
}
