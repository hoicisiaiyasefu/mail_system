<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Delete, Refresh, DeleteFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMailList, permanentDelete, emptyTrash } from '@/api/mail'

const router = useRouter()

const mailList = ref([])
const selectedMails = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const totalElements = ref(0)

async function loadTrash() {
  loading.value = true
  try {
    const res = await getMailList('TRASH', currentPage.value - 1, pageSize.value)
    mailList.value = (res.data.mails || []).map((m) => ({
      ...m,
      date: m.receivedAt || '',
      preview: (m.summary || m.subject || '').substring(0, 80),
    }))
    totalElements.value = res.data.totalElements || 0
  } catch (err) {
    ElMessage.error('加载废纸篓失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadTrash)

watch(currentPage, () => loadTrash())
watch(pageSize, () => { currentPage.value = 1; loadTrash() })

function handleSelect(selection) {
  selectedMails.value = selection
}

async function handlePermanentDelete() {
  if (selectedMails.value.length === 0) {
    ElMessage.warning('请先选择要彻底删除的邮件')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要彻底删除选中的 ${selectedMails.value.length} 封邮件吗？此操作不可恢复！`,
      '警告',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'error' },
    )
  } catch {
    return
  }

  loading.value = true
  const ids = selectedMails.value.map((m) => m.id)
  for (const id of ids) {
    try {
      await permanentDelete(id)
    } catch (err) {
      ElMessage.error('删除失败：' + (err.response?.data?.error || err.message))
    }
  }
  selectedMails.value = []
  ElMessage.success('已彻底删除')
  loadTrash()
  loading.value = false
}

async function handleEmptyTrash() {
  try {
    await ElMessageBox.confirm(
      '确定要清空废纸篓吗？所有邮件将被永久删除且不可恢复！',
      '清空废纸篓',
      { confirmButtonText: '确定清空', cancelButtonText: '取消', type: 'error' },
    )
  } catch {
    return
  }

  loading.value = true
  try {
    const res = await emptyTrash()
    ElMessage.success(res.data.message || '废纸篓已清空')
    loadTrash()
  } catch (err) {
    ElMessage.error('清空失败：' + (err.response?.data?.error || err.message))
  } finally {
    loading.value = false
  }
}

function handleViewMail(row) {
  router.push(`/mail/${row.id}`)
}

function handleRefresh() {
  currentPage.value = 1
  loadTrash()
  ElMessage.success('刷新成功')
}
</script>

<template>
  <div>
    <div class="mail-list-card">
      <div class="mail-toolbar">
        <div style="display: flex; gap: 8px">
          <el-button
            type="danger"
            :disabled="selectedMails.length === 0"
            @click="handlePermanentDelete"
          >
            <el-icon><Delete /></el-icon> 彻底删除
          </el-button>
          <el-button
            type="danger"
            plain
            @click="handleEmptyTrash"
          >
            <el-icon><DeleteFilled /></el-icon> 清空废纸篓
          </el-button>
          <el-button @click="handleRefresh" :loading="loading">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </div>

      <el-table
        :data="mailList"
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
            <span>🗑️</span>
          </template>
        </el-table-column>
        <el-table-column label="发件人/收件人" width="220">
          <template #default="{ row }">
            <div style="font-size: 13px">
              <div>发：{{ row.from }}</div>
              <div style="color: #909399">收：{{ row.to }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="主题" min-width="320">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px">
              <span>{{ row.subject }}</span>
              <span style="color: #909399; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px">
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
