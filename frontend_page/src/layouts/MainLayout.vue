<template>
  <div class="flex h-screen bg-gray-100">
    <!-- Sidebar -->
    <aside
      :class="[
        'bg-gray-800 text-white transition-all duration-300',
        sidebarOpen ? 'w-64' : 'w-16'
      ]"
    >
      <!-- Logo/Title -->
      <div class="h-16 flex items-center justify-center border-b border-gray-700">
        <h1 v-if="sidebarOpen" class="text-xl font-bold">Subgenarr</h1>
        <span v-else class="text-xl">SG</span>
      </div>

      <!-- Menu Items -->
      <nav class="mt-6">
        <!-- Media Records -->
        <div class="px-4 py-2">
          <div
            class="flex items-center cursor-pointer hover:bg-gray-700 rounded px-3 py-2"
            @click="toggleMediaMenu"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
            </svg>
            <span v-if="sidebarOpen" class="ml-3">{{ t('nav.mediaRecords') }}</span>
          </div>

          <!-- Submenu -->
          <div v-if="sidebarOpen && mediaMenuOpen" class="ml-6 mt-2 space-y-1">
            <router-link
              to="/movies"
              class="flex items-center px-3 py-2 rounded hover:bg-gray-700"
              :class="{ 'bg-gray-700': $route.path.startsWith('/movies') }"
            >
              {{ t('nav.movies') }}
            </router-link>
            <router-link
              to="/tvshows"
              class="flex items-center px-3 py-2 rounded hover:bg-gray-700"
              :class="{ 'bg-gray-700': $route.path.startsWith('/tvshows') }"
            >
              {{ t('nav.tvShows') }}
            </router-link>
          </div>
        </div>

        <!-- Task List -->
        <router-link
          to="/tasks"
          class="flex items-center px-7 py-2 mx-4 rounded hover:bg-gray-700"
          :class="{ 'bg-gray-700': $route.path === '/tasks' }"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <span v-if="sidebarOpen" class="ml-3">{{ t('nav.taskList') }}</span>
        </router-link>

        <!-- Processing History -->
        <router-link
          to="/history"
          class="flex items-center px-7 py-2 mx-4 rounded hover:bg-gray-700 mt-2"
          :class="{ 'bg-gray-700': $route.path === '/history' }"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span v-if="sidebarOpen" class="ml-3">{{ t('nav.history') }}</span>
        </router-link>
      </nav>
    </aside>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Top Navigation Bar -->
      <header class="bg-white shadow-sm h-16 flex items-center justify-between px-6">
        <!-- Left: Sidebar Toggle -->
        <button
          @click="sidebarOpen = !sidebarOpen"
          class="p-2 rounded hover:bg-gray-100"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <!-- Right: Language Selector and Logout -->
        <div class="flex items-center space-x-4">
          <!-- Language Selector -->
          <select
            v-model="currentLocale"
            @change="changeLocale"
            class="px-3 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="en">English</option>
            <option value="zh">中文</option>
          </select>

          <!-- Logout Button -->
          <button
            @click="handleLogout"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded hover:bg-red-700 transition"
          >
            {{ t('common.logout') }}
          </button>
        </div>
      </header>

      <!-- Content Area -->
      <main class="flex-1 overflow-auto p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const { t, locale } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

const sidebarOpen = ref(true)
const mediaMenuOpen = ref(true)
const currentLocale = ref(locale.value)

function toggleMediaMenu() {
  if (sidebarOpen.value) {
    mediaMenuOpen.value = !mediaMenuOpen.value
  }
}

function changeLocale() {
  locale.value = currentLocale.value
  localStorage.setItem('locale', currentLocale.value)
}

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>
