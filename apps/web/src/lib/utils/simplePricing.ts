/**
 * Simple pricing utilities
 * TODO: Move to proper pricing service when refactoring
 */

import { useState, useEffect } from 'react'

export interface MarkupConfig {
  defaultMarkup: number
  categoryMarkups: Record<string, number>
}

const DEFAULT_MARKUP = 35

export function calculatePrice(cost: number, markup: number = DEFAULT_MARKUP): number {
  return cost * (1 + markup / 100)
}

export function formatPrice(price: number): string {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
  }).format(price)
}

export function useMarkupConfig() {
  const [config, setConfig] = useState<MarkupConfig>({
    defaultMarkup: DEFAULT_MARKUP,
    categoryMarkups: {},
  })

  // TODO: Fetch from API when backend is ready
  useEffect(() => {
    // Placeholder
  }, [])

  return config
}
