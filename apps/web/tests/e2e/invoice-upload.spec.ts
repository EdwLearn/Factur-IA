import { test, expect } from '@playwright/test'

test.describe('Invoice Upload Flow', () => {
  test('should navigate to invoice page', async ({ page }) => {
    await page.goto('/')

    // Wait for page to load
    await page.waitForLoadState('networkidle')

    // Check if page loaded
    expect(page.url()).toContain('localhost:3000')
  })

  test.skip('should upload and process invoice', async ({ page }) => {
    // TODO: Implement when invoice upload UI is ready
    await page.goto('/invoices')

    // Upload file
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles('tests/fixtures/sample-invoice.pdf')

    // Click upload button
    await page.click('button:has-text("Upload")')

    // Wait for processing
    await expect(page.locator('.status')).toHaveText('Processing', { timeout: 60000 })
    await expect(page.locator('.status')).toHaveText('Completed', { timeout: 120000 })

    // Verify invoice data displayed
    await expect(page.locator('.invoice-number')).toBeVisible()
  })
})
