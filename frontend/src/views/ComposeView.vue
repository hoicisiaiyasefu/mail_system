<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Promotion, EditPen, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { sendMailFormData } from '@/api/mail'

const router = useRouter()

const composeFormRef = ref(null)
const uploadRef = ref(null)

const composeForm = reactive({
  to: '',
  cc: '',
  subject: '',
  body: '',
})

// 附件列表（存储用户选择的文件）
const fileList = ref([])

const rules = {
  to: [
    { required: true, message: '请输入收件人邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  subject: [
    { required: true, message: '请输入邮件主题', trigger: 'blur' },
  ],
}

const sending = ref(false)

async function handleSend() {
  const valid = await composeFormRef.value?.validate().catch(() => false)
  if (!valid) return

  sending.value = true
  try {
    // 用 FormData 打包文字和文件
    const formData = new FormData()
    formData.append('to', composeForm.to)
    formData.append('subject', composeForm.subject)
    formData.append('content', composeForm.body)
    if (composeForm.cc) {
      formData.append('cc', composeForm.cc)
    }
    // 添加附件
    fileList.value.forEach((file) => {
      formData.append('file', file.raw || file)
    })

    const res = await sendMailFormData(formData)
    const data = res.data
    if (data.error) {
      ElMessage.error(data.error)
      return
    }
    ElMessage.success('邮件发送成功！收件人将收到 AI 自动分析。')
    router.push('/inbox')
  } catch (err) {
    const msg = err.response?.data?.error || '发送失败，请检查网络连接'
    ElMessage.error(msg)
  } finally {
    sending.value = false
  }
}

function handleDraft() {
  ElMessage.success('已保存到草稿箱（后续开发）')
}

/** el-upload 文件变化时更新 fileList */
function handleFileChange(uploadFile) {
  fileList.value = uploadFile
}
</script>

<template>
  <div>
    <div class="compose-card">
      <h3 style="margin-bottom: 24px; font-size: 18px; color: #303133">
        <el-icon style="margin-right: 6px"><EditPen /></el-icon> 撰写邮件
      </h3>

      <el-form
        ref="composeFormRef"
        :model="composeForm"
        :rules="rules"
        label-width="80px"
      >
        <el-form-item label="收件人" prop="to">
          <el-input
            v-model="composeForm.to"
            placeholder="请输入收件人邮箱，如 user@example.com"
          />
        </el-form-item>

        <el-form-item label="抄送" prop="cc">
          <el-input
            v-model="composeForm.cc"
            placeholder="抄送（可选，多个邮箱用逗号分隔）"
          />
        </el-form-item>

        <el-form-item label="主题" prop="subject">
          <el-input
            v-model="composeForm.subject"
            placeholder="请输入邮件主题"
          />
        </el-form-item>

        <el-form-item label="附件">
          <el-upload
            ref="uploadRef"
            v-model:file-list="fileList"
            action="#"
            :auto-upload="false"
            :limit="3"
            :on-exceed="() => ElMessage.warning('最多上传 3 个附件')"
            @change="handleFileChange"
          >
            <el-button type="primary" plain>
              <el-icon><UploadFilled /></el-icon> 添加附件
            </el-button>
            <template #tip>
              <div style="color: #909399; font-size: 12px; margin-top: 4px">
                单个文件不超过 10MB，最多上传 3 个附件
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item label="内容" prop="body">
          <el-input
            v-model="composeForm.body"
            type="textarea"
            :rows="12"
            placeholder="请输入邮件正文内容..."
          />
        </el-form-item>

        <el-form-item>
          <div style="display: flex; gap: 12px">
            <el-button type="primary" :loading="sending" @click="handleSend">
              <el-icon><Promotion /></el-icon> 发送
            </el-button>
            <el-button @click="handleDraft">存草稿</el-button>
            <el-button @click="router.push('/inbox')">取消</el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
/* 写信页样式已在全局 styles.css 中定义 */
</style>
