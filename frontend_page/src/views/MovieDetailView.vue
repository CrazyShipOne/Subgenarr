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
    <div v-else-if="media">
      <!-- Header Section with Poster -->
      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex flex-col md:flex-row gap-6">
          <!-- Poster -->
          <div class="w-full md:w-64 flex-shrink-0">
            <div class="aspect-[2/3] bg-gray-200 rounded-lg overflow-hidden">
              <img
                v-if="media.has_poster"
                :src="getPosterUrl(media.media_id)"
                :alt="media.title"
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
            <h1 class="text-3xl font-bold text-gray-900">{{ media.title }}</h1>
            <p class="text-lg text-gray-600 mt-2">{{ media.year }}</p>

            <!-- Status Badge -->
            <div class="mt-4">
              <span
                :class="[
                  'px-3 py-1 inline-flex text-sm font-semibold rounded-full',
                  getStatusColor(media.processing_status)
                ]"
              >
                {{ t(`status.${media.processing_status}`) }}
              </span>
            </div>

            <!-- Overview -->
            <div v-if="media.overview" class="mt-4">
              <h3 class="text-sm font-semibold text-gray-700 uppercase">{{ t('media.overview') }}</h3>
              <p class="mt-2 text-gray-700 leading-relaxed">{{ media.overview }}</p>
            </div>

            <!-- Cast -->
            <div v-if="media.cast && media.cast.length > 0" class="mt-4">
              <h3 class="text-sm font-semibold text-gray-700 uppercase">{{ t('media.cast') }}</h3>
              <p class="mt-2 text-gray-700">{{ media.cast.join(', ') }}</p>
            </div>

            <!-- Generate Subtitle Button -->
            <div v-if="!media.subtitle_file_path && media.processing_status === 'unprocessed'" class="mt-6">
              <button
                @click="triggerProcessing"
                :disabled="triggeringTask"
                class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition"
              >
                <span v-if="triggeringTask">{{ t('common.loading') }}</span>
                <span v-else>{{ t('media.generateSubtitle') }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Files Section -->
      <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-xl font-bold text-gray-900 mb-4">{{ t('media.files') }}</h2>

        <div v-if="filesLoading" class="text-center py-6">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>

        <div v-else-if="files" class="space-y-4">
          <!-- Video File -->
          <div v-if="files.files.video" class="border-b border-gray-200 pb-4">
            <h3 class="text-sm font-semibold text-gray-700 uppercase mb-2">{{ t('media.videoFile') }}</h3>
            <div class="bg-gray-50 rounded p-3">
              <p class="text-sm text-gray-900 font-mono break-all">{{ files.files.video.path }}</p>
              <p class="text-xs text-gray-500 mt-1">
                {{ formatFileSize(files.files.video.size_bytes) }}
              </p>
            </div>
          </div>

          <!-- Generated Subtitle -->
          <div v-if="files.files.generated_subtitle" class="border-b border-gray-200 pb-4">
            <h3 class="text-sm font-semibold text-gray-700 uppercase mb-2">{{ t('media.subtitleFile') }}</h3>
            <div class="bg-gray-50 rounded p-3">
              <p class="text-sm text-gray-900 font-mono break-all">{{ files.files.generated_subtitle.path }}</p>
              <p class="text-xs text-gray-500 mt-1">
                {{ formatFileSize(files.files.generated_subtitle.size_bytes) }}
                <span v-if="files.files.generated_subtitle.language">
                  · {{ files.files.generated_subtitle.language.toUpperCase() }}
                </span>
              </p>
            </div>
          </div>

          <!-- Other Subtitles -->
          <div v-if="files.files.other_subtitles.length > 0">
            <h3 class="text-sm font-semibold text-gray-700 uppercase mb-2">{{ t('media.otherSubtitles') }}</h3>
            <div class="space-y-2">
              <div
                v-for="(subtitle, index) in files.files.other_subtitles"
                :key="index"
                class="bg-gray-50 rounded p-3"
              >
                <p class="text-sm text-gray-900 font-mono break-all">{{ subtitle.path }}</p>
                <p class="text-xs text-gray-500 mt-1">
                  {{ formatFileSize(subtitle.size_bytes) }}
                  <span v-if="subtitle.language">
                    · {{ subtitle.language.toUpperCase() }}
                  </span>
                </p>
              </div>
            </div>
          </div>

          <!-- NFO File -->
          <div v-if="files.files.nfo">
            <h3 class="text-sm font-semibold text-gray-700 uppercase mb-2">{{ t('media.nfoFile') }}</h3>
            <div class="bg-gray-50 rounded p-3">
              <p class="text-sm text-gray-900 font-mono break-all">{{ files.files.nfo.path }}</p>
              <p class="text-xs text-gray-500 mt-1">
                {{ formatFileSize(files.files.nfo.size_bytes) }}
              </p>
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
import type { MediaDetail, MediaFiles } from '@/types/api'

const { t } = useI18n()
const route = useRoute()

const media = ref<MediaDetail | null>(null)
const files = ref<MediaFiles | null>(null)
const loading = ref(false)
const filesLoading = ref(false)
const error = ref<string | null>(null)
const triggeringTask = ref(false)

async function loadMedia() {
  loading.value = true
  error.value = null

  try {
    const mediaId = parseInt(route.params.mediaId as string)
    const response = await mediaApi.getMediaDetail(mediaId)

    if (response.success && response.data) {
      media.value = response.data
      loadFiles(mediaId)
    } else {
      error.value = response.error || 'Failed to load media details'
    }
  } catch (err: any) {
    error.value = err.message || 'Failed to load media details'
  } finally {
    loading.value = false
  }
}

async function loadFiles(mediaId: number) {
  filesLoading.value = true

  try {
    const response = await mediaApi.getMediaFiles(mediaId)

    if (response.success && response.data) {
      files.value = response.data
    }
  } catch (err) {
    console.error('Failed to load files:', err)
  } finally {
    filesLoading.value = false
  }
}

async function triggerProcessing() {
  if (!media.value) return

  triggeringTask.value = true

  try {
    const response = await tasksApi.triggerTask(media.value.media_id)

    if (response.success) {
      // Reload media to update status
      await loadMedia()
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

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

onMounted(() => {
  loadMedia()
})
</script>
