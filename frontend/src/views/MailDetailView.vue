<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, Delete, WarningFilled,
  Paperclip, Document, Download, Back,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()

// 模拟邮件数据库
const allMails = {
  1: {
    id: 1,
    from: 'zhangsan@example.com',
    fromName: '张三',
    to: 'me@mail-system.com',
    subject: '关于项目进展的汇报',
    body: '您好，\n\n附件是本周的项目进展汇报，请查收。\n\n主要内容包括：\n1. 前端页面开发进度 —— 已完成登录页、收件箱和写信页的基础开发，使用了 Vue 3 + Element Plus 技术栈。\n2. 后端接口开发进度 —— 用户模块和邮件模块的 Controller 和 Service 层已基本完成。\n3. AI 插件模块 —— 垃圾邮件识别和安全检测插件已初步集成。\n\n下周计划：\n- 前后端接口联调\n- 补充邮件详情页和已发送页面\n- 完善 AI 辅助功能\n\n如有问题请随时联系。\n\n此致\n敬礼\n\n张三',
    date: '2026-05-31 14:30',
    isRead: true,
    hasAttachment: true,
    attachments: [
      { name: '项目周报_0529.docx', size: '1.2 MB' },
      { name: '进度截图.png', size: '856 KB' },
    ],
  },
  2: {
    id: 2,
    from: 'lisi@company.com',
    fromName: '李四',
    to: 'me@mail-system.com',
    subject: '会议邀请：需求评审',
    body: '各位同事，\n\n定于本周五下午 3 点在会议室 A 进行需求评审会议，请大家提前准备相关材料。\n\n会议议程：\n1. 上周开发进度回顾（15分钟）\n2. 需求文档评审（30分钟）\n3. 技术方案讨论（20分钟）\n4. 任务分配（10分钟）\n\n请务必准时参加。\n\n李四',
    date: '2026-05-31 10:15',
    isRead: true,
    hasAttachment: false,
    attachments: [],
  },
  3: {
    id: 3,
    from: 'wangwu@school.edu',
    fromName: '王五',
    to: 'me@mail-system.com',
    subject: '实训周报提交提醒',
    body: '同学们请注意，\n\n第一周的实训周报需要在周五前提交，格式请参考模板。\n\n周报内容要求：\n1. 本周工作综述\n2. 遇到的问题和解决方案\n3. 下周工作计划\n\n提交截止时间：本周五 18:00\n\n王老师',
    date: '2026-05-30 16:45',
    isRead: true,
    hasAttachment: true,
    attachments: [
      { name: '实训周报模板.docx', size: '328 KB' },
    ],
  },
  4: {
    id: 4,
    from: 'admin@mail-system.com',
    fromName: '系统管理员',
    to: 'me@mail-system.com',
    subject: '欢迎使用邮件系统',
    body: '欢迎注册使用本邮件系统！\n\n以下是系统的使用指南，帮助您快速上手：\n\n📧 写信：点击左侧「写信」按钮，填写收件人、主题和正文后发送。支持上传附件（最多3个，单个不超过10MB）。\n\n📥 收件箱：查看所有收到的邮件，支持搜索、多选删除等操作。\n\n📨 已发送：查看已发送的邮件记录。\n\n⚠️ 垃圾邮件：系统会自动识别垃圾邮件并放入此文件夹。\n\n🤖 AI 助手：支持垃圾邮件智能识别、邮件安全检测和优先级排序（后续开放）。\n\n如有任何问题，请联系技术支持。\n\n系统管理员',
    date: '2026-05-29 09:00',
    isRead: true,
    hasAttachment: false,
    attachments: [],
  },
  5: {
    id: 5,
    from: 'noreply@github.com',
    fromName: 'GitHub',
    to: 'me@mail-system.com',
    subject: '[mail-system] New pull request #12',
    body: 'Hello,\n\nA new pull request has been opened in the mail-system repository:\n\nPR #12: feat: 添加前端登录页面和收件箱页面\nAuthor: hoicisiaiyasefu\n\nDescription:\n新增了 Vue3 前端登录页面和收件箱页面，使用 Element Plus 组件库。\n\nChanges:\n- 新增 LoginView.vue 登录页面\n- 新增 InboxView.vue 收件箱页面\n- 新增 ComposeView.vue 写信页面\n- 配置全局布局和路由\n\nView the pull request on GitHub for more details.\n\n— GitHub',
    date: '2026-05-28 22:10',
    isRead: true,
    hasAttachment: false,
    attachments: [],
  },
}

const mailId = computed(() => Number(route.params.id))
const mail = computed(() => allMails[mailId.value] || null)

// 标记为已读
if (mail.value) {
  mail.value.isRead = true
}

function goBack() {
  router.back()
}

function handleReply() {
  ElMessage.info('跳转到回复页面（后续开发）')
}

function handleDelete() {
  ElMessageBox.confirm('确定要删除这封邮件吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    ElMessage.success('已删除')
    router.push('/inbox')
  }).catch(() => {})
}

function handleReportSpam() {
  ElMessage.success('已将该邮件标记为垃圾邮件')
}
</script>

<template>
  <div>
    <!-- 未找到邮件 -->
    <el-result
      v-if="!mail"
      icon="warning"
      title="邮件不存在"
      sub-title="该邮件可能已被删除或链接无效"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/inbox')">返回收件箱</el-button>
      </template>
    </el-result>

    <!-- 邮件详情 -->
    <div v-else class="mail-detail-card">
      <!-- 标题栏 -->
      <div class="detail-header">
        <el-button text :icon="ArrowLeft" @click="goBack">返回</el-button>
        <h3 class="detail-subject">{{ mail.subject }}</h3>
        <div style="display: flex; gap: 8px">
          <el-button type="danger" plain size="small" :icon="WarningFilled" @click="handleReportSpam">
            举报垃圾
          </el-button>
          <el-button type="danger" size="small" :icon="Delete" @click="handleDelete">
            删除
          </el-button>
        </div>
      </div>

      <!-- 发件人信息 -->
      <div class="detail-meta">
        <div class="detail-from">
          <el-avatar :size="40" style="background: #409eff">
            {{ mail.fromName.charAt(0) }}
          </el-avatar>
          <div class="detail-from-info">
            <div class="detail-from-name">
              {{ mail.fromName }}
              <span class="detail-from-email">&lt;{{ mail.from }}&gt;</span>
            </div>
            <div class="detail-to">
              收件人：{{ mail.to }}
            </div>
          </div>
        </div>
        <div class="detail-date">{{ mail.date }}</div>
      </div>

      <el-divider />

      <!-- 正文 -->
      <div class="detail-body">
        <pre>{{ mail.body }}</pre>
      </div>

      <!-- 附件 -->
      <div v-if="mail.hasAttachment" class="detail-attachments">
        <el-divider />
        <h4 style="margin-bottom: 12px">
          <el-icon style="margin-right: 4px"><Paperclip /></el-icon>
          附件（{{ mail.attachments.length }}个）
        </h4>
        <div class="attachment-list">
          <div
            v-for="(att, index) in mail.attachments"
            :key="index"
            class="attachment-item"
          >
            <div class="attachment-left">
              <el-icon size="24" color="#409eff"><Document /></el-icon>
              <div>
                <div class="attachment-name">{{ att.name }}</div>
                <div class="attachment-size">{{ att.size }}</div>
              </div>
            </div>
            <el-button type="primary" link size="small">
              <el-icon><Download /></el-icon> 下载
            </el-button>
          </div>
        </div>
      </div>

      <el-divider />

      <!-- 底部操作栏 -->
      <div class="detail-actions">
        <el-button type="primary" @click="handleReply">
          <el-icon><Back /></el-icon> 回复
        </el-button>
        <el-button @click="handleReply">转发</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mail-detail-card {
  max-width: 900px;
  margin: 0 auto;
  background: #fff;
  border-radius: 8px;
  padding: 24px 30px;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.detail-subject {
  font-size: 20px;
  color: #303133;
  flex: 1;
  margin: 0 20px;
}

.detail-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.detail-from {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-from-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-from-name {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}

.detail-from-email {
  font-weight: 400;
  color: #909399;
  font-size: 13px;
  margin-left: 4px;
}

.detail-to {
  font-size: 13px;
  color: #909399;
}

.detail-date {
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
}

.detail-body {
  padding: 16px 0;
  line-height: 1.8;
  color: #303133;
  font-size: 15px;
}

.detail-body pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
}

.detail-attachments h4 {
  font-size: 14px;
  color: #303133;
}

.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.attachment-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f5f7fa;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.attachment-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.attachment-name {
  font-size: 14px;
  color: #303133;
}

.attachment-size {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.detail-actions {
  display: flex;
  gap: 12px;
}
</style>
