# Parent H5 (家长端)

微信 H5 应用，家长通过老师分享的链接查看孩子的测评报告。

## 技术栈

- **Framework**: React 19
- **UI Library**: Tailwind CSS
- **Animation**: Framer Motion
- **Icons**: Lucide React
- **Charts**: Recharts
- **Build Tool**: Vite
- **Language**: TypeScript

## 项目结构

```
parent-h5/
├── src/
│   ├── components/          # 可复用组件
│   │   ├── layout.tsx       # 页面布局容器
│   │   ├── monkey.tsx       # 猴子 IP 形象组件
│   │   ├── advice-card.tsx  # 建议卡片
│   │   ├── audio-waveform.tsx
│   │   ├── chat-bubble.tsx
│   │   ├── detail-panel.tsx
│   │   ├── dialogue-card.tsx
│   │   ├── info-card.tsx
│   │   └── waveform-bubble.tsx
│   ├── pages/               # 页面组件
│   │   ├── cover.tsx        # 封面页
│   │   ├── radar.tsx        # 雷达图页
│   │   ├── vocab.tsx        # 词汇能量站页
│   │   ├── dialogue.tsx     # 对话能力表现页
│   │   ├── roadmap.tsx      # 课程配比建议页
│   │   └── badge.tsx        # 徽章页
│   ├── types.ts             # TypeScript 类型定义
│   ├── App.tsx              # 主应用组件
│   ├── main.tsx             # 应用入口
│   └── index.css            # 全局样式
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## 页面列表

1. **封面页 (Cover)** - 报告封面，显示学生信息和总体评分
2. **雷达图页 (Radar)** - 多维度能力雷达图展示
3. **词汇能量站 (Vocab)** - 词汇掌握情况可视化展示
4. **对话能力表现 (Dialogue)** - 最佳/待提升样本对比分析
5. **课程配比建议 (Roadmap)** - 学习计划和课程建议
6. **徽章页 (Badge)** - 成就展示和分享

## 功能特性

- ✨ 流畅的页面切换动画（支持滑动手势）
- 🎨 Klein Blue + Baby Yellow 配色方案
- 📱 移动端优先的响应式设计
- 🐵 可爱的猴子 IP 形象贯穿全程
- 📊 丰富的数据可视化展示
- 🎭 精美的动画效果和交互体验

## 启动项目

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 设计规范

### 颜色变量

- `--color-klein`: #002FA7 (Klein Blue)
- `--color-baby`: #FFF59D (Baby Yellow)
- `--color-baby-dark`: #FBC02D (Baby Yellow Dark)

### CSS 工具类

- `.bg-klein` / `.text-klein` - Klein Blue 背景/文字
- `.bg-baby` / `.text-baby` - Baby Yellow 背景/文字
- `.bg-babyDark` / `.text-babyDark` - Baby Yellow Dark 背景/文字

## 注意事项

- 页面为只读，无需登录
- 需要处理 Token 过期/撤回的错误提示
- 所有组件使用 kebab-case 命名规范
- 路径别名 `@/` 指向 `src/` 目录

## 开发规范

- 组件文件使用 kebab-case 命名（如 `audio-waveform.tsx`）
- 组件名使用 PascalCase（如 `AudioWaveform`）
- 使用 TypeScript 进行类型检查
- 遵循 React Hooks 最佳实践
