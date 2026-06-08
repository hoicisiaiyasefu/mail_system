# 前端 Axios 集成指南

## 📋 完成内容汇总

前端已改造完成，可以直接连接后端 API，包括：

### 1. **创建的服务文件** 
- `src/api/axiosConfig.js` - axios 实例配置 + 请求/响应拦截器
- `src/api/authService.js` - 登录/注册服务
- `src/api/mailService.js` - 邮件收发服务

### 2. **改造的 Vue 组件**
- `src/views/LoginView.vue` - 登录 + 注册功能（Token 自动保存到 localStorage）
- `src/views/ComposeView.vue` - 发送邮件（FormData 打包文件）
- `src/views/InboxView.vue` - 收件箱列表（v-for 循环渲染后端数据）

---

## 🔑 关键知识点

### 1️⃣ Token 存储与自动注入

**LoginView.vue 中的登录流程：**
```javascript
// 调用后端登录接口
const res = await authService.login(username, password)
// 后端返回 token，authService 自动保存到 localStorage
// localStorage.setItem('authToken', res.data.token)
```

**axiosConfig.js 中的自动注入：**
```javascript
// 每次发请求时，拦截器自动从 localStorage 读 token，加入 Authorization header
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

**功能：后续所有请求都会自动带上 token，不需要手动处理**

---

### 2️⃣ FormData 上传文件

**ComposeView.vue 中的文件处理：**
```javascript
// el-upload 组件捕获文件
function handleFileChange(uploadFile, uploadFiles) {
  attachedFiles.value = uploadFiles.map((f) => f.raw)
}

// 发送时构造 FormData
function handleSend() {
  const formData = new FormData()
  formData.append('to', composeForm.to)
  formData.append('subject', composeForm.subject)
  formData.append('body', composeForm.body)
  
  // 添加多个文件
  attachedFiles.value.forEach((file) => {
    formData.append('attachments', file) // 数组形式
  })
  
  await mailService.sendMail(formData)
}
```

**重点：后端接收时需要用 `@RequestParam("attachments")` 接收 File[] 数组**

---

### 3️⃣ v-for 循环渲染邮件列表

**InboxView.vue 中的循环：**
```vue
<!-- 直接用 v-for 渲染后端返回的 mailList -->
<el-table
  :data="mailList"
  @selection-change="handleSelect"
>
  <el-table-column label="发件人" width="180">
    <template #default="{ row }">
      {{ row.from }}  <!-- 来自 mailList 中的每一项 -->
    </template>
  </el-table-column>
  <!-- ... 其他列 ... -->
</el-table>

<!-- 分页变化时自动重新拉取 -->
<el-pagination
  v-model:current-page="currentPage"
  :total="total"
  @change="handlePageChange"
/>
```

**流程：**
1. 页面加载时调用 `fetchMailList()`
2. 从后端拉取 `{ mails: [...], total: 100 }`
3. 赋值给 `mailList.ref([...])`
4. el-table 自动用 v-for 渲染
5. 分页变化时重新调用 `handlePageChange()`

---

## ⚙️ 后端接口要求

### 登录接口
```
POST /api/auth/login
Request: { username, password }
Response: { 
  code: 200,
  data: { 
    token: "jwt_token_here",
    user: { id, username, email }
  }
}
```

### 注册接口
```
POST /api/auth/register
Request: { username, password, email }
Response: { 
  code: 200,
  data: { userId: 1, message: "注册成功" }
}
```

### 邮件列表接口
```
GET /api/mails?page=1&pageSize=10
Headers: Authorization: Bearer {token}
Response: {
  code: 200,
  data: {
    mails: [
      { id, from, to, subject, body, preview, date, isRead, hasAttachment }
    ],
    total: 100
  }
}
```

### 发送邮件接口
```
POST /api/mails/send
Headers: 
  - Authorization: Bearer {token}
  - Content-Type: multipart/form-data
Body (FormData):
  - to: string
  - cc: string (optional)
  - subject: string
  - body: string
  - attachments: File[] (optional)

Response: {
  code: 200,
  data: { mailId: 1, message: "发送成功" }
}
```

### 删除邮件接口
```
DELETE /api/mails/{id}
Headers: Authorization: Bearer {token}
Response: { code: 200, data: { message: "删除成功" } }
```

### 标记已读接口
```
PUT /api/mails/{id}/read
Headers: Authorization: Bearer {token}
Response: { code: 200, data: { message: "标记成功" } }
```

---

## 🧪 测试步骤

1. **修改 baseURL**
   - 打开 `src/api/axiosConfig.js`
   - 改 `baseURL: 'http://localhost:8080/api'` 为你的后端地址

2. **确保后端提供上述接口**
   - 可以用 Postman 先测试一遍
   - 确保返回格式一致

3. **运行前端**
   ```bash
   cd frontend
   npm install  # 首次需要安装依赖
   npm run dev  # 开发服务器 (通常是 http://localhost:5173)
   ```

4. **测试流程**
   - 注册账号 → 登录 → token 保存到 localStorage
   - 发送邮件（带附件） → FormData 打包上传
   - 收件箱列表 → v-for 渲染邮件

---

## 🔍 常见问题

### Q1: 如何调试 token 是否保存成功？
```javascript
// 在浏览器控制台输入
localStorage.getItem('authToken')
// 如果有值说明保存成功
```

### Q2: 文件上传时后端报错怎么办？
- 检查 `Content-Type: multipart/form-data` 是否正确设置
- 检查后端是否用 `@RequestParam("attachments")` 接收
- 后端可能需要添加 `@CrossOrigin` 跨域注解

### Q3: 登录后访问其他页面报 401 怎么办？
- 检查 token 是否过期
- axiosConfig.js 中自动处理 401，会跳回登录页
- 可以在后端延长 token 有效期

### Q4: 邮件列表显示为空怎么办？
- 检查后端返回数据格式是否与前端一致
- 打开浏览器开发者工具 → Network → 查看 API 返回的 JSON
- 确保前端的 `res.data?.mails` 路径对应后端返回结构

---

## 📝 后续改进方向

1. **搜索功能** - 在 `GET /api/mails?page=1&pageSize=10&keyword=xxx` 中加 query 参数
2. **详情页面** - 新建 MailDetailView.vue 查看完整邮件
3. **草稿箱** - 增加 draft 状态和对应接口
4. **错误处理** - 完善异常提示和重试机制
5. **加载状态** - 表格中添加骨架屏或空状态提示

---

Good luck! 🚀
