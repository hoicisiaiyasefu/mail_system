<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getMailList, moveToFolder } from '@/api/mail'
import { getCache, setCache } from '@/utils/cache'

const router = useRouter()

const mailList = ref([])
const searchKeyword = ref('')
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const totalElements = ref(0)

async function loadArchive() {
  const cached = getCache('ARCHIVE')
  if (cached) {
    mailList.value = (cached.mails || []).map(normalize)
    totalElements.value = cached.totalElements || 0
  }

  loading.value = true
  try {
    const res = await getMailList('ARCHIVE', currentPage.value - 1, pageSize.value)
    const data = res.data
    mailList.value = (data.mails || []).map(normalize)
    totalElements.value = data.totalElements || 0
    setCache('ARCHIVE', { mails: data.mails, totalElements: data.totalElements })
  } catch (err) {
    if (!cached) ElMessage.error('加载归档邮件失败')
  } finally {
    loading.value = false
  }
}

function normalize(m) {
  return {
    ...m,
    date: m.receivedAt || '',
    preview: (m.summary || m.subject || '').substring(0, 80),
    isRead: m.readFlag !== undefined ? m.readFlag : false,
  }
}

onMounted(loadArchive)

watch(currentPage, () => loadArchive())
watch(pageSize, () => { currentPage.value = 1; loadArchive() })

async function handleMoveToInbox(row) {
  try {
    await moveToFolder(row.id, 'INBOX')
    ElMessage.success('已移回收件箱')
    loadArchive()
  } catch (err) {
    ElMessage.error('操作失败：' + (err.response?.data?.error || err.message))
  }
}

function handleViewMail(row) {
  router.push(`/mail/${row.id}`)
}

function handleRefresh() {
  currentPage.value = 1
  loadArchive()
  ElMessage.success('刷新成功')
}
</script>

<template>
  <div>
    <div class="mail-list-card">
      <div class="mail-toolbar">
        <div style="display: flex; gap: 8px">
          <el-button @click="handleRefresh" :loading="loading">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
        <div style="display: flex; gap: 8px; align-items: center">
          <el-tag type="info" size="small">
            📦 归档邮件 · 共 {{ totalElements }} 封
          </el-tag>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索归档邮件..."
            :prefix-icon="Search"
            style="width: 220px"
            clearable
          />
        </div>
      </div>

      <el-table
        :data="mailList"
        style="width: 100%"
        @row-click="handleViewMail"
        stripe
        highlight-current-row
        v-loading="loading"
      >
        <el-table-column label="" width="70">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click.stop="handleMoveToInbox(row)">
              移回收件箱
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="发件人" width="200">
          <template #default="{ row }">
            <span :style="{ fontWeight: row.isRead ? 'normal' : 'bold' }">{{ row.from }}</span>
          </template>
        </el-table-column>
        <el-table-column label="主题" min-width="320">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px">
              <span :style="{ fontWeight: row.isRead ? 'normal' : 'bold' }">{{ row.subject }}</span>
              <span style="color: #909399; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 250px">
                — {{ row.preview }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170" align="right">
          <template #default="{ row }">
            <span style="color: #909399; font-size: 13px">{{ row.date }}</span>
          </template>
        </el-table-column>
      </el-table>

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
