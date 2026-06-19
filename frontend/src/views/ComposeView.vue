<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Promotion, EditPen, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { QuillEditor } from '@vueup/vue-quill'
import '@vueup/vue-quill/dist/vue-quill.snow.css'
import { sendMailFormData, saveDraft, updateDraft } from '@/api/mail'
import api from '@/api'

const router = useRouter()
const route = useRoute()

const composeFormRef = ref(null)
const uploadRef = ref(null)

// 当前编辑的草稿 ID（编辑已有草稿时设置）
const editingDraftId = ref(null)

const composeForm = reactive({
  to: '',
  cc: '',
  bcc: '',
  subject: '',
  body: '',
})

// 附件列表（存储用户选择的文件）
const fileList = ref([])

// 从 query 参数恢复草稿内容
onMounted(async () => {
  // 加载用户签名
  try {
    const res = await api.get('/user/profile')
    if (res.data.signature) {
      composeForm.body = '\n\n-- \n' + res.data.signature
    }
  } catch (_) { /* 静默失败 */ }

  const query = route.query
  if (query.draftId) {
    editingDraftId.value = Number(query.draftId)
    composeForm.to = query.to || ''
    composeForm.cc = query.cc || ''
    composeForm.subject = query.subject || ''
    composeForm.body = query.content || ''
  }
  // 回复/转发参数
  if (query.replyTo) {
    const origSubject = query.subject || ''
    composeForm.subject = origSubject.startsWith('Re:') ? origSubject : `Re: ${origSubject}`
    composeForm.to = query.from || ''
    const origContent = query.content || ''
    const origFrom = query.from || ''
    const origDate = query.date || ''
    composeForm.body = `\n\n> -------- 原始邮件 --------\n> 发件人: ${origFrom}\n> 时间: ${origDate}\n> 主题: ${origSubject}\n>\n> ${origContent.replace(/\n/g, '\n> ')}`
  }
  if (query.forward) {
    const origSubject = query.subject || ''
    composeForm.subject = origSubject.startsWith('Fwd:') ? origSubject : `Fwd: ${origSubject}`
    const origContent = query.content || ''
    const origFrom = query.from || ''
    const origDate = query.date || ''
    composeForm.body = `\n\n> -------- 转发邮件 --------\n> 发件人: ${origFrom}\n> 时间: ${origDate}\n> 主题: ${origSubject}\n>\n> ${origContent.replace(/\n/g, '\n> ')}`
  }
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
    if (composeForm.bcc) {
      formData.append('bcc', composeForm.bcc)
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

async function handleDraft() {
  if (!composeForm.to && !composeForm.subject && !composeForm.body) {
    ElMessage.warning('请至少填写一项内容再保存草稿')
    return
  }
  try {
    if (editingDraftId.value) {
      await updateDraft(editingDraftId.value, composeForm.to, composeForm.subject, composeForm.body, composeForm.cc)
      ElMessage.success('草稿已更新')
    } else {
      const res = await saveDraft(composeForm.to, composeForm.subject, composeForm.body, composeForm.cc)
      if (res.data.error) {
        ElMessage.error(res.data.error)
        return
      }
      editingDraftId.value = res.data.id
      ElMessage.success('草稿已保存')
    }
  } catch (err) {
    ElMessage.error('保存草稿失败：' + (err.response?.data?.error || err.message))
  }
}

/** el-upload 文件变化时更新 fileList — 使用 nextTick 确保 DOM 同步 */
function handleFileChange() {
  // v-model:file-list 已自动双向绑定，此处仅用于强制刷新
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

        <el-form-item label="密送">
          <el-input
            v-model="composeForm.bcc"
            placeholder="密送（可选，收件人彼此不可见）"
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

        <el-form-item label="内容" prop="body" class="editor-form-item">
          <QuillEditor
            v-model:content="composeForm.body"
            content-type="html"
            theme="snow"
            toolbar="full"
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

<style>
/*
 * Quill 编辑器全局样式覆盖
 * 非 scoped — Quill vendor CSS 优先级很高，scoped :deep() 难以稳定覆盖
 * 使用 .editor-form-item 作为命名空间避免污染其他页面
 */

/* 容器：强制宽度约束，覆盖 Quill 默认 height:100% */
.editor-form-item .ql-container {
  width: 100% !important;
  max-width: 100% !important;
  height: auto !important;
  min-height: 300px;
  max-height: 520px;
  overflow: hidden auto;   /* x:hidden y:auto */
  box-sizing: border-box;
  border-radius: 0 0 6px 6px;
  border: 1px solid #dcdfe6;
  border-top: none;
  font-size: 15px;
}

.editor-form-item .ql-toolbar {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box;
  display: flex;
  flex-wrap: wrap;
  border-radius: 6px 6px 0 0;
  border: 1px solid #dcdfe6;
  border-bottom: 1px solid #e8edf2;
}

/* 关键：强制 el-form-item__content 不超出表单宽度 */
.editor-form-item .el-form-item__content {
  min-width: 0;
  overflow: hidden;
}

.editor-form-item .ql-editor {
  min-height: 300px;
  max-width: 100%;
  line-height: 1.8;
  word-break: break-word;
  overflow-wrap: break-word;
  white-space: pre-wrap;
}
</style>
