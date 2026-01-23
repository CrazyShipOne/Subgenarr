import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/movies'
        },
        {
          path: 'movies',
          name: 'movies',
          component: () => import('@/views/MoviesView.vue')
        },
        {
          path: 'movies/:mediaId',
          name: 'movie-detail',
          component: () => import('@/views/MovieDetailView.vue')
        },
        {
          path: 'tvshows',
          name: 'tvshows',
          component: () => import('@/views/TVShowsView.vue')
        },
        {
          path: 'tvshows/:showTitle',
          name: 'tvshow-detail',
          component: () => import('@/views/TVShowDetailView.vue')
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: () => import('@/views/TasksView.vue')
        },
        {
          path: 'history',
          name: 'history',
          component: () => import('@/views/HistoryView.vue')
        }
      ]
    }
  ]
})

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Check if route requires authentication
  if (to.meta.requiresAuth !== false) {
    // Check authentication status
    if (!authStore.isAuthenticated) {
      await authStore.checkAuth()
    }

    if (!authStore.isAuthenticated) {
      // Redirect to login
      next({ name: 'login', query: { redirect: to.fullPath } })
      return
    }
  } else if (to.name === 'login' && authStore.isAuthenticated) {
    // If already authenticated, redirect to home
    next({ path: '/' })
    return
  }

  next()
})

export default router
