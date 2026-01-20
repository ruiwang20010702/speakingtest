# Parent H5 (家长端)

移动端 H5 应用，家长通过老师分享的链接查看孩子的深度 AI 口语测评报告。

## 🌟 核心功能

- **五维能力图谱**：基于 Recharts 动态生成的雷达图，展示流利度、发音、自信度、词汇、整句输出五维能力。
- **Part 1 核心词汇**：单词发音红绿灯展示（Perfect/Unclear/Failed），点击可查看详细评分。
- **Part 2 对话复盘**：查看最佳回答与待提升回答，支持逐题录音回放与 AI 评语查看。
- **AI 汇总建议**：基于 Qwen-Plus 深度分析生成的个性化学习亮点、短板及本周练习计划。
- **IP 互动体验**：贯穿全程的可爱猴子 IP 动画，营造轻松的阅读氛围。
- **免登入查看**：通过加密 Token 链接直接访问，适配微信分享。

## 🛠️ 技术栈

- **Framework**: React 19
- **Build Tool**: Vite 6
- **UI Styling**: Tailwind CSS 4
- **Animation**: Framer Motion
- **Charts**: Recharts (雷达图)
- **Icons**: Lucide React

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

访问地址: `http://localhost:3000` (默认端口)

### 3. 构建生产版本

```bash
npm run build
```

## 📂 项目结构

```
parent-h5/
├── src/
│   ├── components/      # 业务组件 (RadarChart, AudioPlayer, Monkey, etc.)
│   ├── pages/           # 页面 (Cover, Radar, Vocab, Dialogue, Roadmap, Badge)
│   ├── context/         # 状态管理 (ReportContext)
│   ├── assets/          # 图片与静态资源
│   └── types/           # 报告数据类型定义
├── vite.config.ts       # Vite 配置
└── tailwind.config.js   # 样式配置
```

## 🎨 设计规范

- **主色调 (Klein Blue)**: `#002FA7` (用于强调、按钮、标题)
- **辅助色 (Baby Yellow)**: `#FFF59D` (用于背景、高亮)
- **设计风格**: 现代简约，结合动态插画与微交互。

## 🔗 API 交互

家长端通过加密 Token 获取报告数据：
`GET /api/v1/reports/shared/{token}`
数据包含学生信息、总分、维度分、单题详情及 AI 建议。
