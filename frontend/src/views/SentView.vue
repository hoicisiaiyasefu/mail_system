<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Delete, Refresh, EditPen } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

const mailList = ref([
  {
    id: 101,
    to: 'zhangsan@example.com',
    toName: '张三',
    subject: 'Re: 关于项目进展的汇报',
    preview: '收到，我会在下周一之前完成前端部分的开发...',
    date: '2026-06-01 09:15',
    hasAttachment: true,
  },
  {
    id: 102,
    to: 'lisi@company.com',
    toName: '李四',
    subject: 'Re: 会议邀请：需求评审',
    preview: '好的，我会准时参加，已经准备好了相关材料...',
    date: '2026-05-31 16:30',
    hasAttachment: false,
  },
  {
    id: 103,
    to: 'admin@mail-system.com',
    toName: '系统管理员',
    subject: '关于系统使用的问题咨询',
    preview: '你好，请问附件上传的大小限制可以调整吗？目前...',
    date: '2026-05-30 11:20',
    hasAttachment: false,
  },
  {
    id: 104,
    to: 'wangwu@school.edu',
    toName: '王五',
    subject: '第一周实训周报',
    preview: '王老师您好，附件是我第一周的实训周报，请查收...',
    date: '2026-05-29 17:00',
    hasAttachment: true,
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
  ElMessage.info(`查看已发送邮件详情（后续开发）: ${row.subject}`)
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
        :data="mailList"
        style="width: 100%"
        @selection-change="handleSelect"
        @row-click="handleViewMail"
        stripe
        highlight-current-row
      >
        <el-table-column type="selection" width="45" />
        <el-table-column label="" width="40">
          <template #default="{ row }">
            <span v-if="row.hasAttachment">📎</span>
          </template>
        </el-table-column>
        <el-table-column label="收件人" width="200">
          <template #default="{ row }">
            <div>
              <div>{{ row.toName }}</div>
              <div style="font-size: 12px; color: #909399">{{ row.to }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="主题" min-width="320">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px">
              <span>{{ row.subject }}</span>
              <span style="color: #909399; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 260px">
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
