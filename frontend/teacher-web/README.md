# Teacher Web (教师端)

PC 端管理后台，供教师和管理员使用。提供班级管理、测评监控、报告审核与手动修正功能。

## 🌟 核心功能

- **班级看板**：查看班级整体测评进度与平均分分布。
- **学生列表**：管理学生信息，生成测评二维码/链接。
- **报告审核**：
  - 查看 AI 生成的详细评分数据。
  - **人工修正**：支持教师手动修改 AI 评分（如流利度、发音分）。
  - **评语编辑**：支持编辑或重写 AI 生成的综合评语。
- **报告分享**：一键生成家长端分享链接。

## 🛠️ 技术栈

- **Framework**: React 18
- **UI Component**: Ant Design (或类似 Admin 组件库)
- **State Management**: Zustand / Context
- **Network**: Axios
- **Build Tool**: Vite

## 🚀 快速启动

### 1. 安装依赖

```bash
cd frontend/teacher-web
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问地址: `http://localhost:5173` (默认端口)

### 3. 构建生产版本

```bash
npm run build
```

## 📂 项目结构

```
teacher-web/
├── src/
│   ├── api/             # 后端 API 接口封装
│   ├── components/      # 通用组件 (Header, Sidebar, etc.)
│   ├── pages/           # 页面组件
│   │   ├── Dashboard/   # 仪表盘
│   │   ├── Class/       # 班级管理
│   │   ├── Report/      # 报告详情与编辑
│   │   └── Login/       # 登录页
│   ├── utils/           # 工具函数
│   └── App.tsx          # 路由入口
└── vite.config.ts       # Vite 配置
```

## 🔐 权限说明

- **Admin**: 拥有所有权限，可管理教师账号。
- **Teacher**: 仅可管理自己班级的学生和报告。
