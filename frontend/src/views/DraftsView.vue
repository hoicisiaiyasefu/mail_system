<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Delete, Refresh, EditPen } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMailList, deleteDraft } from '@/api/mail'

const router = useRouter()

const mailList = ref([])
const selectedMails = ref([])
const searchKeyword = ref('')
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const totalElements = ref(0)

async function loadDrafts() {
  loading.value = true
  try {
    const res = await getMailList('DRAFT', currentPage.value - 1, pageSize.value)
    mailList.value = (res.data.mails || []).map((m) => ({
      ...m,
      date: m.receivedAt || '',
      preview: (m.content || '').substring(0, 80),
    }))
    totalElements.value = res.data.totalElements || 0
  } catch (err) {
    ElMessage.error('加载草稿箱失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadDrafts)

watch(currentPage, () => loadDrafts())
watch(pageSize, () => { currentPage.value = 1; loadDrafts() })

function handleSelect(selection) {
  selectedMails.value = selection
}

function handleEditDraft(row) {
  // 跳转写信页并传递草稿数据
  router.push({
    path: '/compose',
    query: {
      draftId: row.id,
      to: row.to,
      subject: row.subject,
      content: row.content,
      cc: row.ccAddresses || '',
    },
  })
}

async function handleDelete() {
  if (selectedMails.value.length === 0) {
    ElMessage.warning('请先选择要删除的草稿')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedMails.value.length} 封草稿吗？`,
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
      await deleteDraft(id)
      deletedCount++
    } catch (err) {
      ElMessage.error('删除失败：' + (err.response?.data?.error || err.message))
    }
  }
  selectedMails.value = []
  if (deletedCount > 0) {
    ElMessage.success(`已删除 ${deletedCount} 封草稿`)
    loadDrafts()
  }
  loading.value = false
}

function handleCompose() {
  router.push('/compose')
}

function handleRefresh() {
  currentPage.value = 1
  loadDrafts()
  ElMessage.success('刷新成功')
}
</script>

<template>
  <div>
    <div class="mail-list-card">
      <div class="mail-toolbar">
        <div style="display: flex; gap: 8px">
          <el-button type="primary" @click="handleCompose">
            <el-icon><EditPen /></el-icon> 写信
          </el-button>
          <el-button
            type="danger"
            :disabled="selectedMails.length === 0"
            @click="handleDelete"
          >
            <el-icon><Delete /></el-icon> 删除
          </el-button>
          <el-button @click="handleRefresh">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
        <el-input
          v-model="searchKeyword"
          placeholder="搜索草稿..."
          :prefix-icon="Search"
          style="width: 260px"
          clearable
        />
      </div>

      <el-table
        :data="mailList"
        style="width: 100%"
        @selection-change="handleSelect"
        @row-click="handleEditDraft"
        stripe
        highlight-current-row
        v-loading="loading"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column label="" width="40">
          <template #default>
            <el-tag size="small" type="warning">草稿</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="收件人" width="220">
          <template #default="{ row }">
            <span :style="{ color: row.to ? '#303133' : '#c0c4cc' }">
              {{ row.to || '（未填写收件人）' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="主题" min-width="300">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px">
              <span>{{ row.subject || '（无主题）' }}</span>
              <span style="color: #909399; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 260px">
                — {{ row.preview || '' }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="最后编辑" width="170" align="right">
          <template #default="{ row }">
            <span style="color: #909399; font-size: 13px">{{ row.date || '' }}</span>
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
