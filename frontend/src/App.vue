<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  UserFilled,
  EditPen,
  Message,
  Promotion,
  WarningFilled,
  DocumentCopy,
  Delete,
  Star,
  Box,
  Setting,
  User,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const showMailLayout = computed(() => route.meta.layout === 'mail')

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/compose')) return '/compose'
  if (path.startsWith('/inbox')) return '/inbox'
  if (path.startsWith('/sent')) return '/sent'
  if (path.startsWith('/drafts')) return '/drafts'
  if (path.startsWith('/spam')) return '/spam'
  if (path.startsWith('/trash')) return '/trash'
  if (path.startsWith('/archive')) return '/archive'
  if (path.startsWith('/starred')) return '/starred'
  if (path.startsWith('/contacts')) return '/contacts'
  if (path.startsWith('/settings')) return '/settings'
  if (path.startsWith('/mail/')) return '/inbox'  // 邮件详情页高亮收件箱
  return '/inbox'
})

function handleMenuSelect(index) {
  router.push(index)
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <!-- 空白布局：登录页等 -->
  <div v-if="!showMailLayout">
    <router-view />
  </div>

  <!-- 邮件系统布局：侧边栏 + 内容区 -->
  <div v-else class="mail-layout">
    <!-- 左侧导航 -->
    <aside class="mail-sidebar">
      <div class="logo">📧 邮件系统</div>
      <el-menu
        :default-active="activeMenu"
        @select="handleMenuSelect"
      >
        <el-menu-item index="/compose">
          <el-icon><EditPen /></el-icon>
          <span>写信</span>
        </el-menu-item>
        <el-menu-item index="/inbox">
          <el-icon><Message /></el-icon>
          <span>收件箱</span>
        </el-menu-item>
        <el-menu-item index="/sent">
          <el-icon><Promotion /></el-icon>
          <span>已发送</span>
        </el-menu-item>
        <el-menu-item index="/drafts">
          <el-icon><DocumentCopy /></el-icon>
          <span>草稿箱</span>
        </el-menu-item>
        <el-menu-item index="/spam">
          <el-icon><WarningFilled /></el-icon>
          <span>垃圾邮件</span>
        </el-menu-item>
        <el-menu-item index="/starred">
          <el-icon><Star /></el-icon>
          <span>星标邮件</span>
        </el-menu-item>
        <el-menu-item index="/archive">
          <el-icon><Box /></el-icon>
          <span>归档</span>
        </el-menu-item>
        <el-menu-item index="/trash">
          <el-icon><Delete /></el-icon>
          <span>废纸篓</span>
        </el-menu-item>
        <el-menu-item index="/contacts">
          <el-icon><User /></el-icon>
          <span>通讯录</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
      </el-menu>
    </aside>

    <!-- 右侧主区域 -->
    <div class="mail-main">
      <!-- 顶部栏 -->
      <header class="mail-header">
        <span style="font-size: 16px; font-weight: 500; color: #303133;">
          {{ route.meta.title || '邮件系统' }}
        </span>
        <div class="user-info">
          <el-icon><UserFilled /></el-icon>
          <span>{{ authStore.username }}</span>
          <el-button type="danger" size="small" text @click="handleLogout">退出</el-button>
        </div>
      </header>

      <!-- 内容区 -->
      <main class="mail-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
/* 图标样式：需要与 el-icon 配合 */
</style>
