import axios, { type AxiosInstance } from 'axios'
import router from '@/router'

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - redirect to login
      router.push({ name: 'login' })
    }
    return Promise.reject(error)
  }
)

export default apiClient
