const BASE = ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(options?.headers as Record<string, string>) }
  const token = localStorage.getItem('token')
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(BASE + path, { ...options, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail || res.statusText)
  }
  return res.json()
}

export const api = {
  me: () => request<any>('/api/auth/me'),
  pipelines: (params?: string) => request<any[]>(`/api/pipelines${params ? '?' + params : ''}`),
  pipeline: (id: string) => request<any>(`/api/pipelines/${id}`),
  createPipeline: (data: any) => request<any>('/api/pipelines', { method: 'POST', body: JSON.stringify(data) }),
  validatePipeline: (id: string) => request<any>(`/api/pipelines/${id}/validate`, { method: 'POST' }),
  runPipeline: (id: string) => request<any>(`/api/pipelines/${id}/run`, { method: 'POST' }),
  jobs: (params?: string) => request<any[]>(`/api/jobs${params ? '?' + params : ''}`),
  job: (id: string) => request<any>(`/api/jobs/${id}`),
  retryJob: (id: string) => request<any>(`/api/jobs/${id}/retry`, { method: 'POST' }),
  quality: (params?: string) => request<any[]>(`/api/quality${params ? '?' + params : ''}`),
  logs: (params?: string) => request<any[]>(`/api/logs${params ? '?' + params : ''}`),
  inferSchema: (data: any) => request<any>('/api/schema/infer', { method: 'POST', body: JSON.stringify(data) }),
  connectors: () => request<any[]>('/api/connectors'),
  detectAnomaly: (data: any) => request<any>('/api/anomaly/detect', { method: 'POST', body: JSON.stringify(data) }),
  health: () => request<any>('/api/health'),
}
