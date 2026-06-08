import apiClient from './axiosConfig'

export const authService = {
  /**
   * 登录
   * @param {string} username
   * @param {string} password
   * @returns {Promise<{ token: string, user: { id, username, email } }>}
   */
  login: (username, password) => {
    return apiClient.post('/user/login', { username, password }).then((res) => {
      // 登录成功后，将 token 存到 localStorage
      if (res.token) {
        localStorage.setItem('authToken', res.token)
      }
      return res
    })
  },

  /**
   * 注册
   * @param {string} username
   * @param {string} password
   * @param {string} email
   * @returns {Promise<{ message: string, user: { id, username, email } }>}
   */
  register: (username, password, email) => {
    return apiClient.post('/user/register', { username, password, email })
  },

  /**
   * 登出（清空 token）
   */
  logout: () => {
    localStorage.removeItem('authToken')
  },

  /**
   * 获取当前用户信息
   */
  getCurrentUser: () => {
    return apiClient.get('/auth/me')
  },
}
