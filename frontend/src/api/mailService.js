import apiClient from './axiosConfig'

export const mailService = {
  /**
   * 获取收件箱邮件列表
   * @param {number} page - 页码（从 1 开始）
   * @param {number} pageSize - 每页数量
   * @returns {Promise<{ mails: Array, total: number }>}
   */
  getMailList: (page = 1, pageSize = 10) => {
    return apiClient.get('/mail/list', {
      params: { page, pageSize },
    }).then((res) => {
      // 后端返回 { mails: [...] }，前端补充 total 和 preview
      const mails = res.mails || []
      return {
        mails: mails.map((mail) => ({
          ...mail,
          preview: mail.subject || '（无主题）',
          date: mail.receivedAt?.split('T')[0] || '未知时间',
          isRead: false, // 简化处理
        })),
        total: mails.length,
      }
    })
  },

  /**
   * 获取单封邮件详情
   * @param {number} id - 邮件 ID
   */
  getMail: (id) => {
    return apiClient.get(`/mails/${id}`)
  },

  /**
   * 发送邮件（支持文件附件）
   * @param {Object} data
   *   - to: string - 收件人邮箱
   *   - cc: string - 抄送邮箱（可选）
   *   - subject: string - 主题
   *   - body: string - 邮件正文
   *   - files: File[] - 文件列表（可选）
   * @returns {Promise<{ mailId: number, message: string }>}
   */
  sendMail: (data) => {
    const formData = new FormData()
    formData.append('to', data.to)
    if (data.cc) formData.append('cc', data.cc)
    formData.append('subject', data.subject)
    formData.append('content', data.body) // 后端期望 "content"

    // 添加文件
    if (data.files && data.files.length > 0) {
      data.files.forEach((file) => {
        formData.append('file', file) // 后端用 @RequestParam("file")
      })
    }

    return apiClient.post('/mail/send', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /**
   * 删除邮件
   * @param {number} id - 邮件 ID
   */
  deleteMail: (id) => {
    return apiClient.delete(`/mails/${id}`)
  },

  /**
   * 标记邮件为已读
   * @param {number} id - 邮件 ID
   */
  markAsRead: (id) => {
    return apiClient.put(`/mails/${id}/read`)
  },
}
