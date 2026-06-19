<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Delete, Refresh, EditPen } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

// 模拟收件箱数据（is_spam: 1 表示垃圾邮件，匹配后端返回格式）
const mailList = ref([
  {
    id: 1,
    from: 'zhangsan@example.com',
    subject: '关于项目进展的汇报',
    preview: '您好，附件是本周的项目进展汇报，请查收。主要内容包括：1. 前端页面开发进度...',
    date: '2026-05-31 14:30',
    isRead: false,
    hasAttachment: true,
    is_spam: 0,
  },
  {
    id: 2,
    from: 'lisi@company.com',
    subject: '会议邀请：需求评审',
    preview: '各位同事，定于本周五下午3点在会议室A进行需求评审会议，请大家提前准备...',
    date: '2026-05-31 10:15',
    isRead: false,
    hasAttachment: false,
    is_spam: 0,
  },
  {
    id: 3,
    from: 'wangwu@school.edu',
    subject: '实训周报提交提醒',
    preview: '同学们请注意，第一周的实训周报需要在周五前提交，格式请参考模板...',
    date: '2026-05-30 16:45',
    isRead: true,
    hasAttachment: true,
    is_spam: 0,
  },
  {
    id: 4,
    from: 'admin@mail-system.com',
    subject: '欢迎使用邮件系统',
    preview: '欢迎注册使用本邮件系统！以下是系统的使用指南，帮助您快速上手...',
    date: '2026-05-29 09:00',
    isRead: true,
    hasAttachment: false,
    is_spam: 0,
  },
  {
    id: 5,
    from: 'noreply@github.com',
    subject: '[mail-system] New pull request #12',
    preview: 'feat: 添加前端登录页面和收件箱页面 — 新增了 Vue3 前端登录页面...',
    date: '2026-05-28 22:10',
    isRead: true,
    hasAttachment: false,
    is_spam: 0,
  },
  {
    id: 6,
    from: 'spammer@fake-promo.net',
    subject: '🎉 恭喜获得限时优惠大礼包',
    preview: '尊敬的客户，您已被选中获得我们的超级 VIP 折扣，全场商品低至1折！点击链接立即抢购...',
    date: '2026-06-01 08:30',
    isRead: false,
    hasAttachment: false,
    is_spam: 1,
  },
  {
    id: 7,
    from: 'lottery@scam-2026.cn',
    subject: '百万大奖通知 — 请立即领取',
    preview: '尊敬的用户，恭喜您在本年度抽奖活动中获得特等奖！请填写个人信息领取您的奖金...',
    date: '2026-06-01 02:15',
    isRead: false,
    hasAttachment: true,
    is_spam: 1,
  },
])

const selectedMails = ref([])
const searchKeyword = ref('')

const currentPage = ref(1)
const pageSize = ref(10)

// ========== 搜索过滤 ==========
const filteredMailList = computed(() => {
  if (!searchKeyword.value.trim()) return mailList.value
  const keyword = searchKeyword.value.toLowerCase().trim()
  return mailList.value.filter(
    (mail) =>
      mail.subject.toLowerCase().includes(keyword) ||
      mail.from.toLowerCase().includes(keyword) ||
      mail.preview.toLowerCase().includes(keyword)
  )
})

function handleSelect(selection) {
  selectedMails.value = selection
}

function handleRefresh() {
  ElMessage.success('刷新成功')
}

// 批量删除
function handleBatchDelete() {
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

// 单行删除
function handleDeleteSingle(row) {
  ElMessageBox.confirm(`确定要删除邮件"${row.subject}"吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    mailList.value = mailList.value.filter((m) => m.id !== row.id)
    selectedMails.value = selectedMails.value.filter((m) => m.id !== row.id)
    ElMessage.success('删除成功')
  }).catch(() => {})
}

// 切换已读/未读
function handleToggleRead(row) {
  row.isRead = !row.isRead
  ElMessage.success(row.isRead ? '已标记为已读' : '已标记为未读')
}

function handleViewMail(row) {
  ElMessage.info(`查看邮件详情（后续开发）: ${row.subject}`)
}

function handleCompose() {
  router.push('/compose')
}

// 勾选行样式：未读邮件高亮背景
function tableRowClassName({ row }) {
  if (row.is_spam === 1) return 'spam-row'
  return row.isRead ? '' : 'unread-row'
}
</script>

<template>
  <div>
    <!-- ========== 搜索框（页面顶部） ========== -->
    <div class="search-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索邮件 — 支持发件人、主题、内容预览..."
        :prefix-icon="Search"
        clearable
        size="large"
        class="search-input"
      />
    </div>

    <!-- ========== 邮件列表卡片 ========== -->
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
            @click="handleBatchDelete"
          >
            <el-icon><Delete /></el-icon> 批量删除
          </el-button>
        </div>
        <span class="mail-count">
          共 {{ filteredMailList.length }} 封邮件
          <template v-if="searchKeyword.trim()">（搜索结果）</template>
        </span>
      </div>

      <!-- 邮件列表表格 -->
      <el-table
        :data="filteredMailList"
        style="width: 100%"
        @selection-change="handleSelect"
        @row-click="handleViewMail"
        :row-class-name="tableRowClassName"
        stripe
        highlight-current-row
      >
        <!-- 多选列 -->
        <el-table-column type="selection" width="45" />

        <!-- 已读/未读状态圆点 -->
        <el-table-column label="状态" width="60" align="center">
          <template #default="{ row }">
            <span
              class="status-dot"
              :class="row.isRead ? 'status-read' : 'status-unread'"
              :title="row.isRead ? '已读' : '未读'"
              @click.stop="handleToggleRead(row)"
              style="cursor: pointer"
            ></span>
          </template>
        </el-table-column>

        <!-- 附件图标 -->
        <el-table-column label="" width="40">
          <template #default="{ row }">
            <span v-if="row.hasAttachment">📎</span>
          </template>
        </el-table-column>

        <!-- 发件人 -->
        <el-table-column label="发件人" width="180">
          <template #default="{ row }">
            <span :style="{ fontWeight: row.isRead ? 'normal' : 'bold' }">
              {{ row.from }}
            </span>
          </template>
        </el-table-column>

        <!-- 主题（含垃圾邮件标签） -->
        <el-table-column label="主题" min-width="320">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px">
              <!-- 垃圾邮件标签（当 is_spam == 1 时显示） -->
              <el-tag
                v-if="row.is_spam === 1"
                type="danger"
                size="small"
                effect="dark"
              >
                垃圾邮件
              </el-tag>
              <span :style="{ fontWeight: row.isRead ? 'normal' : 'bold' }">
                {{ row.subject }}
              </span>
              <span
                class="mail-preview"
                :style="{ fontWeight: row.isRead ? 'normal' : 'normal' }"
              >
                — {{ row.preview }}
              </span>
            </div>
          </template>
        </el-table-column>

        <!-- 时间 -->
        <el-table-column label="时间" width="170" align="right">
          <template #default="{ row }">
            <span style="color: #909399; font-size: 13px">{{ row.date }}</span>
          </template>
        </el-table-column>

        <!-- 操作列 -->
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="danger"
              size="small"
              text
              :icon="Delete"
              @click.stop="handleDeleteSingle(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="mail-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="filteredMailList.length"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          small
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ===== 搜索框 ===== */
.search-bar {
  margin-bottom: 16px;
}

.search-input {
  max-width: 600px;
}

/* ===== 状态圆点 ===== */
.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.status-read {
  background-color: #67c23a;
  box-shadow: 0 0 4px rgba(103, 194, 58, 0.5);
}

.status-unread {
  background-color: #409eff;
  box-shadow: 0 0 4px rgba(64, 158, 255, 0.5);
}

/* ===== 邮件预览文本截断 ===== */
.mail-preview {
  color: #909399;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

/* ===== 邮件计数 ===== */
.mail-count {
  color: #909399;
  font-size: 13px;
}

/* ===== 分页 ===== */
.mail-pagination {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px;
}

/* ===== 行样式 ===== */
:deep(.unread-row) {
  background-color: #f0f7ff;
}

:deep(.spam-row) {
  background-color: #fef0f0;
}
</style>
