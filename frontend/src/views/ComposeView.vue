<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Promotion, EditPen, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { mailService } from '@/api/mailService'

const router = useRouter()

const composeFormRef = ref(null)
const uploadRef = ref(null)

const composeForm = reactive({
  to: '',
  cc: '',
  subject: '',
  body: '',
})

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
const attachedFiles = ref([]) // 保存已选择的文件

function handleSend() {
  composeFormRef.value?.validate(async (valid) => {
    if (!valid) return
    sending.value = true
    try {
      // 调用后端发送邮件接口，传递 FormData
      const response = await mailService.sendMail({
        to: composeForm.to,
        cc: composeForm.cc,
        subject: composeForm.subject,
        body: composeForm.body,
        files: attachedFiles.value, // 文件数组直接传递
      })

      ElMessage.success('邮件发送成功！')
      // 清空表单和文件
      composeForm.to = ''
      composeForm.cc = ''
      composeForm.subject = ''
      composeForm.body = ''
      attachedFiles.value = []
      uploadRef.value?.clearFiles()
      
      // 返回收件箱
      setTimeout(() => {
        router.push('/inbox')
      }, 1500)
    } catch (error) {
      ElMessage.error(error.response?.data?.message || '发送失败，请稍后重试')
      console.error('Send mail error:', error)
    } finally {
      sending.value = false
    }
  })
}

function handleDraft() {
  ElMessage.success('已保存到草稿箱（后续开发）')
}

/**
 * 处理文件上传前的事件
 * 限制文件大小和数量
 */
function handleExceed(files) {
  ElMessage.warning('最多上传 3 个附件')
}

/**
 * 文件被添加时的回调
 */
function handleFileChange(uploadFile, uploadFiles) {
  // 更新 attachedFiles，保存文件对象供发送时使用
  attachedFiles.value = uploadFiles.map((f) => f.raw)
}

/**
 * 删除附件
 */
function handleRemoveFile(uploadFile, uploadFiles) {
  attachedFiles.value = uploadFiles.map((f) => f.raw)
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
            action="#"
            :auto-upload="false"
            :limit="3"
            :on-exceed="handleExceed"
            @change="handleFileChange"
            @remove="handleRemoveFile"
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
