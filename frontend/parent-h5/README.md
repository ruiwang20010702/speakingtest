# Parent H5 (家长端)

微信 H5 应用，家长通过老师分享的链接查看孩子的 AI 口语测评报告。

## 🌟 核心功能

- **多维雷达图**：展示流利度、发音、自信度、词汇、整句输出五维能力。
- **Part 1 详情**：单词发音红绿灯展示（Perfect/Unclear/Failed）。
- **Part 2 复盘**：查看最佳回答与待提升回答，试听录音回放。
- **AI 建议**：基于 Qwen-Plus 生成的个性化学习建议与练习计划。
- **IP 互动**：贯穿全程的可爱猴子 IP 动画与引导。

## 🛠️ 技术栈

- **Framework**: React 18
- **UI Library**: Tailwind CSS
- **Animation**: Framer Motion
- **Charts**: Recharts (雷达图)
- **Icons**: Lucide React
- **Build Tool**: Vite

## 🚀 快速启动

### 1. 安装依赖

```bash
cd frontend/parent-h5
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问地址: `http://localhost:3000`

### 3. 构建

```bash
npm run build
```

## 📂 项目结构

```
parent-h5/
├── src/
│   ├── components/      # 业务组件 (RadarChart, AudioPlayer, etc.)
│   ├── pages/           # 页面 (Cover, Radar, Dialogue, Roadmap)
│   ├── assets/          # 图片与静态资源
│   └── types.ts         # 报告数据类型定义
├── vite.config.ts       # Vite 配置
└── tailwind.config.js   # 样式配置
```

## 🎨 设计规范

- **主色调 (Klein Blue)**: `#002FA7` (用于强调、按钮、标题)
- **辅助色 (Baby Yellow)**: `#FFF59D` (用于背景、高亮)
- **字体**: 系统默认无衬线字体，强调清晰易读。

## 🔗 API 交互

家长端主要是一个只读应用，核心接口为：
`GET /api/v1/reports/shared/{token}`
通过 Token 获取完整的 JSON 报告数据进行渲染。
