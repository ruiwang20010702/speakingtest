# Teacher Web (教师端)

PC 端管理后台，供教师和管理员使用。提供学生管理、测评监控、AI 报告解读及系统运维功能。

## 🌟 核心功能

- **数据看板 (Dashboard)**：实时监控学生总数、测评完成率、分享率及家长打开率。
- **学生管理 (Student List)**：
  - 对接 CRM 自动同步学生档案。
  - 一键生成学生专属测评二维码/链接。
  - 查看学生历史测评记录。
- **报告与解读 (Report & Interpretation)**：
  - 查看 AI 生成的详细评分、转写及维度分析。
  - **AI 解读助手**：自动生成针对家长的 10 分钟报告解读演讲稿。
  - **报告分享**：一键生成家长端加密分享链接。
- **系统运维 (Admin)**：
  - **成本监控**：实时查看 AI 调用产生的 Token 消耗与 RMB 成本。
  - **任务重试**：监控并一键重试失败或超时的测评任务。
  - **审计日志**：追踪系统关键操作记录。

## 🛠️ 技术栈

- **Framework**: React 19
- **Build Tool**: Vite 7 (Rolldown)
- **UI Styling**: Tailwind CSS 3
- **State Management**: Zustand
- **Charts**: Recharts
- **Icons**: Lucide React
- **HTTP**: Axios

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
│   ├── components/      # 通用 UI 组件
│   ├── pages/           # 页面组件
│   │   ├── Admin/       # 管理员功能 (看板、成本、任务、日志)
│   │   ├── Assessment/  # 测评管理
│   │   ├── Report/      # 报告详情
│   │   ├── Interpretation/ # AI 解读页
│   │   └── StudentList/ # 学生管理
│   ├── store/           # Zustand 状态管理
│   └── App.tsx          # 路由入口
└── vite.config.ts       # Vite 配置
```

## 🔐 权限说明

- **Admin**: 拥有全局数据看板、成本统计、任务重试及审计日志查看权限。
- **Teacher**: 仅可管理自己名下的学生、查看测评报告并生成分享链接。
