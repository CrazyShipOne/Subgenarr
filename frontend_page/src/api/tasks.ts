import apiClient from './client'
import type { ApiResponse, Task, PaginationInfo } from '@/types/api'

export interface TaskListResponse {
  items: Task[]
  pagination: PaginationInfo
}

export const tasksApi = {
  async getTasks(params: {
    page?: number
    page_size?: number
    status?: string
    media_id?: number
    media_type?: string
  }): Promise<ApiResponse<TaskListResponse>> {
    const response = await apiClient.get('/tasks', { params })
    return response.data
  },

  async getTask(taskId: number): Promise<ApiResponse<Task>> {
    const response = await apiClient.get(`/tasks/${taskId}`)
    return response.data
  },

  async retryTask(taskId: number): Promise<ApiResponse<{ task_id: number; status: string; retry_count: number }>> {
    const response = await apiClient.post(`/tasks/${taskId}/retry`)
    return response.data
  },

  async cancelTask(taskId: number): Promise<ApiResponse<{ task_id: number; status: string; failure_reason: string }>> {
    const response = await apiClient.post(`/tasks/${taskId}/cancel`)
    return response.data
  },

  async triggerTask(mediaId: number): Promise<ApiResponse<{ task_id: number; media_id: number; status: string }>> {
    const response = await apiClient.post('/tasks/trigger', { media_id: mediaId })
    return response.data
  }
}
