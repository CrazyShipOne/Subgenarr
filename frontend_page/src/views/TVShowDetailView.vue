<template>
  <div class="space-y-6">
    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      <p class="mt-4 text-gray-600">{{ t('common.loading') }}</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
      {{ error }}
    </div>

    <!-- Content -->
    <div v-else-if="tvShow">
      <!-- Header Section with Poster -->
      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex flex-col md:flex-row gap-6">
          <!-- Poster -->
          <div class="w-full md:w-64 flex-shrink-0">
            <div class="aspect-[2/3] bg-gray-200 rounded-lg overflow-hidden">
              <img
                v-if="tvShow.has_poster"
                :src="getPosterUrl(tvShow.seasons[0]?.episodes[0]?.media_id || 0)"
                :alt="tvShow.title"
                class="w-full h-full object-cover"
                @error="handleImageError"
              />
              <div v-else class="w-full h-full flex items-center justify-center">
                <svg class="w-24 h-24 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
                </svg>
              </div>
            </div>
          </div>

          <!-- Metadata -->
          <div class="flex-1">
            <h1 class="text-3xl font-bold text-gray-900">{{ tvShow.title }}</h1>
            <p class="text-lg text-gray-600 mt-2">{{ tvShow.year }}</p>

            <!-- Stats -->
            <div class="mt-4 flex items-center space-x-4 text-sm text-gray-600">
              <span>{{ tvShow.season_count }} {{ t('media.seasonCount') }}</span>
              <span>·</span>
              <span>{{ tvShow.episode_count }} {{ t('media.episodeCount') }}</span>
            </div>

            <!-- Overview -->
            <div v-if="tvShow.overview" class="mt-4">
              <h3 class="text-sm font-semibold text-gray-700 uppercase">{{ t('media.overview') }}</h3>
              <p class="mt-2 text-gray-700 leading-relaxed">{{ tvShow.overview }}</p>
            </div>

            <!-- Cast -->
            <div v-if="tvShow.cast && tvShow.cast.length > 0" class="mt-4">
              <h3 class="text-sm font-semibold text-gray-700 uppercase">{{ t('media.cast') }}</h3>
              <p class="mt-2 text-gray-700">{{ tvShow.cast.join(', ') }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Seasons & Episodes -->
      <div class="space-y-4">
        <div
          v-for="season in tvShow.seasons"
          :key="season.season_number"
          class="bg-white rounded-lg shadow overflow-hidden"
        >
          <!-- Season Header -->
          <div
            class="bg-gray-50 px-6 py-4 flex justify-between items-center cursor-pointer hover:bg-gray-100"
            @click="toggleSeason(season.season_number)"
          >
            <h2 class="text-xl font-bold text-gray-900">
              {{ t('media.season') }} {{ season.season_number }}
              <span class="text-sm font-normal text-gray-600 ml-2">
                ({{ season.episodes.length }} {{ t('media.episodeCount') }})
              </span>
            </h2>
            <svg
              :class="['w-6 h-6 text-gray-600 transition-transform', { 'transform rotate-180': expandedSeasons.has(season.season_number) }]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </div>

          <!-- Episodes List -->
          <div v-show="expandedSeasons.has(season.season_number)" class="divide-y divide-gray-200">
            <div
              v-for="episode in season.episodes"
              :key="episode.media_id"
              class="px-6 py-4 hover:bg-gray-50"
            >
              <div class="flex justify-between items-start">
                <div class="flex-1">
                  <div class="flex items-center">
                    <h3 class="text-lg font-semibold text-gray-900">
                      {{ t('media.episode') }} {{ episode.episode_number }}
                    </h3>
                    <span
                      :class="[
                        'ml-3 px-2 py-1 text-xs font-medium rounded-full',
                        getStatusColor(episode.processing_status)
                      ]"
                    >
                      {{ t(`status.${episode.processing_status}`) }}
                    </span>
                  </div>

                  <!-- Episode Overview -->
                  <p v-if="episode.episode_overview" class="mt-2 text-gray-700 text-sm">
                    {{ episode.episode_overview }}
                  </p>

                  <!-- Files -->
                  <div class="mt-3 space-y-1 text-sm">
                    <div class="text-gray-600">
                      <span class="font-medium">{{ t('media.videoFile') }}:</span>
                      <span class="ml-2 font-mono text-xs">{{ getFileName(episode.video_file_path) }}</span>
                    </div>
                    <div v-if="episode.subtitle_file_path" class="text-gray-600">
                      <span class="font-medium">{{ t('media.subtitleFile') }}:</span>
                      <span class="ml-2 font-mono text-xs">{{ getFileName(episode.subtitle_file_path) }}</span>
                    </div>
                  </div>
                </div>

                <!-- Action Button -->
                <div v-if="!episode.subtitle_file_path && episode.processing_status === 'unprocessed'">
                  <button
                    @click="triggerProcessing(episode.media_id)"
                    :disabled="triggeringTask"
                    class="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded transition"
                  >
                    {{ t('media.generateSubtitle') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { mediaApi } from '@/api/media'
import { tasksApi } from '@/api/tasks'
import type { TVShowDetail } from '@/types/api'

const { t } = useI18n()
const route = useRoute()

const tvShow = ref<TVShowDetail | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const triggeringTask = ref(false)
const expandedSeasons = ref<Set<number>>(new Set())

async function loadTVShow() {
  loading.value = true
  error.value = null

  try {
    const showTitle = route.params.showTitle as string
    const response = await mediaApi.getTVShowDetail(showTitle)

    if (response.success && response.data) {
      tvShow.value = response.data
      // Expand first season by default
      if (tvShow.value.seasons.length > 0) {
        expandedSeasons.value.add(tvShow.value.seasons[0].season_number)
      }
    } else {
      error.value = response.error || 'Failed to load TV show details'
    }
  } catch (err: any) {
    error.value = err.message || 'Failed to load TV show details'
  } finally {
    loading.value = false
  }
}

function toggleSeason(seasonNumber: number) {
  if (expandedSeasons.value.has(seasonNumber)) {
    expandedSeasons.value.delete(seasonNumber)
  } else {
    expandedSeasons.value.add(seasonNumber)
  }
}

async function triggerProcessing(mediaId: number) {
  triggeringTask.value = true

  try {
    const response = await tasksApi.triggerTask(mediaId)

    if (response.success) {
      // Reload TV show to update status
      await loadTVShow()
      alert('Subtitle generation task has been queued')
    } else {
      alert(response.error || 'Failed to trigger processing')
    }
  } catch (err: any) {
    alert(err.response?.data?.error || 'Failed to trigger processing')
  } finally {
    triggeringTask.value = false
  }
}

function getPosterUrl(mediaId: number): string {
  return mediaApi.getPosterUrl(mediaId)
}

function handleImageError(event: Event) {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    completed: 'bg-green-100 text-green-800',
    processing: 'bg-blue-100 text-blue-800',
    pending: 'bg-yellow-100 text-yellow-800',
    failed: 'bg-red-100 text-red-800',
    unprocessed: 'bg-gray-100 text-gray-800'
  }
  return colors[status] || colors.unprocessed
}

function getFileName(path: string): string {
  return path.split('/').pop() || path
}

onMounted(() => {
  loadTVShow()
})
</script>
