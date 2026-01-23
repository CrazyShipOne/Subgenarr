import apiClient from './client'
import type {
  ApiResponse,
  MediaItem,
  TVShowGrouped,
  TVShowDetail,
  MediaDetail,
  MediaFiles,
  PaginationInfo
} from '@/types/api'

export interface MediaListResponse {
  items: MediaItem[]
  pagination: PaginationInfo
}

export interface TVShowGroupedResponse {
  items: TVShowGrouped[]
  pagination: PaginationInfo
}

export const mediaApi = {
  async getMovies(params: {
    page?: number
    page_size?: number
    search?: string
    year?: number
    has_subtitle?: boolean
  }): Promise<ApiResponse<MediaListResponse>> {
    const response = await apiClient.get('/media/movies', { params })
    return response.data
  },

  async getTVShows(params: {
    page?: number
    page_size?: number
    search?: string
    year?: number
    season?: number
  }): Promise<ApiResponse<MediaListResponse>> {
    const response = await apiClient.get('/media/tvshows', { params })
    return response.data
  },

  async getTVShowsGrouped(params: {
    page?: number
    page_size?: number
    search?: string
    year?: number
  }): Promise<ApiResponse<TVShowGroupedResponse>> {
    const response = await apiClient.get('/media/tvshows/grouped', { params })
    return response.data
  },

  async getTVShowDetail(showTitle: string): Promise<ApiResponse<TVShowDetail>> {
    const response = await apiClient.get(`/media/tvshows/detail/${encodeURIComponent(showTitle)}`)
    return response.data
  },

  async getMediaDetail(mediaId: number): Promise<ApiResponse<MediaDetail>> {
    const response = await apiClient.get(`/media/${mediaId}`)
    return response.data
  },

  async getMediaFiles(mediaId: number): Promise<ApiResponse<MediaFiles>> {
    const response = await apiClient.get(`/media/${mediaId}/files`)
    return response.data
  },

  getPosterUrl(mediaId: number): string {
    return `/api/media/${mediaId}/poster`
  }
}
