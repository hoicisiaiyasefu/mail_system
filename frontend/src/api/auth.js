import api from './index'

/** 用户注册 */
export function register(username, password, email) {
  return api.post('/user/register', { username, password, email })
}

/** 用户登录 */
export function login(username, password) {
  return api.post('/user/login', { username, password })
}
