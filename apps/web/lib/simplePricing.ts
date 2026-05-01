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

/**
 * Redondeo psicológico de precios para retail colombiano.
 * - precio < 4,000  → sin redondeo (entero exacto)
 * - precio >= 4,000 → ceil al múltiplo de 1,000 más cercano hacia arriba
 */
export function roundRetailPrice(price: number): number {
  if (price < 4000) return Math.round(price)
  return Math.ceil(price / 1000) * 1000
}

export function calculatePrice(cost: number, markup: number = DEFAULT_MARKUP): { finalPrice: number } {
  return { finalPrice: roundRetailPrice(cost * (1 + markup / 100)) }
}

export function formatPrice(price: number): string {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
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
