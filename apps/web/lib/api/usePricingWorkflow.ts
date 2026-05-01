/**
 * Pricing workflow hook
 */

import { useState, useCallback } from 'react'
import { useInvoice } from '../../src/lib/hooks/useInvoice'
import type { InvoicePricingData } from '@facturia/shared-types'

export interface PricingWorkflowState {
  loading: boolean
  error: string | null
  pricingData: InvoicePricingData | null
}

export function usePricingWorkflow() {
  const { loading, error, getPricingData, setPricing, confirmPricing } = useInvoice()
  const [pricingData, setPricingDataState] = useState<InvoicePricingData | null>(null)

  const loadPricingData = useCallback(
    async (invoiceId: string) => {
      const data = await getPricingData(invoiceId)
      if (data) {
        setPricingDataState(data)
      }
      return data
    },
    [getPricingData]
  )

  const updatePricing = useCallback(
    async (invoiceId: string, lineItems: Array<{ id: string; salePrice: number }>) => {
      const success = await setPricing(invoiceId, lineItems)
      if (success) {
        // Reload pricing data
        await loadPricingData(invoiceId)
      }
      return success
    },
    [setPricing, loadPricingData]
  )

  const finalizePricing = useCallback(
    async (invoiceId: string) => {
      return await confirmPricing(invoiceId)
    },
    [confirmPricing]
  )

  return {
    loading,
    error,
    pricingData,
    loadPricingData,
    updatePricing,
    finalizePricing,
  }
}

export default usePricingWorkflow
