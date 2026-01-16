# Student H5 (学生端)

移动端 H5 应用，为学生提供口语测评的答题入口。支持单词朗读 (Part 1) 和开放式问答 (Part 2)。

## 🌟 核心功能

- **扫码登录**：通过一次性 Token 快速进入测评。
- **设备检测**：自动检测麦克风权限与可用性。
- **Part 1 答题**：
  - 单词卡片展示
  - 实时录音与波形反馈
  - 自动提交与下一题跳转
- **Part 2 答题**：
  - 场景图片展示与问题播放
  - 倒计时机制
  - 长语音录制与上传
- **结果反馈**：完成测评后展示感谢页。

## 🛠️ 技术栈

- **Framework**: React 18
- **Build Tool**: Vite
- **UI Styling**: Tailwind CSS
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
│   ├── pages/          # 页面组件 (Part1, Part2, Welcome, etc.)
│   ├── services/       # API 封装
│   ├── types/          # TypeScript 类型定义
│   ├── App.tsx         # 路由配置
│   └── main.tsx        # 入口文件
├── public/             # 静态资源
└── vite.config.ts      # Vite 配置 (包含 API 代理)
```

## ⚠️ 注意事项

- **HTTPS**: 移动端浏览器录音权限通常要求 HTTPS 环境。开发时可使用 localhost，但在真机测试时需注意。
- **iOS 兼容性**: 录音格式为 WebM，在部分旧版 iOS Safari 上可能需要 Polyfill 或后端转码支持（后端 Qwen API 支持 WebM）。
