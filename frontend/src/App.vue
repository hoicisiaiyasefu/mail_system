<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  UserFilled,
  EditPen,
  Message,
  Promotion,
  WarningFilled,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const showMailLayout = computed(() => route.meta.layout === 'mail')

const activeMenu = computed(() => {
  if (route.path.startsWith('/inbox')) return '/inbox'
  if (route.path.startsWith('/compose')) return '/compose'
  return '/inbox'
})

function handleMenuSelect(index) {
  router.push(index)
}

function handleLogout() {
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
        <el-menu-item index="/spam">
          <el-icon><WarningFilled /></el-icon>
          <span>垃圾邮件</span>
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
          <span>用户名</span>
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
