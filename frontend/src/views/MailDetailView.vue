<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, Delete, WarningFilled,
  Paperclip, Document, Download, Back,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMailDetail, generateSummary, getAiReport, deleteMail, markAsRead } from '@/api/mail'

const route = useRoute()
const router = useRouter()

const mailId = computed(() => Number(route.params.id))
const mail = ref(null)
const loading = ref(true)
const summaryLoading = ref(false)

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
  router.push('/compose')
  ElMessage.info('已跳转到写信页')
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
      <div class="detail-body">
        <pre>{{ mail.content }}</pre>
      </div>

      <el-divider />

      <!-- 底部操作栏 -->
      <div class="detail-actions">
        <el-button type="primary" @click="handleReply">
          <el-icon><Back /></el-icon> 回复
        </el-button>
        <el-button @click="handleReply">转发</el-button>
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

.detail-subject {
  font-size: 20px;
  color: #303133;
  flex: 1;
  margin: 0 20px;
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
</style>
