<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Delete, Refresh, EditPen } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getInboxList } from '@/api/mail'

const router = useRouter()

const mailList = ref([])
const selectedMails = ref([])
const searchKeyword = ref('')
const loading = ref(false)

const currentPage = ref(1)
const pageSize = ref(10)

// 加载收件箱数据
async function loadInbox() {
  loading.value = true
  try {
    const res = await getInboxList()
    mailList.value = (res.data.mails || []).map((m) => ({
      ...m,
      preview: (m.summary || m.subject || '').substring(0, 80),
      date: m.receivedAt || '',
      isRead: m.readFlag !== undefined ? m.readFlag : true,
    }))
  } catch (err) {
    ElMessage.error('加载收件箱失败：' + (err.response?.data?.error || err.message))
  } finally {
    loading.value = false
  }
}

onMounted(loadInbox)

const filteredList = ref(mailList)

function handleSelect(selection) {
  selectedMails.value = selection
}

function handleRefresh() {
  loadInbox()
  ElMessage.success('刷新成功')
}

function handleDelete() {
  if (selectedMails.value.length === 0) {
    ElMessage.warning('请先选择要删除的邮件')
    return
  }
  ElMessageBox.confirm(`确定要删除选中的 ${selectedMails.value.length} 封邮件吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    selectedMails.value = []
    ElMessage.success('删除成功（后端接口待完善）')
  }).catch(() => {})
}

function handleViewMail(row) {
  router.push(`/mail/${row.id}`)
}

function handleCompose() {
  router.push('/compose')
}

function tableRowClassName({ row }) {
  return row.isRead ? '' : 'unread-row'
}

// AI标签颜色
function getPriorityColor(level) {
  const map = { critical: '#f56c6c', high: '#e6a23c', normal: '#909399', low: '#c0c4cc' }
  return map[level] || '#909399'
}
</script>

<template>
  <div>
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
              <el-tag v-if="row.isSpam" type="danger" size="small">垃圾</el-tag>
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
      </el-table>

      <!-- 分页 -->
      <div style="display: flex; justify-content: flex-end; padding: 12px 16px">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="mailList.length"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          small
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
:deep(.unread-row) {
  background-color: #f0f7ff;
}
</style>
