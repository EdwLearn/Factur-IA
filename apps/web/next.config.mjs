/** @type {import('next').NextConfig} */
const nextConfig = {
  // Tu configuración actual
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  
  // Nuevas configuraciones para Railway
  output: 'standalone',
  
  // Variables de entorno públicas
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '/api/v1'
  }
}

export default nextConfig
