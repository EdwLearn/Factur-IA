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
  },

  // Proxy: el browser llama /api/v1/... → Next.js reenvía al backend (sin CORS)
  async rewrites() {
    const backendUrl = process.env.API_URL || 'http://localhost:8001'
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ]
  },
}

export default nextConfig
