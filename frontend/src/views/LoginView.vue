<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const loginFormRef = ref(null)

const loginForm = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度在 2 到 20 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度在 6 到 20 个字符', trigger: 'blur' },
  ],
}

const loading = ref(false)

async function handleLogin() {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await login(loginForm.username, loginForm.password)
    const data = res.data
    if (data.error) {
      ElMessage.error(data.error)
      return
    }
    // 保存 token 和用户信息
    authStore.setAuth(data.token, data.user)
    ElMessage.success('登录成功！')
    router.push('/inbox')
  } catch (err) {
    const msg = err.response?.data?.error || '登录失败，请检查网络连接'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function goToRegister() {
  router.push('/register')
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <h2>📧 邮件系统</h2>
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="rules"
        label-position="top"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            :loading="loading"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <div style="text-align: center; margin-top: 10px">
        <span style="color: #909399; font-size: 14px">还没有账号？</span>
        <el-link type="primary" :underline="false" @click="goToRegister">
          立即注册
        </el-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 登录页样式已在全局 styles.css 中定义 */
</style>
