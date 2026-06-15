import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login',
    },
    // ========== 空白布局（无侧边栏）==========
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { layout: 'blank' },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { layout: 'blank' },
    },
    // ========== 邮件布局（侧边栏 + 顶栏）==========
    {
      path: '/inbox',
      name: 'inbox',
      component: () => import('@/views/InboxView.vue'),
      meta: { layout: 'mail', title: '收件箱' },
    },
    {
      path: '/compose',
      name: 'compose',
      component: () => import('@/views/ComposeView.vue'),
      meta: { layout: 'mail', title: '写信' },
    },
    {
      path: '/mail/:id',
      name: 'mailDetail',
      component: () => import('@/views/MailDetailView.vue'),
      meta: { layout: 'mail', title: '邮件详情' },
    },
    {
      path: '/sent',
      name: 'sent',
      component: () => import('@/views/SentView.vue'),
      meta: { layout: 'mail', title: '已发送' },
    },
    {
      path: '/spam',
      name: 'spam',
      component: () => import('@/views/SpamView.vue'),
      meta: { layout: 'mail', title: '垃圾邮件' },
    },
    {
      path: '/drafts',
      name: 'drafts',
      component: () => import('@/views/DraftsView.vue'),
      meta: { layout: 'mail', title: '草稿箱' },
    },
    {
      path: '/trash',
      name: 'trash',
      component: () => import('@/views/TrashView.vue'),
      meta: { layout: 'mail', title: '废纸篓' },
    },
    {
      path: '/starred',
      name: 'starred',
      component: () => import('@/views/StarredView.vue'),
      meta: { layout: 'mail', title: '星标邮件' },
    },
    {
      path: '/archive',
      name: 'archive',
      component: () => import('@/views/ArchiveView.vue'),
      meta: { layout: 'mail', title: '归档' },
    },
    {
      path: '/contacts',
      name: 'contacts',
      component: () => import('@/views/ContactsView.vue'),
      meta: { layout: 'mail', title: '通讯录' },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: { layout: 'mail', title: '设置' },
    },
  ],
})

export default router
