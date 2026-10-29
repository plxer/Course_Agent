import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/course' },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/ops',
      name: 'ops',
      component: () => import('../views/course/OpsView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/learning-analysis',
      name: 'learningAnalysis',
      component: () => import('../views/course/LearningAnalysisView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/course',
      name: 'courseHome',
      component: () => import('../views/course/ConversationView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/conversation',
      name: 'courseConversation',
      component: () => import('../views/course/ConversationView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/exercises',
      name: 'courseExercises',
      component: () => import('../views/course/ExercisesView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/reading',
      name: 'courseReading',
      component: () => import('../views/course/ReadingView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/videos',
      name: 'courseVideos',
      component: () => import('../views/course/VideosView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/guide',
      name: 'courseGuide',
      component: () => import('../views/course/GuideView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/feedback-admin',
      name: 'feedbackAdmin',
      component: () => import('../views/course/FeedbackAdminView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('../views/EmptyView.vue'),
      meta: { requiresAuth: false }
    }
  ]
})

router.beforeEach(async (to, from, next) => {
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth === true)
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin)

  const userStore = useUserStore()

  if (userStore.token && !userStore.userId) {
    try {
      await userStore.getCurrentUser()
    } catch (error) {
      console.error('获取用户信息失败:', error)
      userStore.logout()
    }
  }

  const isLoggedIn = userStore.isLoggedIn
  const isAdmin = userStore.isAdmin

  if (requiresAuth && !isLoggedIn) {
    sessionStorage.setItem('redirect', to.fullPath)
    next('/login')
    return
  }

  if (requiresAdmin && !isAdmin) {
    next('/course')
    return
  }

  if ((to.path === '/login' || to.path === '/register') && isLoggedIn) {
    next('/course')
    return
  }

  next()
})

export default router
