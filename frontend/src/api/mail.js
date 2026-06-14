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

/** 发送邮件（FormData 版，支持附件） */
export function sendMailFormData(formData) {
  return api.post('/mail/send-with-attachment', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
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

/** 删除邮件（软删除） */
export function deleteMail(id) {
  return api.delete('/mail/delete', { params: { id } })
}

/** 标记邮件为已读 */
export function markAsRead(id) {
  return api.post('/mail/read', null, { params: { id } })
}

/** 获取未读邮件数量 */
export function getUnreadCount() {
  return api.get('/mail/unread-count')
}

/** 获取收件箱未读邮件数量（用于轮询新邮件通知） */
export function getUnreadCount() {
  return api.get('/mail/unread-count')
}
