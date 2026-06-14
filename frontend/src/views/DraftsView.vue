<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Delete, Refresh, EditPen } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

// 草稿箱暂时使用本地存储（后端暂无草稿 API）
const savedDrafts = localStorage.getItem('mail_drafts')
const mailList = ref(savedDrafts ? JSON.parse(savedDrafts) : [])

const selectedMails = ref([])
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

// 搜索过滤后的草稿列表
const filteredList = computed(() => {
  const kw = searchKeyword.value.toLowerCase().trim()
  if (!kw) return mailList.value
  return mailList.value.filter(
    (m) =>
      (m.to || '').toLowerCase().includes(kw) ||
      (m.subject || '').toLowerCase().includes(kw),
  )
})

function handleSelect(selection) {
  selectedMails.value = selection
}

function handleEditDraft(row) {
  router.push('/compose')
  ElMessage.info('已跳转到写信页（草稿预填充功能后续开发）')
}

function handleDelete() {
  if (selectedMails.value.length === 0) {
    ElMessage.warning('请先选择要删除的草稿')
    return
  }
  ElMessageBox.confirm('确定要删除选中的草稿吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    const ids = selectedMails.value.map((m) => m.id)
    mailList.value = mailList.value.filter((m) => !ids.includes(m.id))
    selectedMails.value = []
    localStorage.setItem('mail_drafts', JSON.stringify(mailList.value))
    ElMessage.success('草稿已删除')
  }).catch(() => {})
}

function handleCompose() {
  router.push('/compose')
}

function handleRefresh() {
  ElMessage.success('刷新成功')
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

      <!-- 列表 -->
      <el-table
        :data="filteredList"
        style="width: 100%"
        @selection-change="handleSelect"
        @row-click="handleEditDraft"
        stripe
        highlight-current-row
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
              <span>{{ row.subject }}</span>
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
