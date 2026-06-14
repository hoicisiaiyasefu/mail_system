<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Delete, Refresh, EditPen } from '@element-plus/icons-vue'
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
      (m.to || '').toLowerCase().includes(kw) ||
      (m.subject || '').toLowerCase().includes(kw),
  )
})

// 加载已发送列表（目前从收件箱中筛选 SENT 文件夹的邮件）
async function loadSent() {
  loading.value = true
  try {
    const res = await getMailList('SENT')
    mailList.value = res.data.mails || []
  } catch (err) {
    ElMessage.error('加载已发送邮件失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadSent)

function handleSelect(selection) {
  selectedMails.value = selection
}

function handleRefresh() {
  loadSent()
  ElMessage.success('刷新成功')
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
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  loading.value = true
  const ids = selectedMails.value.map((m) => m.id)
  let deletedCount = 0
  for (const id of ids) {
    try {
      await deleteMail(id)
      deletedCount++
    } catch (err) {
      ElMessage.error('删除失败：' + (err.response?.data?.error || err.message))
    }
  }
  selectedMails.value = []
  if (deletedCount > 0) {
    ElMessage.success(`已成功删除 ${deletedCount} 封邮件`)
    loadSent()
  }
  loading.value = false
}

function handleViewMail(row) {
  router.push(`/mail/${row.id}`)
}

function handleCompose() {
  router.push('/compose')
}
</script>

<template>
  <div>
    <div class="mail-list-card">
      <!-- 工具栏 -->
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
        <el-input
          v-model="searchKeyword"
          placeholder="搜索已发送邮件..."
          :prefix-icon="Search"
          style="width: 260px"
          clearable
        />
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
          <template #default="{ row }">
            <span v-if="row.hasAttachments">📎</span>
          </template>
        </el-table-column>
        <el-table-column label="收件人" width="200">
          <template #default="{ row }">
            <div>
              <div>{{ row.to }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="主题" min-width="320">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px">
              <span>{{ row.subject }}</span>
              <span style="color: #909399; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 260px">
                — {{ row.summary || row.subject }}
              </span>
            </div>
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
