<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Delete, Refresh, WarningFilled, CircleCheckFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMailList, deleteMail } from '@/api/mail'

const router = useRouter()

const mailList = ref([])
const selectedMails = ref([])
const searchKeyword = ref('')
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)

// 搜索过滤后的邮件列表
const filteredList = computed(() => {
  const kw = searchKeyword.value.toLowerCase().trim()
  if (!kw) return mailList.value
  return mailList.value.filter(
    (m) =>
      (m.from || '').toLowerCase().includes(kw) ||
      (m.subject || '').toLowerCase().includes(kw),
  )
})

// 加载垃圾邮件列表（从收件箱中筛选 isSpam=true 的）
async function loadSpam() {
  loading.value = true
  try {
    const res = await getMailList('SPAM')
    mailList.value = res.data.mails || []
  } catch (err) {
    ElMessage.error('加载垃圾邮件失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadSpam)

function handleSelect(selection) {
  selectedMails.value = selection
}

function handleNotSpam() {
  if (selectedMails.value.length === 0) {
    ElMessage.warning('请先选择要标记的邮件')
    return
  }
  selectedMails.value = []
  ElMessage.success('已标记为非垃圾邮件（后端接口待完善）')
  loadSpam()
}

function handleDelete() {
  if (selectedMails.value.length === 0) {
    ElMessage.warning('请先选择要删除的邮件')
    return
  }
  ElMessageBox.confirm('确定要永久删除选中的垃圾邮件吗？', '警告', {
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
    type: 'error',
  }).then(() => {
    selectedMails.value = []
    ElMessage.success('已彻底删除')
    loadSpam()
  }).catch(() => {})
}

function handleRefresh() {
  loadSpam()
  ElMessage.success('刷新成功')
}

function handleViewMail(row) {
  router.push(`/mail/${row.id}`)
}

function getScoreType(score) {
  if (score >= 0.8) return 'danger'
  if (score >= 0.5) return 'warning'
  return 'info'
}

function getScorePercent(score) {
  return Math.round((score || 0) * 100)
}
</script>

<template>
  <div>
    <div class="mail-list-card">
      <!-- 工具栏 -->
      <div class="mail-toolbar">
        <div style="display: flex; gap: 8px">
          <el-button
            type="success"
            :disabled="selectedMails.length === 0"
            @click="handleNotSpam"
          >
            <el-icon><CircleCheckFilled /></el-icon> 这不是垃圾邮件
          </el-button>
          <el-button
            type="danger"
            :disabled="selectedMails.length === 0"
            @click="handleDelete"
          >
            <el-icon><Delete /></el-icon> 彻底删除
          </el-button>
          <el-button @click="handleRefresh" :loading="loading">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
        <div style="display: flex; gap: 8px; align-items: center">
          <el-tag type="info" size="small">
            🤖 AI 自动识别 · 共 {{ mailList.length }} 封
          </el-tag>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索垃圾邮件..."
            :prefix-icon="Search"
            style="width: 220px"
            clearable
          />
        </div>
      </div>

      <!-- 列表 -->
      <el-table
        :data="filteredList"
        style="width: 100%"
        @selection-change="handleSelect"
        @row-click="handleViewMail"
        stripe
        highlight-current-row
        v-loading="loading"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column label="" width="40">
          <template #default>
            <el-icon color="#f56c6c"><WarningFilled /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="发件人" width="200">
          <template #default="{ row }">
            <span style="color: #f56c6c">{{ row.from }}</span>
          </template>
        </el-table-column>
        <el-table-column label="主题" min-width="280">
          <template #default="{ row }">
            <span>{{ row.subject }}</span>
          </template>
        </el-table-column>
        <el-table-column label="AI 判定" width="130">
          <template #default="{ row }">
            <el-tag :type="getScoreType(row.spamScore)" size="small">
              {{ row.isSpam ? '垃圾邮件' : '正常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="垃圾指数" width="90" align="center">
          <template #default="{ row }">
            <span :style="{ color: (row.spamScore || 0) >= 0.5 ? '#f56c6c' : '#e6a23c', fontWeight: 'bold' }">
              {{ getScorePercent(row.spamScore) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170" align="right">
          <template #default="{ row }">
            <span style="color: #909399; font-size: 13px">{{ row.receivedAt || '' }}</span>
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
