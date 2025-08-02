import type React from "react"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "FacturIA - Automatización de Facturas para Retail Colombiano",
  description:
    "IA + Visión por Computadora para extraer datos de facturas en segundos. Actualiza tu inventario automáticamente. Diseñado para el retail colombiano.",
  keywords: "facturas, automatización, retail, colombia, IA, inventario, POS",
    generator: 'v0.dev'
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        {children}
      </body>
    </html>
  )
}
