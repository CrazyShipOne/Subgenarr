<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold text-gray-800">{{ t('nav.tvShows') }}</h1>

      <!-- View Toggle -->
      <div class="flex space-x-2">
        <button
          @click="viewMode = 'grid'"
          :class="[
            'px-4 py-2 rounded',
            viewMode === 'grid' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          ]"
        >
          {{ t('media.gridView') }}
        </button>
        <button
          @click="viewMode = 'list'"
          :class="[
            'px-4 py-2 rounded',
            viewMode === 'list' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          ]"
        >
          {{ t('media.listView') }}
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white p-4 rounded-lg shadow space-y-4">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Search -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('common.search') }}</label>
          <input
            v-model="filters.search"
            type="text"
            :placeholder="t('media.title')"
            class="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            @input="debouncedSearch"
          />
        </div>

        <!-- Year Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('media.year') }}</label>
          <input
            v-model.number="filters.year"
            type="number"
            placeholder="YYYY"
            class="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            @change="loadTVShows"
          />
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      <p class="mt-4 text-gray-600">{{ t('common.loading') }}</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
      {{ error }}
    </div>

    <!-- Grid View -->
    <div v-else-if="viewMode === 'grid'" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
      <div
        v-for="show in tvShows"
        :key="show.media_id"
        class="bg-white rounded-lg shadow hover:shadow-lg transition cursor-pointer overflow-hidden"
        @click="goToDetail(show.media_id)"
      >
        <!-- Poster -->
        <div class="aspect-[2/3] bg-gray-200 relative">
          <img
            v-if="show.has_poster"
            :src="getPosterUrl(show.media_id)"
            :alt="show.title"
            class="w-full h-full object-cover"
            @error="handleImageError"
          />
          <div v-else class="w-full h-full flex items-center justify-center">
            <svg class="w-16 h-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
            </svg>
          </div>
        </div>

        <!-- Info -->
        <div class="p-4">
          <h3 class="font-semibold text-gray-900 truncate" :title="show.title">
            {{ show.title }}
          </h3>
          <p class="text-sm text-gray-600 mt-1">{{ show.year }}</p>
          <p class="text-xs text-gray-500 mt-2">
            {{ show.season_count }} {{ t('media.seasonCount') }} ·
            {{ show.episode_count }} {{ t('media.episodeCount') }}
          </p>
        </div>
      </div>
    </div>

    <!-- List View -->
    <div v-else class="bg-white rounded-lg shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('media.title') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('media.year') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('media.seasonCount') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('media.episodeCount') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {{ t('common.actions') }}
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="show in tvShows"
            :key="show.media_id"
            class="hover:bg-gray-50 cursor-pointer"
            @click="goToDetail(show.media_id)"
          >
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="flex items-center">
                <div class="w-12 h-16 flex-shrink-0 bg-gray-200 rounded overflow-hidden">
                  <img
                    v-if="show.has_poster"
                    :src="getPosterUrl(show.media_id)"
                    :alt="show.title"
                    class="w-full h-full object-cover"
                    @error="handleImageError"
                  />
                </div>
                <div class="ml-4">
                  <div class="text-sm font-medium text-gray-900">{{ show.title }}</div>
                </div>
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ show.year }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ show.season_count }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ show.episode_count }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              <button
                class="text-blue-600 hover:text-blue-900"
                @click.stop="goToDetail(show.media_id)"
              >
                {{ t('common.view') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && !error && tvShows.length === 0" class="text-center py-12">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
      </svg>
      <p class="mt-4 text-gray-600">{{ t('common.noData') }}</p>
    </div>

    <!-- Pagination -->
    <div v-if="!loading && tvShows.length > 0" class="flex justify-between items-center">
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
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { mediaApi } from '@/api/media'
import type { TVShowGrouped, PaginationInfo } from '@/types/api'

const { t } = useI18n()
const router = useRouter()

const viewMode = ref<'grid' | 'list'>('grid')
const tvShows = ref<TVShowGrouped[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const filters = ref({
  search: '',
  year: undefined as number | undefined
})

const pagination = ref<PaginationInfo>({
  page: 1,
  page_size: 20,
  total_items: 0,
  total_pages: 0
})

let searchTimeout: NodeJS.Timeout

async function loadTVShows() {
  loading.value = true
  error.value = null

  try {
    const response = await mediaApi.getTVShowsGrouped({
      page: pagination.value.page,
      page_size: pagination.value.page_size,
      search: filters.value.search || undefined,
      year: filters.value.year
    })

    if (response.success && response.data) {
      tvShows.value = response.data.items
      pagination.value = response.data.pagination
    } else {
      error.value = response.error || 'Failed to load TV shows'
    }
  } catch (err: any) {
    error.value = err.message || 'Failed to load TV shows'
  } finally {
    loading.value = false
  }
}

function debouncedSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    pagination.value.page = 1
    loadTVShows()
  }, 500)
}

function goToPage(page: number) {
  pagination.value.page = page
  loadTVShows()
}

function goToDetail(mediaId: number) {
  router.push({ name: 'tvshow-detail', params: { mediaId } })
}

function getPosterUrl(mediaId: number): string {
  return mediaApi.getPosterUrl(mediaId)
}

function handleImageError(event: Event) {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

onMounted(() => {
  loadTVShows()
})
</script>
