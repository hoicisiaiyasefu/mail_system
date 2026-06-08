<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Delete, Refresh, EditPen } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { mailService } from '@/api/mailService'

const router = useRouter()

const mailList = ref([]) // 从后端获取的邮件列表
const selectedMails = ref([])
const searchKeyword = ref('')
const loading = ref(false)

const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

/**
 * 页面加载时拉取邮件列表
 */
onMounted(() => {
  fetchMailList()
})

/**
 * 从后端获取邮件列表
 */
async function fetchMailList() {
  loading.value = true
  try {
    const res = await mailService.getMailList(currentPage.value, pageSize.value)
    mailList.value = res.mails || []
    total.value = res.total || 0
  } catch (error) {
    ElMessage.error('获取邮件列表失败')
    console.error('Fetch mails error:', error)
  } finally {
    loading.value = false
  }
}

function handleSelect(selection) {
  selectedMails.value = selection
}

async function handleRefresh() {
  await fetchMailList()
  ElMessage.success('刷新成功')
}

async function handleDelete() {
  if (selectedMails.value.length === 0) {
    ElMessage.warning('请先选择要删除的邮件')
    return
  }
  ElMessageBox.confirm(`确定要删除选中的 ${selectedMails.value.length} 封邮件吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        // 批量删除邮件
        await Promise.all(selectedMails.value.map((m) => mailService.deleteMail(m.id)))
        ElMessage.success('删除成功')
        selectedMails.value = []
        await fetchMailList() // 刷新列表
      } catch (error) {
        ElMessage.error('删除失败')
        console.error('Delete error:', error)
      }
    })
    .catch(() => {})
}

async function handleViewMail(row) {
  try {
    // 标记为已读
    await mailService.markAsRead(row.id)
    // 跳转到详情页（如果有）
    ElMessage.info(`查看邮件详情: ${row.subject}（后续开发详情页）`)
  } catch (error) {
    console.error('Mark as read error:', error)
  }
}

function handleCompose() {
  router.push('/compose')
}

// 勾选行样式
function tableRowClassName({ row }) {
  return row.isRead ? '' : 'unread-row'
}

// 分页变化时重新拉取
function handlePageChange() {
  fetchMailList()
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

      <!-- 邮件列表（使用 v-for 循环渲染） -->
      <el-table
        :data="mailList"
        style="width: 100%"
        v-loading="loading"
        @selection-change="handleSelect"
        @row-click="handleViewMail"
        :row-class-name="tableRowClassName"
        stripe
        highlight-current-row
      >
        <el-table-column type="selection" width="45" />
        <el-table-column label="" width="40">
          <template #default="{ row }">
            <span v-if="row.hasAttachment">📎</span>
          </template>
        </el-table-column>
        <el-table-column label="发件人" width="180">
          <template #default="{ row }">
            <span :style="{ fontWeight: row.isRead ? 'normal' : 'bold' }">
              {{ row.from }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="主题" min-width="320">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px">
              <span :style="{ fontWeight: row.isRead ? 'normal' : 'bold' }">
                {{ row.subject }}
              </span>
              <span
                style="
                  color: #909399;
                  font-size: 13px;
                  overflow: hidden;
                  text-overflow: ellipsis;
                  white-space: nowrap;
                  max-width: 300px;
                "
              >
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

      <!-- 分页 -->
      <div style="display: flex; justify-content: flex-end; padding: 12px 16px">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="handlePageChange"
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
