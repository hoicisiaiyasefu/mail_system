<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, ArrowDown, Delete, WarningFilled,
  Paperclip, Document, Download, Back, Star, StarFilled, Box, FolderOpened,
} from '@element-plus/icons-vue'
import DOMPurify from 'dompurify'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMailDetail, generateSummary, getAiReport, deleteMail, markAsRead, downloadAttachment, toggleStar, archiveMail, moveToFolder, toggleRead } from '@/api/mail'

const route = useRoute()
const router = useRouter()

const mailId = computed(() => Number(route.params.id))
const mail = ref(null)
const loading = ref(true)
const summaryLoading = ref(false)

// 安全渲染 HTML 正文（XSS 防护）
const safeContent = computed(() => {
  if (!mail.value?.content) return ''
  // 如果内容是 HTML，用 DOMPurify 净化；否则按纯文本处理
  const raw = mail.value.content
  if (raw.trim().startsWith('<')) {
    return DOMPurify.sanitize(raw)
  }
  // 纯文本：转义 HTML 后保留换行
  return raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
})

// 解析附件列表
const attachments = computed(() => {
  if (!mail.value?.hasAttachments || !mail.value?.attachmentPath) return []
  const paths = mail.value.attachmentPath.split(',')
  return paths.map((p) => {
    const rawName = p.split('/').pop().split('\\').pop()  // 兼容 Win/Linux 路径
    // 去掉 UUID 前缀（格式: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx_原始文件名）
    const cleanName = rawName.replace(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_/, '')
    const ext = cleanName.split('.').pop().toLowerCase()
    return {
      name: cleanName,
      path: p.trim(),
      ext,
      isImage: ['jpg','jpeg','png','gif','webp','bmp'].includes(ext),
      isPdf: ext === 'pdf',
      isDoc: ['doc','docx'].includes(ext),
    }
  })
})

// 下载附件（带 JWT 认证）
async function handleDownload() {
  try {
    const res = await downloadAttachment(mailId.value)
    // 优先从 Content-Disposition 头提取文件名
    const disposition = res.headers['content-disposition']
    let fileName = ''
    if (disposition) {
      // 尝试匹配 filename*=UTF-8''xxx 或 filename="xxx"
      const matchStar = disposition.match(/filename\*=UTF-8''([^;]+)/)
      const matchNormal = disposition.match(/filename="?([^";\n]+)"?/)
      if (matchStar) {
        fileName = decodeURIComponent(matchStar[1])
      } else if (matchNormal) {
        fileName = decodeURIComponent(matchNormal[1])
      }
    }
    // 回退：使用 attachments 中解析的文件名
    if (!fileName && attachments.value.length > 0) {
      fileName = attachments.value[0].name
    }
    if (!fileName) fileName = 'attachment'
    // 创建 Blob 下载链接
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = fileName
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    ElMessage.error('附件下载失败')
  }
}

// 加载邮件详情（并自动标记已读）
async function loadMail() {
  loading.value = true
  try {
    const res = await getMailDetail(mailId.value)
    mail.value = res.data
    // 如果邮件未读，自动标记为已读
    if (mail.value && !mail.value.readFlag) {
      markAsRead(mailId.value).then(() => {
        mail.value.readFlag = true
      }).catch(() => {})
    }
  } catch (err) {
    ElMessage.error('加载邮件失败')
    mail.value = null
  } finally {
    loading.value = false
  }
}

onMounted(loadMail)

// 生成 AI 摘要
async function handleGenerateSummary() {
  summaryLoading.value = true
  try {
    const res = await generateSummary(mailId.value)
    if (mail.value) {
      mail.value.summary = res.data.summary
      mail.value.summaryMethod = res.data.method
    }
    ElMessage.success(`摘要生成完成（方式：${res.data.method === 'llm' ? '大模型' : '提取式'}）`)
  } catch (err) {
    ElMessage.error('摘要生成失败')
  } finally {
    summaryLoading.value = false
  }
}

function goBack() {
  router.back()
}

function handleReply() {
  if (!mail.value) return
  router.push({
    path: '/compose',
    query: {
      replyTo: mail.value.id,
      from: mail.value.from,
      subject: mail.value.subject,
      content: mail.value.content,
      date: mail.value.receivedAt || '',
    },
  })
}

function handleForward() {
  if (!mail.value) return
  router.push({
    path: '/compose',
    query: {
      forward: mail.value.id,
      from: mail.value.from,
      subject: mail.value.subject,
      content: mail.value.content,
      date: mail.value.receivedAt || '',
    },
  })
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm('确定要删除这封邮件吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deleteMail(mailId.value)
    ElMessage.success('已删除')
    router.push('/inbox')
  } catch (err) {
    ElMessage.error('删除失败：' + (err.response?.data?.error || err.message))
  }
}

function handleReportSpam() {
  ElMessage.success('已将该邮件标记为垃圾邮件')
}

async function handleToggleStar() {
  if (!mail.value) return
  try {
    await toggleStar(mail.value.id)
    mail.value.starred = !mail.value.starred
    ElMessage.success(mail.value.starred ? '已标星' : '已取消标星')
  } catch (err) {
    ElMessage.error('操作失败')
  }
}

async function handleArchive() {
  if (!mail.value) return
  try {
    await ElMessageBox.confirm('确定要归档这封邮件吗？', '提示', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'info',
    })
  } catch { return }
  try {
    await archiveMail(mail.value.id)
    ElMessage.success('邮件已归档')
    router.push('/inbox')
  } catch (err) {
    ElMessage.error('归档失败：' + (err.response?.data?.error || err.message))
  }
}

async function handleMoveTo(folder) {
  if (!mail.value) return
  const labels = { INBOX: '收件箱', SPAM: '垃圾邮件', ARCHIVE: '归档', TRASH: '废纸篓' }
  const label = labels[folder] || folder
  try {
    await ElMessageBox.confirm(`确定要将邮件移动到「${label}」吗？`, '移动邮件', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'info',
    })
  } catch { return }
  try {
    await moveToFolder(mail.value.id, folder)
    ElMessage.success(`邮件已移动到「${label}」`)
    if (folder === 'TRASH') {
      router.push('/trash')
    } else {
      router.push('/inbox')
    }
  } catch (err) {
    ElMessage.error('移动失败：' + (err.response?.data?.error || err.message))
  }
}

async function handleToggleRead() {
  if (!mail.value) return
  try {
    await toggleRead(mail.value.id)
    mail.value.readFlag = !mail.value.readFlag
    ElMessage.success(mail.value.readFlag ? '已标记为已读' : '已标记为未读')
  } catch (err) {
    ElMessage.error('操作失败')
  }
}

// 风险等级颜色
function getRiskColor(level) {
  const map = { safe: '#67c23a', low: '#e6a23c', medium: '#e6a23c', high: '#f56c6c', critical: '#f56c6c' }
  return map[level] || '#909399'
}

// 优先级颜色
function getPriorityColor(level) {
  const map = { critical: '#f56c6c', high: '#e6a23c', normal: '#67c23a', low: '#909399' }
  return map[level] || '#909399'
}
</script>

<template>
  <div>
    <!-- 加载中 -->
    <div v-if="loading" style="text-align: center; padding: 60px">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p style="color: #909399; margin-top: 12px">加载邮件中...</p>
    </div>

    <!-- 未找到邮件 -->
    <el-result
      v-else-if="!mail"
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
        <div class="detail-subject-area">
          <el-tag
            v-if="mail.isSpam"
            type="danger"
            size="small"
            effect="dark"
            style="margin-right: 8px"
          >
            垃圾邮件
          </el-tag>
          <h3 class="detail-subject">{{ mail.subject }}</h3>
        </div>
        <div style="display: flex; gap: 8px; align-items: center">
          <el-button text size="small" @click="handleToggleStar" :title="mail.starred ? '取消标星' : '标星'">
            <el-icon :color="mail.starred ? '#e6a23c' : '#c0c4cc'" :size="18">
              <StarFilled v-if="mail.starred" /><Star v-else />
            </el-icon>
          </el-button>
          <el-button size="small" @click="handleToggleRead">
            {{ mail.readFlag ? '标记未读' : '标记已读' }}
          </el-button>
          <el-dropdown @command="handleMoveTo">
            <el-button size="small">
              移动到 <el-icon><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="INBOX">📥 收件箱</el-dropdown-item>
                <el-dropdown-item command="ARCHIVE">📦 归档</el-dropdown-item>
                <el-dropdown-item command="SPAM">🚫 垃圾邮件</el-dropdown-item>
                <el-dropdown-item command="TRASH">🗑️ 废纸篓</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button type="info" plain size="small" @click="handleArchive">
            <el-icon><Box /></el-icon> 归档
          </el-button>
          <el-button type="danger" plain size="small" :icon="WarningFilled" @click="handleReportSpam">
            举报垃圾
          </el-button>
          <el-button type="danger" size="small" :icon="Delete" @click="handleDelete">
            删除
          </el-button>
        </div>
      </div>

      <!-- AI 分析标签栏 -->
      <div v-if="mail.aiAnalyzed" class="ai-tags-bar">
        <el-tag v-if="mail.riskLevel" :color="getRiskColor(mail.riskLevel)" effect="dark" size="small">
          🔒 安全：{{ mail.riskLevel }}
        </el-tag>
        <el-tag v-if="mail.priorityLevel" :color="getPriorityColor(mail.priorityLevel)" effect="dark" size="small">
          ⚡ 优先级：{{ mail.priorityLevel }}
        </el-tag>
        <el-tag v-if="mail.isSpam" type="danger" effect="dark" size="small">
          🗑 垃圾邮件 ({{ mail.spamScore }})
        </el-tag>
        <el-tag v-else type="success" effect="dark" size="small">
          ✅ 正常邮件
        </el-tag>
      </div>
      <div v-else class="ai-tags-bar">
        <el-tag type="info" size="small">⏳ AI 正在后台分析中...</el-tag>
      </div>

      <!-- AI 摘要卡片 -->
      <div v-if="mail.summary" class="ai-summary-card">
        <div class="summary-label">🤖 AI 摘要</div>
        <div class="summary-text">{{ mail.summary }}</div>
      </div>
      <div v-else class="ai-summary-card" style="background: #fafafa; border-style: dashed">
        <div class="summary-label">🤖 AI 摘要</div>
        <div class="summary-text" style="color: #c0c4cc">
          点击下方「生成摘要」按钮，AI 将为你提炼邮件要点
        </div>
      </div>

      <!-- 发件人信息 -->
      <div class="detail-meta">
        <div class="detail-from">
          <el-avatar :size="40" style="background: #409eff">
            {{ (mail.from || '?').charAt(0).toUpperCase() }}
          </el-avatar>
          <div class="detail-from-info">
            <div class="detail-from-name">
              <span class="detail-from-email">&lt;{{ mail.from }}&gt;</span>
            </div>
            <div class="detail-to">
              收件人：{{ mail.to }}
            </div>
          </div>
        </div>
        <div class="detail-date">{{ mail.receivedAt || '' }}</div>
      </div>

      <el-divider />

      <!-- 正文 -->
      <div class="detail-body" v-html="safeContent"></div>

      <!-- 附件区域 -->
      <div v-if="attachments.length > 0" class="attachment-section">
        <el-divider />
        <div class="attachment-title">
          <el-icon><Paperclip /></el-icon> 附件（{{ attachments.length }}）
        </div>
        <div class="attachment-list">
          <div
            v-for="(att, idx) in attachments"
            :key="idx"
            class="attachment-item"
          >
            <div class="attachment-icon">
              <span v-if="att.isImage">🖼️</span>
              <span v-else-if="att.isPdf">📕</span>
              <span v-else-if="att.isDoc">📝</span>
              <span v-else>📄</span>
            </div>
            <div class="attachment-info">
              <span class="attachment-name">{{ att.name }}</span>
              <span class="attachment-type">.{{ att.ext }}</span>
            </div>
            <el-button
              text
              type="primary"
              size="small"
              class="attachment-download"
              @click.stop="handleDownload"
            >
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
        <el-button @click="handleForward">转发</el-button>
        <el-button
          type="success"
          :loading="summaryLoading"
          @click="handleGenerateSummary"
        >
          🤖 {{ mail.summary ? '重新生成摘要' : 'AI 生成摘要' }}
        </el-button>
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
  margin-bottom: 16px;
}

.detail-subject-area {
  display: flex;
  align-items: center;
  flex: 1;
  margin: 0 20px;
}
.detail-subject {
  font-size: 20px;
  color: #303133;
  margin: 0;
}

.ai-tags-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.ai-summary-card {
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
}

.summary-label {
  font-size: 13px;
  color: #409eff;
  font-weight: 500;
  margin-bottom: 4px;
}

.summary-text {
  font-size: 14px;
  color: #303133;
  line-height: 1.6;
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

.detail-actions {
  display: flex;
  gap: 12px;
}

/* 附件区域 */
.attachment-section {
  margin: 8px 0 16px;
}
.attachment-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 12px;
}
.attachment-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.attachment-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  min-width: 220px;
  transition: all 0.2s;
}
.attachment-item:hover {
  border-color: #409eff;
  background: #ecf5ff;
}
.attachment-icon {
  font-size: 22px;
}
.attachment-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}
.attachment-name {
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.attachment-type {
  font-size: 11px;
  color: #909399;
  text-transform: uppercase;
}
.attachment-download {
  flex-shrink: 0;
  font-size: 12px;
}
</style>
