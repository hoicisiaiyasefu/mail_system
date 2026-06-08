import api from './index'

/** 获取邮件列表（可按文件夹筛选：INBOX, SPAM, SENT, DRAFT） */
export function getMailList(folder = 'INBOX') {
  return api.get('/mail/list', { params: { folder } })
}

/** 获取收件箱列表 */
export function getInboxList() {
  return getMailList('INBOX')
}

/** 获取邮件详情 */
export function getMailDetail(id) {
  return api.get(`/mail/${id}`)
}

/** 发送邮件 */
export function sendMail(to, subject, content, cc) {
  return api.post('/mail/send', { to, subject, content, cc })
}

/** 接收邮件（测试用） */
export function receiveMail(from, to, subject, content) {
  return api.post('/mail/receive', { from, to, subject, content })
}

/** 生成邮件摘要 */
export function generateSummary(id, maxLength) {
  return api.post(`/mail/${id}/summary`, maxLength ? { maxLength } : {})
}

/** 获取 AI 分析报告 */
export function getAiReport(id) {
  return api.get(`/mail/${id}/ai-report`)
}

/** 重新检测垃圾邮件（含完整 AI 分析） */
export function recheckSpam(id) {
  return api.post(`/mail/${id}/recheck-spam`)
}
