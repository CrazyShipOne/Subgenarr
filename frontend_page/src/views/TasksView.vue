<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold text-gray-900">{{ t('tasks.title') }}</h1>
      <div class="text-sm text-gray-600">
        {{ t('tasks.autoRefresh') }}
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white p-4 rounded-lg shadow">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Status Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('tasks.status') }}</label>
          <select
            v-model="filters.status"
            class="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            @change="loadTasks"
          >
            <option value="">All</option>
            <option value="pending">{{ t('status.pending') }}</option>
            <option value="metadata_fetching">Metadata Fetching</option>
            <option value="processing">{{ t('status.processing') }}</option>
            <option value="completed">{{ t('status.completed') }}</option>
            <option value="failed">{{ t('status.failed') }}</option>
          </select>
        </div>

        <!-- Media Type Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('media.type') }}</label>
          <select
            v-model="filters.media_type"
            class="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            @change="loadTasks"
          >
            <option value="">All</option>
            <option value="movie">{{ t('nav.movies') }}</option>
            <option value="tv">{{ t('nav.tvShows') }}</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && tasks.length === 0" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      <p class="mt-4 text-gray-600">{{ t('common.loading') }}</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
      {{ error }}
    </div>

    <!-- Tasks Table -->
    <div v-else class="bg-white rounded-lg shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('tasks.taskId') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('tasks.mediaName') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('tasks.status') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('tasks.retryCount') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('tasks.createdTime') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('tasks.actions') }}
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="task in tasks" :key="task.task_id" class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ task.task_id }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm font-medium text-gray-900">{{ task.media_title }}</div>
              <div v-if="task.media_type === 'tv' && task.season" class="text-xs text-gray-500">
                S{{ String(task.season).padStart(2, '0') }}E{{ String(task.episode).padStart(2, '0') }}
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span
                :class="[
                  'px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full',
                  getStatusColor(task.status)
                ]"
              >
                {{ t(`status.${task.status}`) || task.status }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ task.retry_count }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ formatDate(task.created_at) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
              <button
                v-if="task.status === 'failed'"
                @click="retryTask(task.task_id)"
                :disabled="actionLoading"
                class="text-blue-600 hover:text-blue-900 disabled:opacity-50"
              >
                {{ t('tasks.retry') }}
              </button>
              <button
                v-if="['pending', 'metadata_fetching', 'processing'].includes(task.status)"
                @click="cancelTask(task.task_id)"
                :disabled="actionLoading"
                class="text-red-600 hover:text-red-900 disabled:opacity-50"
              >
                {{ t('tasks.cancel') }}
              </button>
              <span v-if="task.failure_reason" class="text-gray-500" :title="task.failure_reason">
                ⚠️
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Empty State -->
      <div v-if="tasks.length === 0" class="text-center py-12">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <p class="mt-4 text-gray-600">{{ t('common.noData') }}</p>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="!loading && tasks.length > 0" class="flex justify-between items-center">
      <div class="text-sm text-gray-700">
        {{ t('common.page') }} {{ pagination.page }} {{ t('common.of') }} {{ pagination.total_pages }}
        ({{ t('common.total') }}: {{ pagination.total_items }} {{ t('common.items') }})
      </div>
      <div class="flex space-x-2">
        <button
          @click="goToPage(pagination.page - 1)"
          :disabled="pagination.page <= 1"
          class="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Previous
        </button>
        <button
          @click="goToPage(pagination.page + 1)"
          :disabled="pagination.page >= pagination.total_pages"
          class="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { tasksApi } from '@/api/tasks'
import type { Task, PaginationInfo } from '@/types/api'

const { t } = useI18n()

const tasks = ref<Task[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const actionLoading = ref(false)

const filters = ref({
  status: '',
  media_type: ''
})

const pagination = ref<PaginationInfo>({
  page: 1,
  page_size: 20,
  total_items: 0,
  total_pages: 0
})

let refreshInterval: NodeJS.Timeout

async function loadTasks() {
  loading.value = true
  error.value = null

  try {
    const response = await tasksApi.getTasks({
      page: pagination.value.page,
      page_size: pagination.value.page_size,
      status: filters.value.status || undefined,
      media_type: filters.value.media_type || undefined
    })

    if (response.success && response.data) {
      tasks.value = response.data.items
      pagination.value = response.data.pagination
    } else {
      error.value = response.error || 'Failed to load tasks'
    }
  } catch (err: any) {
    error.value = err.message || 'Failed to load tasks'
  } finally {
    loading.value = false
  }
}

async function retryTask(taskId: number) {
  actionLoading.value = true

  try {
    const response = await tasksApi.retryTask(taskId)

    if (response.success) {
      await loadTasks()
    } else {
      alert(response.error || 'Failed to retry task')
    }
  } catch (err: any) {
    alert(err.response?.data?.error || 'Failed to retry task')
  } finally {
    actionLoading.value = false
  }
}

async function cancelTask(taskId: number) {
  if (!confirm('Are you sure you want to cancel this task?')) {
    return
  }

  actionLoading.value = true

  try {
    const response = await tasksApi.cancelTask(taskId)

    if (response.success) {
      await loadTasks()
    } else {
      alert(response.error || 'Failed to cancel task')
    }
  } catch (err: any) {
    alert(err.response?.data?.error || 'Failed to cancel task')
  } finally {
    actionLoading.value = false
  }
}

function goToPage(page: number) {
  pagination.value.page = page
  loadTasks()
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    completed: 'bg-green-100 text-green-800',
    processing: 'bg-blue-100 text-blue-800',
    metadata_fetching: 'bg-blue-100 text-blue-800',
    pending: 'bg-yellow-100 text-yellow-800',
    failed: 'bg-red-100 text-red-800'
  }
  return colors[status] || 'bg-gray-100 text-gray-800'
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString()
}

onMounted(() => {
  loadTasks()
  // Auto-refresh every 30 seconds
  refreshInterval = setInterval(() => {
    loadTasks()
  }, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>
