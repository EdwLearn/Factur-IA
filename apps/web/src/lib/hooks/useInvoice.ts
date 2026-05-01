/**
 * Custom hook for invoice operations
 */

import { useState, useCallback } from 'react'
import { invoicesApi } from '@/lib/api/endpoints/invoices'
import type {
  Invoice,
  InvoiceUploadResponse,
  InvoiceStatusResponse,
  InvoicePricingData,
} from '@facturia/shared-types'

export function useInvoice() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const uploadInvoice = useCallback(async (file: File) => {
    setLoading(true)
    setError(null)

    try {
      const response = await invoicesApi.uploadInvoice(file)

      if (!response.success) {
        setError(response.error?.message || 'Upload failed')
        return null
      }

      return response.data
    } catch (err) {
      setError('An unexpected error occurred')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const uploadPhoto = useCallback(async (file: File) => {
    setLoading(true)
    setError(null)

    try {
      const response = await invoicesApi.uploadPhoto(file)

      if (!response.success) {
        setError(response.error?.message || 'Upload failed')
        return null
      }

      return response.data
    } catch (err) {
      setError('An unexpected error occurred')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const getStatus = useCallback(async (invoiceId: string) => {
    setLoading(true)
    setError(null)

    try {
      const response = await invoicesApi.getStatus(invoiceId)

      if (!response.success) {
        setError(response.error?.message || 'Failed to get status')
        return null
      }

      return response.data
    } catch (err) {
      setError('An unexpected error occurred')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const getPricingData = useCallback(async (invoiceId: string) => {
    setLoading(true)
    setError(null)

    try {
      const response = await invoicesApi.getPricingData(invoiceId)

      if (!response.success) {
        setError(response.error?.message || 'Failed to get pricing data')
        return null
      }

      return response.data
    } catch (err) {
      setError('An unexpected error occurred')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const setPricing = useCallback(
    async (invoiceId: string, lineItems: Array<{ id: string; salePrice: number }>) => {
      setLoading(true)
      setError(null)

      try {
        const response = await invoicesApi.setPricing(invoiceId, { lineItems })

        if (!response.success) {
          setError(response.error?.message || 'Failed to set pricing')
          return false
        }

        return true
      } catch (err) {
        setError('An unexpected error occurred')
        return false
      } finally {
        setLoading(false)
      }
    },
    []
  )

  const confirmPricing = useCallback(async (invoiceId: string) => {
    setLoading(true)
    setError(null)

    try {
      const response = await invoicesApi.confirmPricing(invoiceId)

      if (!response.success) {
        setError(response.error?.message || 'Failed to confirm pricing')
        return false
      }

      return true
    } catch (err) {
      setError('An unexpected error occurred')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    loading,
    error,
    uploadInvoice,
    uploadPhoto,
    getStatus,
    getPricingData,
    setPricing,
    confirmPricing,
  }
}
