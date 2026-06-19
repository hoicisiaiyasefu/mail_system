<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Delete, Refresh, EditPen } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getInboxList, deleteMail, getUnreadCount, searchMail, batchDelete, batchMarkAsRead, toggleStar } from '@/api/mail'

const router = useRouter()

const mailList = ref([])
const selectedMails = ref([])
const searchKeyword = ref('')
const loading = ref(false)

const currentPage = ref(1)
const pageSize = ref(20)
const totalElements = ref(0)

// 未读邮件通知
const unreadCount = ref(0)
const showNewMailTip = ref(false)
let pollingTimer = null

// 加载收件箱数据（服务端分页）
async function loadInbox() {
  loading.value = true
  try {
    const res = await getInboxList(currentPage.value - 1, pageSize.value)
    const data = res.data
    mailList.value = (data.mails || []).map((m) => ({
      ...m,
      preview: (m.summary || m.subject || '').substring(0, 80),
      date: m.receivedAt || '',
      isRead: m.readFlag !== undefined ? m.readFlag : false,
    }))
    totalElements.value = data.totalElements || 0
  } catch (err) {
    ElMessage.error('加载收件箱失败：' + (err.response?.data?.error || err.message))
  } finally {
    loading.value = false
  }
}

// 后端搜索（分页）
async function performSearch() {
  const kw = searchKeyword.value.trim()
  if (!kw) {
    loadInbox()
    return
  }
  loading.value = true
  try {
    const res = await searchMail(kw, currentPage.value - 1, pageSize.value)
    const data = res.data
    mailList.value = (data.mails || []).map((m) => ({
      ...m,
      preview: (m.summary || m.subject || '').substring(0, 80),
      date: m.receivedAt || '',
      isRead: m.readFlag !== undefined ? m.readFlag : false,
    }))
    totalElements.value = data.totalElements || 0
  } catch (err) {
    ElMessage.error('搜索失败：' + (err.response?.data?.error || err.message))
  } finally {
    loading.value = false
  }
}

// 防抖搜索
let searchTimer = null
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    performSearch()
  }, 400)
}

// 监听分页变化
watch(currentPage, () => {
  if (searchKeyword.value.trim()) {
    performSearch()
  } else {
    loadInbox()
  }
})
watch(pageSize, () => {
  currentPage.value = 1
  if (searchKeyword.value.trim()) {
    performSearch()
  } else {
    loadInbox()
  }
})

// 轮询未读邮件数量（每10秒）
async function pollUnreadCount() {
  try {
    const res = await getUnreadCount()
    const newCount = res.data.unreadCount || 0
    if (newCount > unreadCount.value) {
      showNewMailTip.value = true
    }
    unreadCount.value = newCount
  } catch (_) {
    // 静默失败
  }
}

function dismissTip() {
  showNewMailTip.value = false
}

onMounted(() => {
  loadInbox()
  pollUnreadCount()
  pollingTimer = setInterval(pollUnreadCount, 10000)
})

onUnmounted(() => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
  if (searchTimer) clearTimeout(searchTimer)
})

function handleSelect(selection) {
  selectedMails.value = selection
}

function handleRefresh() {
  currentPage.value = 1
  searchKeyword.value = ''
  loadInbox()
  pollUnreadCount()
  showNewMailTip.value = false
  ElMessage.success('刷新成功')
}

async function handleBatchMarkRead() {
  if (selectedMails.value.length === 0) {
    ElMessage.warning('请先选择要标记的邮件')
    return
  }
  const ids = selectedMails.value.map((m) => m.id)
  try {
    const res = await batchMarkAsRead(ids)
    ElMessage.success(res.data.message || `已标记 ${res.data.count} 封邮件为已读`)
    selectedMails.value = []
    loadInbox()
    pollUnreadCount()
  } catch (err) {
    ElMessage.error('标记失败：' + (err.response?.data?.error || err.message))
  }
}

async function handleDelete() {
  if (selectedMails.value.length === 0) {
    ElMessage.warning('请先选择要删除的邮件')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedMails.value.length} 封邮件吗？`,
      '提示',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  loading.value = true
  const ids = selectedMails.value.map((m) => m.id)
  try {
    const res = await batchDelete(ids)
    if (res.data.count > 0) {
      ElMessage.success(`已成功删除 ${res.data.count} 封邮件`)
      selectedMails.value = []
      loadInbox()
      pollUnreadCount()
    }
  } catch (err) {
    ElMessage.error('删除失败：' + (err.response?.data?.error || err.message))
  }
  loading.value = false
}

// 单行删除
async function handleDeleteSingle(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除邮件"${row.subject}"吗？`,
      '提示',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  loading.value = true
  try {
    await deleteMail(row.id)
    ElMessage.success('删除成功')
    loadInbox()
    pollUnreadCount()
  } catch (err) {
    ElMessage.error('删除失败：' + (err.response?.data?.error || err.message))
  }
  loading.value = false
}

async function handleToggleStar(row) {
  try {
    await toggleStar(row.id)
    row.starred = !row.starred
    ElMessage.success(row.starred ? '已标星' : '已取消标星')
  } catch (err) {
    ElMessage.error('操作失败')
  }
}

function handleViewMail(row) {
  router.push(`/mail/${row.id}`)
}

function handleCompose() {
  router.push('/compose')
}

function tableRowClassName({ row }) {
  if (row.isSpam) return 'spam-row'
  return row.isRead ? '' : 'unread-row'
}

function getPriorityColor(level) {
  const map = { critical: '#f56c6c', high: '#e6a23c', normal: '#909399', low: '#c0c4cc' }
  return map[level] || '#909399'
}
</script>

<template>
  <div>
    <!-- ========== 搜索框（页面顶部） ========== -->
    <div class="search-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索邮件 — 支持发件人、主题、内容..."
        :prefix-icon="Search"
        clearable
        size="large"
        @input="onSearchInput"
        @clear="handleRefresh"
      />
    </div>

    <!-- 新邮件通知横幅 -->
    <div v-if="showNewMailTip" class="new-mail-banner" @click="dismissTip">
      <span>📬 {{ unreadCount > 0 ? `您有 ${unreadCount} 封未读邮件，点击刷新查看` : '检查新邮件中...' }}</span>
      <el-button size="small" text style="color: #fff" @click.stop="handleRefresh">刷新</el-button>
      <span style="cursor: pointer; margin-left: 8px; opacity: 0.8" @click.stop="dismissTip">✕</span>
    </div>

    <!-- 工具栏 -->
    <div class="mail-list-card">
      <div class="mail-toolbar">
        <div style="display: flex; gap: 8px">
          <el-button type="primary" @click="handleCompose">
            <el-icon><EditPen /></el-icon> 写信
          </el-button>
          <el-button @click="handleRefresh" :loading="loading">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
          <el-button
            type="warning"
            :disabled="selectedMails.length === 0"
            @click="handleBatchMarkRead"
          >
            标记已读
          </el-button>
          <el-button
            type="danger"
            :disabled="selectedMails.length === 0"
            @click="handleDelete"
          >
            <el-icon><Delete /></el-icon> 删除
          </el-button>
        </div>
        <div style="display: flex; gap: 8px">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索邮件..."
            :prefix-icon="Search"
            style="width: 260px"
            clearable
            @input="onSearchInput"
            @clear="handleRefresh"
          />
        </div>
      </div>

      <!-- 邮件列表 -->
      <el-table
        :data="mailList"
        style="width: 100%"
        @selection-change="handleSelect"
        @row-click="handleViewMail"
        :row-class-name="tableRowClassName"
        stripe
        highlight-current-row
        v-loading="loading"
      >
        <el-table-column type="selection" width="45" />

        <!-- 已读/未读状态圆点 -->
        <el-table-column label="状态" width="60" align="center">
          <template #default="{ row }">
            <span
              class="status-dot"
              :class="row.isRead ? 'status-read' : 'status-unread'"
              :title="row.isRead ? '已读' : '未读'"
              @click.stop="row.isRead = !row.isRead"
              style="cursor: pointer"
            ></span>
          </template>
        </el-table-column>
        <el-table-column label="" width="40" align="center">
          <template #default="{ row }">
            <span
              :style="{ cursor: 'pointer', color: row.starred ? '#e6a23c' : '#c0c4cc', fontSize: '16px' }"
              @click.stop="handleToggleStar(row)"
            >{{ row.starred ? '⭐' : '☆' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="" width="70">
          <template #default="{ row }">
            <div style="display: flex; gap: 4px; align-items: center">
              <span v-if="row.hasAttachments">📎</span>
              <el-tag
                v-if="row.priorityLevel"
                :color="getPriorityColor(row.priorityLevel)"
                size="small"
                style="color: #fff; border: none; font-size: 11px"
              >
                {{ row.priorityLevel === 'critical' ? '紧急' : row.priorityLevel === 'high' ? '重要' : row.priorityLevel === 'normal' ? '普通' : '低' }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="发件人" width="180">
          <template #default="{ row }">
            <span :style="{ fontWeight: row.isRead ? 'normal' : 'bold' }">
              {{ row.from }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="主题" min-width="280">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px">
              <span :style="{ fontWeight: row.isRead ? 'normal' : 'bold' }">
                {{ row.subject }}
              </span>
              <span style="color: #909399; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 250px">
                — {{ row.summary || row.subject }}
              </span>
              <el-tag v-if="row.isSpam" type="danger" size="small" effect="dark">垃圾邮件</el-tag>
              <el-tag v-if="row.riskLevel && row.riskLevel !== 'safe'" type="warning" size="small">{{ row.riskLevel }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="AI" width="60" align="center">
          <template #default="{ row }">
            <span v-if="row.aiAnalyzed" title="AI已分析">🤖</span>
            <span v-else title="等待AI分析" style="opacity: 0.3">⏳</span>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170" align="right">
          <template #default="{ row }">
            <span style="color: #909399; font-size: 13px">{{ row.date }}</span>
          </template>
        </el-table-column>

        <!-- 操作列 -->
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="danger"
              size="small"
              text
              :icon="Delete"
              @click.stop="handleDeleteSingle(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页（服务端） -->
      <div style="display: flex; justify-content: flex-end; padding: 12px 16px">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="totalElements"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          small
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ===== 搜索框 ===== */
.search-bar {
  margin-bottom: 16px;
}
.search-bar .el-input {
  max-width: 600px;
}

.new-mail-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 10px 20px;
  margin-bottom: 12px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  animation: slideDown 0.3s ease;
}
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to   { opacity: 1; transform: translateY(0); }
}
:deep(.unread-row) {
  background-color: #f0f7ff;
}
:deep(.spam-row) {
  background-color: #fef0f0;
}

/* ===== 状态圆点 ===== */
.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.status-read {
  background-color: #67c23a;
  box-shadow: 0 0 4px rgba(103, 194, 58, 0.5);
}
.status-unread {
  background-color: #409eff;
  box-shadow: 0 0 4px rgba(64, 158, 255, 0.5);
}
</style>
