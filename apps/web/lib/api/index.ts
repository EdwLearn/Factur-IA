/**
 * API exports
 * TODO: This is a compatibility layer for the old structure
 * Eventually migrate to use src/lib/api instead
 */

export * from './facturaAPI'
export * from './usePricingWorkflow'

// Re-export types
export type {
  InvoiceUploadResponse,
  InvoiceStatusResponse,
  InvoicePricingData,
  Invoice,
  InvoiceLineItem,
} from '@facturia/shared-types'

// Re-export dashboard types
export type {
  DashboardMetrics,
  RecentInvoice,
  AnalyticsData,
  PurchaseVolumeData,
  MarginTrendData,
  InventoryProjectionData,
  ComparisonMetrics,
} from '../../src/lib/api/endpoints/dashboard'
