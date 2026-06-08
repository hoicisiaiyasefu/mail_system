import axios from 'axios'

// 创建 axios 实例，配置统一的 baseURL
const apiClient = axios.create({
  baseURL: 'http://localhost:8080/api', // 改成你的后端地址
  timeout: 10000,
})

// 请求拦截器：自动加入 token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：处理通用错误
apiClient.interceptors.response.use(
  (response) => response.data, // 直接返回 data，不要整个 response
  (error) => {
    if (error.response?.status === 401) {
      // token 过期，清除并跳转登录
      localStorage.removeItem('authToken')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
