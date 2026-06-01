<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Delete, Refresh, EditPen } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

// 模拟收件箱数据
const mailList = ref([
  {
    id: 1,
    from: 'zhangsan@example.com',
    subject: '关于项目进展的汇报',
    preview: '您好，附件是本周的项目进展汇报，请查收。主要内容包括：1. 前端页面开发进度...',
    date: '2026-05-31 14:30',
    isRead: false,
    hasAttachment: true,
  },
  {
    id: 2,
    from: 'lisi@company.com',
    subject: '会议邀请：需求评审',
    preview: '各位同事，定于本周五下午3点在会议室A进行需求评审会议，请大家提前准备...',
    date: '2026-05-31 10:15',
    isRead: false,
    hasAttachment: false,
  },
  {
    id: 3,
    from: 'wangwu@school.edu',
    subject: '实训周报提交提醒',
    preview: '同学们请注意，第一周的实训周报需要在周五前提交，格式请参考模板...',
    date: '2026-05-30 16:45',
    isRead: true,
    hasAttachment: true,
  },
  {
    id: 4,
    from: 'admin@mail-system.com',
    subject: '欢迎使用邮件系统',
    preview: '欢迎注册使用本邮件系统！以下是系统的使用指南，帮助您快速上手...',
    date: '2026-05-29 09:00',
    isRead: true,
    hasAttachment: false,
  },
  {
    id: 5,
    from: 'noreply@github.com',
    subject: '[mail-system] New pull request #12',
    preview: 'feat: 添加前端登录页面和收件箱页面 — 新增了 Vue3 前端登录页面...',
    date: '2026-05-28 22:10',
    isRead: true,
    hasAttachment: false,
  },
])

const selectedMails = ref([])
const searchKeyword = ref('')

const currentPage = ref(1)
const pageSize = ref(10)

function handleSelect(selection) {
  selectedMails.value = selection
}

function handleRefresh() {
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
    const ids = selectedMails.value.map((m) => m.id)
    mailList.value = mailList.value.filter((m) => !ids.includes(m.id))
    selectedMails.value = []
    ElMessage.success('删除成功')
  }).catch(() => {})
}

function handleViewMail(row) {
  ElMessage.info(`查看邮件详情（后续开发）: ${row.subject}`)
}

function handleCompose() {
  router.push('/compose')
}

// 勾选行样式
function tableRowClassName({ row }) {
  return row.isRead ? '' : 'unread-row'
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
          <el-button @click="handleRefresh">
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
              <span style="color: #909399; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 300px">
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
