<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UserFilled, Lock, EditPen } from '@element-plus/icons-vue'
import api from '@/api'

const router = useRouter()

const profile = reactive({
  username: '',
  email: '',
  nickname: '',
  signature: '',
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const loading = ref(false)
const signatureLoading = ref(false)

onMounted(async () => {
  try {
    const res = await api.get('/user/profile')
    Object.assign(profile, res.data)
  } catch (err) {
    ElMessage.error('加载用户资料失败')
  }
})

async function handleUpdateProfile() {
  loading.value = true
  try {
    await api.put('/user/profile', { nickname: profile.nickname })
    ElMessage.success('资料已更新')
  } catch (err) {
    ElMessage.error('更新失败：' + (err.response?.data?.error || err.message))
  } finally {
    loading.value = false
  }
}

async function handleChangePassword() {
  if (!passwordForm.oldPassword || !passwordForm.newPassword) {
    ElMessage.warning('请填写旧密码和新密码')
    return
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  if (passwordForm.newPassword.length < 6) {
    ElMessage.warning('新密码长度不能少于 6 位')
    return
  }
  loading.value = true
  try {
    await api.put('/user/password', {
      oldPassword: passwordForm.oldPassword,
      newPassword: passwordForm.newPassword,
    })
    ElMessage.success('密码已修改，请重新登录')
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
  } catch (err) {
    ElMessage.error('修改失败：' + (err.response?.data?.error || err.message))
  } finally {
    loading.value = false
  }
}

async function handleUpdateSignature() {
  signatureLoading.value = true
  try {
    await api.put('/user/signature', { signature: profile.signature })
    ElMessage.success('签名已更新')
  } catch (err) {
    ElMessage.error('更新失败：' + (err.response?.data?.error || err.message))
  } finally {
    signatureLoading.value = false
  }
}
</script>

<template>
  <div style="max-width: 600px; margin: 0 auto">
    <h3 style="margin-bottom: 24px; font-size: 18px; color: #303133">
      <el-icon><UserFilled /></el-icon> 用户设置
    </h3>

    <!-- 基本信息 -->
    <el-card style="margin-bottom: 20px">
      <template #header>
        <span><el-icon><UserFilled /></el-icon> 基本信息</span>
      </template>
      <el-form label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="profile.username" disabled />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="profile.email" disabled />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="profile.nickname" placeholder="设置昵称" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleUpdateProfile">
            保存资料
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 邮件签名 -->
    <el-card style="margin-bottom: 20px">
      <template #header>
        <span><el-icon><EditPen /></el-icon> 邮件签名</span>
      </template>
      <el-form label-width="80px">
        <el-form-item label="签名内容">
          <el-input
            v-model="profile.signature"
            type="textarea"
            :rows="4"
            placeholder="设置邮件签名（发送邮件时自动附加在正文末尾）"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="signatureLoading" @click="handleUpdateSignature">
            保存签名
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 修改密码 -->
    <el-card>
      <template #header>
        <span><el-icon><Lock /></el-icon> 修改密码</span>
      </template>
      <el-form label-width="100px">
        <el-form-item label="旧密码">
          <el-input
            v-model="passwordForm.oldPassword"
            type="password"
            show-password
            placeholder="请输入旧密码"
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            show-password
            placeholder="请输入新密码（至少 6 位）"
          />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            show-password
            placeholder="请再次输入新密码"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="danger" :loading="loading" @click="handleChangePassword">
            修改密码
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>
