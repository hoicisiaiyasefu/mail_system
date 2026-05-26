# Mail System 邮件系统

## 项目简介

本项目为 Java Web 实训项目，目标是开发一个简易邮件系统，实现：

- 用户登录注册
- 邮件发送
- 收件箱
- 文件附件上传
- 垃圾邮件识别
- AI 辅助功能（后续）

---

# 技术栈

## 后端

- Java 17
- Spring Boot 3
- MySQL
- JPA / Hibernate
- Maven

## 前端

- Vue 3
- Vite
- Element Plus
- Axios

## AI / Python

- Python
- 朴素贝叶斯垃圾邮件分类
- 大模型 API（DeepSeek/OpenAI）

---

# 项目目录结构

```text
mail_system
│
├── backend                # SpringBoot 后端
│
├── frontend               # Vue3 前端
│
├── docs                   # 文档
│
├── sql                    # 数据库 SQL 文件
│
├── test                   # 测试相关文件
│
└── README.md

# 开发目录说明（重要）

## backend 后端目录

```text
backend
├── src/main/java/com/example/backend
│   ├── controller     # 接口层
│   ├── service        # 业务逻辑
│   ├── repository     # JPA数据库操作
│   ├── entity         # 数据库实体类
│   └── config         # 配置类
后端 A

负责：

entity/
repository/

主要内容：

用户表
邮件表
数据库设计

后端 B

负责：

controller/
service/

主要内容：

文件上传
邮件发送接口
SpringBoot接口开发

后端 C

负责：

backend/python/

或者：

backend/ai/

主要内容：

Python垃圾邮件识别
大模型API

##frontend 前端目录

```text
frontend
├── src
│   ├── views          # 页面
│   ├── components     # 组件
│   ├── api            # Axios接口
│   ├── router         # 路由
│   └── assets         # 静态资源
前端 D

负责：

views/
components/

主要内容：

登录页
收件箱
写信页
前端 E

负责：

api/
router/

主要内容：

Axios请求
前后端联调
API字段

##docs 文档目录

```text
docs
├── api.md
├── requirement.md
└── weekly-report.md

测试 F

负责：

API文档
测试计划
周报
项目管理
GitHub维护

##SQL目录

```text
sql
├── init.sql
├── user.sql
└── mail.sql

数据库脚本统一放这里。
