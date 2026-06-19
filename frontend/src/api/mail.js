import api from './index'

/** 获取邮件列表（可按文件夹筛选，支持分页：INBOX, SPAM, SENT, DRAFT） */
export function getMailList(folder = 'INBOX', page = 0, size = 20) {
  return api.get('/mail/list', { params: { folder, page, size } })
}

/** 获取收件箱列表（分页） */
export function getInboxList(page = 0, size = 20) {
  return getMailList('INBOX', page, size)
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
  // ⚠️ 绝对不能手动设置 Content-Type！
  // 浏览器必须自动添加 boundary 参数：multipart/form-data; boundary=----WebKitFormBoundary...
  // 否则服务端无法解析文件二进制数据，导致附件丢失
  return api.post('/mail/send-with-attachment', formData, {
    timeout: 60000,
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

/** 获取未读邮件数量（用于轮询新邮件通知） */
export function getUnreadCount() {
  return api.get('/mail/unread-count')
}

/** 搜索邮件（分页，支持 folder/from 筛选） */
export function searchMail(keyword, page = 0, size = 20, folder, from) {
  const params = { keyword, page, size }
  if (folder) params.folder = folder
  if (from) params.from = from
  return api.get('/mail/search', { params })
}

// ============================================================
// 草稿箱 API
// ============================================================

/** 保存草稿 */
export function saveDraft(to, subject, content, cc) {
  return api.post('/mail/draft', { to, subject, content, cc })
}

/** 更新草稿 */
export function updateDraft(id, to, subject, content, cc) {
  return api.put(`/mail/draft/${id}`, { to, subject, content, cc })
}

/** 删除草稿 */
export function deleteDraft(id) {
  return api.delete(`/mail/draft/${id}`)
}

/** 彻底删除邮件 */
export function permanentDelete(id) {
  return api.delete('/mail/permanent', { params: { id } })
}

/** 清空废纸篓 */
export function emptyTrash() {
  return api.delete('/mail/trash/empty')
}

/** 标记为非垃圾邮件 */
export function markNotSpam(id) {
  return api.post(`/mail/${id}/not-spam`)
}

/** 批量标记已读 */
export function batchMarkAsRead(ids) {
  return api.post('/mail/batch-read', { ids })
}

/** 批量删除 */
export function batchDelete(ids) {
  return api.post('/mail/batch-delete', { ids })
}

/** 下载附件（返回 blob） */
export function downloadAttachment(id) {
  return api.get('/mail/download-attachment', {
    params: { id },
    responseType: 'blob',
  })
}

// ============================================================
// C模块：标星、归档、移动、已读切换
// ============================================================

/** 切换已读/未读 */
export function toggleRead(id) {
  return api.post(`/mail/${id}/toggle-read`)
}

/** 切换标星 */
export function toggleStar(id) {
  return api.post(`/mail/${id}/star`)
}

/** 归档邮件 */
export function archiveMail(id) {
  return api.post(`/mail/${id}/archive`)
}

/** 移动邮件到文件夹 */
export function moveToFolder(id, folder) {
  return api.post(`/mail/${id}/move`, null, { params: { folder } })
}

/** 高级搜索（支持 folder 和 from 筛选） */
export function searchMailAdvanced(keyword, folder, from, page = 0, size = 20) {
  return api.get('/mail/search', { params: { keyword, folder, from, page, size } })
}
