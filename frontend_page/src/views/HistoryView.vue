<template>
  <div class="space-y-6">
    <!-- Header -->
    <h1 class="text-3xl font-bold text-gray-900">{{ t('history.title') }}</h1>

    <!-- Statistics Card -->
    <div v-if="stats" class="bg-white rounded-lg shadow p-6">
      <h2 class="text-xl font-bold text-gray-900 mb-4">{{ t('history.stats') }}</h2>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="text-center">
          <div class="text-3xl font-bold text-blue-600">{{ stats.total_processed }}</div>
          <div class="text-sm text-gray-600 mt-1">{{ t('history.totalProcessed') }}</div>
        </div>
        <div class="text-center">
          <div class="text-3xl font-bold text-green-600">{{ stats.successful }}</div>
          <div class="text-sm text-gray-600 mt-1">{{ t('history.successful') }}</div>
        </div>
        <div class="text-center">
          <div class="text-3xl font-bold text-red-600">{{ stats.failed }}</div>
          <div class="text-sm text-gray-600 mt-1">{{ t('history.failed') }}</div>
        </div>
        <div class="text-center">
          <div class="text-3xl font-bold text-purple-600">{{ Math.round(stats.success_rate * 100) }}%</div>
          <div class="text-sm text-gray-600 mt-1">{{ t('history.successRate') }}</div>
        </div>
      </div>

      <div v-if="stats.average_duration_seconds" class="mt-4 text-center">
        <div class="text-lg text-gray-700">
          {{ t('history.averageDuration') }}:
          <span class="font-semibold">{{ formatDuration(stats.average_duration_seconds) }}</span>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white p-4 rounded-lg shadow">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Search -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('common.search') }}</label>
          <input
            v-model="filters.search"
            type="text"
            :placeholder="t('tasks.mediaName')"
            class="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            @input="debouncedSearch"
          />
        </div>

        <!-- Status Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('tasks.status') }}</label>
          <select
            v-model="filters.status"
            class="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            @change="loadHistory"
          >
            <option value="">All</option>
            <option value="success">{{ t('history.successful') }}</option>
            <option value="failed">{{ t('history.failed') }}</option>
          </select>
        </div>

        <!-- Media Type Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('media.type') }}</label>
          <select
            v-model="filters.media_type"
            class="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            @change="loadHistory"
          >
            <option value="">All</option>
            <option value="movie">{{ t('nav.movies') }}</option>
            <option value="tv">{{ t('nav.tvShows') }}</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && history.length === 0" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      <p class="mt-4 text-gray-600">{{ t('common.loading') }}</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
      {{ error }}
    </div>

    <!-- History Table -->
    <div v-else class="bg-white rounded-lg shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('tasks.mediaName') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('tasks.status') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('history.duration') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('tasks.createdTime') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('common.actions') }}
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <template v-for="item in history" :key="item.history_id">
            <!-- Main Row -->
            <tr class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">{{ item.media_title }}</div>
                <div v-if="item.media_type === 'tv' && item.season" class="text-xs text-gray-500">
                  S{{ String(item.season).padStart(2, '0') }}E{{ String(item.episode).padStart(2, '0') }}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="[
                    'px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full',
                    item.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  ]"
                >
                  {{ item.status === 'success' ? t('history.successful') : t('history.failed') }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ item.processing_duration_seconds ? formatDuration(item.processing_duration_seconds) : 'N/A' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ formatDate(item.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button
                  v-if="item.status === 'failed' && (item.failure_reason || item.error_details)"
                  @click="toggleDetails(item.history_id)"
                  class="text-blue-600 hover:text-blue-900"
                >
                  {{ expandedItems.has(item.history_id) ? t('history.hideDetails') : t('history.showDetails') }}
                </button>
              </td>
            </tr>

            <!-- Expanded Error Details Row -->
            <tr v-if="expandedItems.has(item.history_id)" class="bg-gray-50">
              <td colspan="5" class="px-6 py-4">
                <div class="text-sm">
                  <div v-if="item.failure_reason" class="mb-2">
                    <span class="font-semibold text-gray-700">{{ t('tasks.failureReason') }}:</span>
                    <span class="ml-2 text-red-600">{{ item.failure_reason }}</span>
                  </div>
                  <div v-if="item.error_details">
                    <span class="font-semibold text-gray-700">{{ t('history.errorDetails') }}:</span>
                    <pre class="mt-2 p-3 bg-white border border-gray-300 rounded text-xs overflow-x-auto">{{ item.error_details }}</pre>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <!-- Empty State -->
      <div v-if="history.length === 0" class="text-center py-12">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p class="mt-4 text-gray-600">{{ t('common.noData') }}</p>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="!loading && history.length > 0" class="flex justify-between items-center">
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
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { historyApi } from '@/api/history'
import type { HistoryItem, HistoryStats, PaginationInfo } from '@/types/api'

const { t } = useI18n()

const history = ref<HistoryItem[]>([])
const stats = ref<HistoryStats | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const expandedItems = ref<Set<number>>(new Set())

const filters = ref({
  search: '',
  status: '',
  media_type: ''
})

const pagination = ref<PaginationInfo>({
  page: 1,
  page_size: 20,
  total_items: 0,
  total_pages: 0
})

let searchTimeout: NodeJS.Timeout

async function loadHistory() {
  loading.value = true
  error.value = null

  try {
    const response = await historyApi.getHistory({
      page: pagination.value.page,
      page_size: pagination.value.page_size,
      search: filters.value.search || undefined,
      status: filters.value.status || undefined,
      media_type: filters.value.media_type || undefined
    })

    if (response.success && response.data) {
      history.value = response.data.items
      pagination.value = response.data.pagination
    } else {
      error.value = response.error || 'Failed to load history'
    }
  } catch (err: any) {
    error.value = err.message || 'Failed to load history'
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const response = await historyApi.getStats()

    if (response.success && response.data) {
      stats.value = response.data
    }
  } catch (err) {
    console.error('Failed to load stats:', err)
  }
}

function debouncedSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    pagination.value.page = 1
    loadHistory()
  }, 500)
}

function goToPage(page: number) {
  pagination.value.page = page
  loadHistory()
}

function toggleDetails(historyId: number) {
  if (expandedItems.value.has(historyId)) {
    expandedItems.value.delete(historyId)
  } else {
    expandedItems.value.add(historyId)
  }
}

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`
  } else {
    return `${secs}s`
  }
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString()
}

onMounted(() => {
  loadStats()
  loadHistory()
})
</script>
