# Mail System 邮件系统

Java Web 综合实训项目

---

# 项目简介

本项目是一套简易邮件管理系统，基于前后端分离架构开发。  
主要实现用户账号管理、邮件收发、附件上传、垃圾邮件识别等基础功能，并预留 AI 辅助能力扩展接口。

## 核心功能

- 用户注册、登录
- 邮件撰写、发送、接收
- 收件箱管理
- 邮件附件上传
- 垃圾邮件识别
- AI 辅助功能（后续迭代开发）

---

# 技术栈

## 后端技术

- 编程语言：Java 17
- 框架：Spring Boot 3
- 数据库：MySQL 8.0
- 持久层：Spring Data JPA / Hibernate
- 项目构建：Maven

## 前端技术

- 框架：Vue 3 + Vite
- UI 组件库：Element Plus
- 网络请求：Axios

## AI 扩展模块

- 编程语言：Python
- 算法：朴素贝叶斯（垃圾邮件分类）
- 大模型：DeepSeek / OpenAI API 对接

---

# 整体目录结构

```text
mail_system
├── backend        # SpringBoot 后端项目
├── frontend       # Vue3 前端项目
├── docs           # 项目相关文档
├── sql            # 数据库初始化脚本
├── test           # 测试相关文件
└── README.md      # 项目说明文档
```

---

# 各模块目录与开发分工

## 一、后端 backend

```text
backend
└── src/main/java/com/example/backend
    ├── controller     # 接口层：接收前端请求
    ├── service        # 业务逻辑层
    ├── repository     # 数据访问层（JPA）
    ├── entity         # 数据库实体类
    ├── config         # 全局配置类
    └── ai             # Python 调用、大模型、垃圾邮件识别模块
```

### 人员分工

#### 后端 A

- 负责目录：`entity`、`repository`
- 工作内容：数据库表设计、用户实体、邮件实体、数据访问层开发

#### 后端 B

- 负责目录：`controller`、`service`
- 工作内容：业务逻辑编写、接口开发、邮件发送、文件上传功能实现

#### 后端 C

- 负责目录：`ai`
- 工作内容：Python 垃圾邮件分类、大模型 API 对接与调用

---

## 二、前端 frontend

```text
frontend
└── src
    ├── views         # 页面视图
    ├── components    # 公共组件
    ├── api           # Axios 请求封装
    ├── router        # 路由配置
    └── assets        # 静态资源（图片、样式等）
```

### 人员分工

#### 前端 D

- 负责目录：`views`、`components`
- 工作内容：登录页、收件箱、写信页等页面及公共组件开发

#### 前端 E

- 负责目录：`api`、`router`
- 工作内容：路由配置、Axios 接口封装、前后端接口联调

---

## 三、文档 & 数据库 & 测试

### docs 项目文档

```text
docs
├── api.md             # 后端接口文档
├── requirement.md     # 需求文档
└── weekly-report.md   # 开发周报
```

### sql 数据库脚本

统一存放数据库 SQL 脚本：

- `init.sql` 数据库初始化语句
- `user.sql` 用户表脚本
- `mail.sql` 邮件表脚本

### test 测试目录

存放单元测试、接口测试、功能测试相关文件。

#### 测试 / 文档 F

- 负责内容：文档编写、测试计划、API 整理、周报、GitHub 仓库维护

---

# Git 开发规范

## 1. 每日开发前同步远程代码

```bash
git pull origin main
```

---

## 2. 代码提交流程

```bash
git add .
git commit -m "此处填写本次提交说明"
git push origin main
```

---

## 3. 禁止提交的文件

已配置 `.gitignore` 自动忽略以下内容：

- 前端依赖：`node_modules`
- 后端编译目录：`target`
- IDE 配置：`.idea`
- 临时上传文件
- Python 虚拟环境
- 大模型本地文件等

---

# 项目启动方式

## 1. 启动后端（Spring Boot）

进入后端目录执行命令：

```bash
cd backend
mvn spring-boot:run
```

后端访问地址：

```text
http://localhost:8080
```

---

## 2. 启动前端（Vue3）

进入前端目录，先安装依赖再启动：

```bash
cd frontend
npm install
npm run dev
```

前端访问地址：

```text
http://localhost:5173
```
