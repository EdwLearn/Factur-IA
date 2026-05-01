/**
 * API Client for FacturIA Backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1'

export interface ApiError {
  code: string
  message: string
  details?: Record<string, any>
}

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: ApiError
  message?: string
}

class ApiClient {
  private baseUrl: string
  private tenantId: string | null = null

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  setTenantId(tenantId: string) {
    this.tenantId = tenantId
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }

    // Prefer in-memory tenantId, fallback to localStorage on every request
    const tenantId = this.tenantId ?? (typeof window !== 'undefined' ? localStorage.getItem('tenant_id') : null)
    if (tenantId) {
      headers['x-tenant-id'] = tenantId
    }

    // Add auth token if available
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token')
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
    }

    return headers
  }

  async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...this.getHeaders(),
          ...options.headers,
        },
      })

      const data = await response.json()

      if (response.status === 401) {
        // Don't redirect if already on login page (avoids silent loop on wrong credentials)
        const onLoginPage = typeof window !== 'undefined' && window.location.pathname.includes('/login')
        if (!onLoginPage && typeof window !== 'undefined') {
          localStorage.removeItem('auth_token')
          localStorage.removeItem('tenant_id')
          localStorage.removeItem('company_name')
          window.location.href = '/login'
        }
        const errMsg = typeof data?.error === 'string' ? data.error : 'Credenciales inválidas'
        return { success: false, error: { code: 'UNAUTHORIZED', message: errMsg } }
      }

      if (!response.ok) {
        return {
          success: false,
          error: typeof data.error === 'string'
            ? { message: data.error, code: String(data.status_code ?? 'UNKNOWN_ERROR') }
            : data.error || {
                code: 'UNKNOWN_ERROR',
                message: 'An unexpected error occurred',
              },
        }
      }

      return { success: true, data }
    } catch (error) {
      console.error('API request failed:', error)
      return {
        success: false,
        error: {
          code: 'NETWORK_ERROR',
          message: 'Failed to connect to server',
          details: { error: String(error) },
        },
      }
    }
  }

  async get<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async post<T = any>(endpoint: string, body?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  async put<T = any>(endpoint: string, body?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  async delete<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }

  async uploadFile<T = any>(
    endpoint: string,
    file: File,
    additionalData?: Record<string, any>
  ): Promise<ApiResponse<T>> {
    const formData = new FormData()
    formData.append('file', file)

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, String(value))
      })
    }

    const headers: HeadersInit = {}
    const tenantId = this.tenantId ?? (typeof window !== 'undefined' ? localStorage.getItem('tenant_id') : null)
    if (tenantId) {
      headers['x-tenant-id'] = tenantId
    }
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token')
      if (token) headers['Authorization'] = `Bearer ${token}`
    }

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: 'POST',
        headers,
        body: formData,
      })

      const data = await response.json()

      if (response.status === 401) {
        // Don't redirect if already on login page (avoids silent loop on wrong credentials)
        const onLoginPage = typeof window !== 'undefined' && window.location.pathname.includes('/login')
        if (!onLoginPage && typeof window !== 'undefined') {
          localStorage.removeItem('auth_token')
          localStorage.removeItem('tenant_id')
          localStorage.removeItem('company_name')
          window.location.href = '/login'
        }
        const errMsg = typeof data?.error === 'string' ? data.error : 'Credenciales inválidas'
        return { success: false, error: { code: 'UNAUTHORIZED', message: errMsg } }
      }

      if (!response.ok) {
        return {
          success: false,
          error: data.error,
        }
      }

      return { success: true, data }
    } catch (error) {
      return {
        success: false,
        error: {
          code: 'UPLOAD_ERROR',
          message: 'Failed to upload file',
          details: { error: String(error) },
        },
      }
    }
  }
}

export const apiClient = new ApiClient()
