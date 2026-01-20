# Student H5 (学生端)

移动端 H5 应用，为学生提供游戏化的口语测评答题界面。支持核心词汇朗读 (Part 1) 和对话问答 (Part 2)。

## 🌟 核心功能

- **免登入直达**：通过老师生成的专属二维码/链接（一次性 Token）快速进入测评。
- **游戏化引导**：贯穿全程的 IP 形象引导与即时反馈，降低学生紧张感。
- **Part 1 核心词汇**：
  - 单词卡片展示与图片辅助。
  - 实时录音与波形反馈。
  - 左右滑动翻页，支持单词重读。
- **Part 2 对话问答**：
  - 模拟真实教学场景的问题自动播放。
  - 长语音录制与上传。
  - 录音期间支持滑动查看历史问题。
- **即时反馈**：完成测评后立即展示 Part 1 得分，并引导联系老师获取深度报告。

## 🛠️ 技术栈

- **Framework**: React 19
- **Build Tool**: Vite 6
- **UI Styling**: Tailwind CSS 4
- **Audio**: Web Audio API (录音与可视化)
- **HTTP**: Axios (与后端交互)

## 🚀 快速启动

### 1. 安装依赖

```bash
cd frontend/student-h5
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问地址: `http://localhost:3001` (默认端口)

### 3. 构建生产版本

```bash
npm run build
```

## 📂 项目结构

```
student-h5/
├── src/
│   ├── components/     # UI 组件 (AudioRecorder, ProgressBar, etc.)
│   ├── pages/          # 页面组件 (EntryPage, TestPage, ResultPage, etc.)
│   ├── services/       # API 封装 (api.ts)
│   ├── types/          # TypeScript 类型定义
│   ├── App.tsx         # 路由配置
│   └── main.tsx        # 入口文件
├── public/             # 静态资源 (IP 动画、音频等)
└── vite.config.ts      # Vite 配置 (包含 API 代理)
```

## ⚠️ 注意事项

- **HTTPS**: 移动端浏览器录音权限通常要求 HTTPS 环境。开发时可使用 localhost，但在真机测试时需注意。
- **iOS 兼容性**: 录音格式为 WebM/WAV，在部分旧版 iOS Safari 上可能需要 Polyfill。
- **音频播放**: 浏览器通常要求用户交互后才能播放音频，系统已在进入测试页时通过点击按钮触发。
