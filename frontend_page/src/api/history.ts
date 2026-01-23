import apiClient from './client'
import type { ApiResponse, HistoryItem, HistoryStats, PaginationInfo } from '@/types/api'

export interface HistoryListResponse {
  items: HistoryItem[]
  pagination: PaginationInfo
}

export const historyApi = {
  async getHistory(params: {
    page?: number
    page_size?: number
    status?: string
    media_id?: number
    media_type?: string
    search?: string
    date_from?: string
    date_to?: string
  }): Promise<ApiResponse<HistoryListResponse>> {
    const response = await apiClient.get('/history', { params })
    return response.data
  },

  async getStats(params?: {
    date_from?: string
    date_to?: string
  }): Promise<ApiResponse<HistoryStats>> {
    const response = await apiClient.get('/history/stats', { params })
    return response.data
  }
}
