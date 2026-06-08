<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Delete, Refresh, WarningFilled, CircleCheckFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

const mailList = ref([
  {
    id: 201,
    from: 'spammer@ads-click.com',
    subject: '恭喜你中了100万大奖！点击领取',
    preview: '亲爱的用户，恭喜您在本平台抽奖活动中获得一等奖100万元！请点击下方链接领取...',
    date: '2026-06-01 03:15',
    spamReason: '含钓鱼链接',
    spamScore: 98,
  },
  {
    id: 202,
    from: 'noreply@fake-bank.cn',
    subject: '您的银行账户存在异常，请立即验证',
    preview: '尊敬的客户，系统检测到您的银行账户存在异常登录，请立即点击链接验证身份信息...',
    date: '2026-05-31 22:40',
    spamReason: '伪装银行诈骗',
    spamScore: 95,
  },
  {
    id: 203,
    from: 'marketing@cheap-goods.shop',
    subject: '限时特惠！名牌包包1折清仓',
    preview: '全场大牌1折起，LV、Gucci限量特卖，机会难得错过再等一年！点击抢购...',
    date: '2026-05-30 08:00',
    spamReason: '广告营销',
    spamScore: 87,
  },
])

const selectedMails = ref([])
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

function handleSelect(selection) {
  selectedMails.value = selection
}

function handleNotSpam() {
  if (selectedMails.value.length === 0) {
    ElMessage.warning('请先选择要标记的邮件')
    return
  }
  const ids = selectedMails.value.map((m) => m.id)
  mailList.value = mailList.value.filter((m) => !ids.includes(m.id))
  selectedMails.value = []
  ElMessage.success('已标记为非垃圾邮件，移动到收件箱')
}

function handleDelete() {
  if (selectedMails.value.length === 0) {
    ElMessage.warning('请先选择要删除的邮件')
    return
  }
  ElMessageBox.confirm('确定要永久删除选中的垃圾邮件吗？此操作不可恢复！', '警告', {
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
    type: 'error',
  }).then(() => {
    const ids = selectedMails.value.map((m) => m.id)
    mailList.value = mailList.value.filter((m) => !ids.includes(m.id))
    selectedMails.value = []
    ElMessage.success('已彻底删除')
  }).catch(() => {})
}

function handleRefresh() {
  ElMessage.success('刷新成功')
}

function handleViewMail(row) {
  ElMessage.info(`查看垃圾邮件详情（后续开发）: ${row.subject}`)
}

// 根据分数返回颜色
function getScoreType(score) {
  if (score >= 95) return 'danger'
  if (score >= 80) return 'warning'
  return 'info'
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
          <el-button @click="handleRefresh">
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
        :data="mailList"
        style="width: 100%"
        @selection-change="handleSelect"
        @row-click="handleViewMail"
        stripe
        highlight-current-row
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
        <el-table-column label="识别原因" width="130">
          <template #default="{ row }">
            <el-tag :type="getScoreType(row.spamScore)" size="small">
              {{ row.spamReason }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="垃圾指数" width="90" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.spamScore >= 90 ? '#f56c6c' : '#e6a23c', fontWeight: 'bold' }">
              {{ row.spamScore }}%
            </span>
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
