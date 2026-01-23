import apiClient from './client'
import type { ApiResponse, LoginRequest, User } from '@/types/api'

export const authApi = {
  async login(credentials: LoginRequest): Promise<ApiResponse<{ user: User; message: string }>> {
    const response = await apiClient.post('/auth/login', credentials)
    return response.data
  },

  async logout(): Promise<ApiResponse<{ message: string }>> {
    const response = await apiClient.post('/auth/logout')
    return response.data
  },

  async checkStatus(): Promise<{ authenticated: boolean; user?: User }> {
    const response = await apiClient.get('/auth/status')
    return response.data
  }
}
