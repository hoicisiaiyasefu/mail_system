/**
 * localStorage 邮件列表缓存工具
 *
 * 策略：先进页面渲染缓存数据，再异步请求后端更新。
 * 缓存 key 格式：mail_cache_{userId}_{folder}
 * 默认过期时间：5 分钟（可配）
 */

const CACHE_PREFIX = 'mail_cache_'
const DEFAULT_TTL = 5 * 60 * 1000 // 5 分钟

/** 获取当前登录用户的 ID（从 localStorage 读 user 对象） */
function getUserId() {
  try {
    const user = JSON.parse(localStorage.getItem('user') || 'null')
    return user?.id || 'anonymous'
  } catch {
    return 'anonymous'
  }
}

/** 构建缓存 key */
function buildKey(folder) {
  return `${CACHE_PREFIX}${getUserId()}_${folder}`
}

/**
 * 写入缓存
 * @param {string} folder - 文件夹名（INBOX, SENT, SPAM, DRAFT, TRASH 等）
 * @param {object} data  - 要缓存的数据（含 mails 数组和分页信息）
 * @param {number} ttl   - 过期时间（毫秒），默认 5 分钟
 */
export function setCache(folder, data, ttl = DEFAULT_TTL) {
  try {
    const payload = {
      data,
      timestamp: Date.now(),
      ttl,
    }
    localStorage.setItem(buildKey(folder), JSON.stringify(payload))
  } catch (e) {
    // localStorage 满了，静默失败
    console.warn('[cache] 写入缓存失败:', e.message)
  }
}

/**
 * 读取缓存
 * @param {string} folder - 文件夹名
 * @returns {object|null} 缓存数据，过期或不存在则返回 null
 */
export function getCache(folder) {
  try {
    const raw = localStorage.getItem(buildKey(folder))
    if (!raw) return null

    const payload = JSON.parse(raw)
    const age = Date.now() - payload.timestamp
    if (age > payload.ttl) {
      // 过期了，清理
      localStorage.removeItem(buildKey(folder))
      return null
    }
    return payload.data
  } catch {
    return null
  }
}

/**
 * 清除单个文件夹缓存
 * @param {string} folder
 */
export function clearCache(folder) {
  localStorage.removeItem(buildKey(folder))
}

/**
 * 清除当前用户所有邮件缓存
 */
export function clearAllCache() {
  const prefix = `${CACHE_PREFIX}${getUserId()}_`
  const keys = Object.keys(localStorage).filter((k) => k.startsWith(prefix))
  keys.forEach((k) => localStorage.removeItem(k))
}
