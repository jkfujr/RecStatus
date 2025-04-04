import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    title?: string
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    children: [
      {
        path: '',
        name: 'home',
        component: () => import('@/views/Home.vue'),
        meta: {
          title: '首页',
          requiresAuth: false
        }
      },
      {
        path: 'rooms',
        name: 'rooms',
        component: () => import('@/views/Rooms.vue'),
        meta: {
          title: '房间管理',
          requiresAuth: false
        }
      },
      {
        path: 'servers',
        name: 'servers',
        component: () => import('@/views/Servers.vue'),
        meta: {
          title: '服务器管理',
          requiresAuth: false
        }
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router 