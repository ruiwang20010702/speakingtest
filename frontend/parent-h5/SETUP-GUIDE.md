# 🔧 设置指南

## 问题诊断

之前的项目**缺少 Tailwind CSS 配置**，导致所有样式无法正常显示。

### 原因分析

- ✅ Downloads 版本：使用 **Tailwind CDN**（通过 `<script src="https://cdn.tailwindcss.com"></script>`）
- ❌ parent-h5 项目：缺少 Tailwind CSS 的 npm 包和配置文件

## 已修复的问题

### 1. 添加了 Tailwind CSS 配置文件

**tailwind.config.js** - 配置了自定义颜色和字体
```javascript
{
  colors: {
    klein: '#002FA7',      // Klein Blue
    baby: '#FFF59D',       // Baby Yellow
    babyDark: '#FBC02D',   // Baby Yellow Dark
  }
}
```

### 2. 添加了 PostCSS 配置

**postcss.config.js** - 用于处理 Tailwind CSS

### 3. 更新了依赖包

在 `package.json` 中添加了：
- `tailwindcss` - Tailwind CSS 核心
- `postcss` - CSS 处理器
- `autoprefixer` - 自动添加浏览器前缀

## 🚀 启动步骤

### 1. 删除旧的 node_modules（如果存在）

```bash
rm -rf node_modules
rm package-lock.json
```

### 2. 重新安装依赖

```bash
npm install
```

这将安装所有必需的包，包括新添加的 Tailwind CSS。

### 3. 启动开发服务器

```bash
npm run dev
```

### 4. 访问应用

打开浏览器访问 http://localhost:3000

## ✨ 预期效果

现在你应该能看到：

- 🎨 **Klein Blue 背景** (#002FA7)
- 💛 **Baby Yellow 强调色** (#FFF59D)
- 🐵 **可爱的猴子 IP 形象**
- ✨ **流畅的页面切换动画**
- 📊 **精美的数据可视化**
- 🎭 **所有 Tailwind 样式类正常工作**

## 📋 验证清单

启动后检查以下内容：

- [ ] 背景是 Klein Blue 蓝色（不是白色或其他颜色）
- [ ] 文字和按钮有正确的颜色和样式
- [ ] 可以通过滑动手势切换页面
- [ ] 猴子形象正常显示
- [ ] 所有动画效果流畅
- [ ] 词汇卡片、雷达图等组件样式正确

## 🔍 如果还有问题

### 清除缓存并重启

```bash
# 停止开发服务器 (Ctrl+C)
# 删除 Vite 缓存
rm -rf node_modules/.vite

# 重新启动
npm run dev
```

### 检查浏览器控制台

打开开发者工具 (F12)，查看是否有错误信息。

### 验证 Tailwind 是否工作

在浏览器中检查任何元素，应该能看到 Tailwind 生成的 CSS 类。

## 📁 关键文件说明

| 文件 | 作用 |
|------|------|
| `tailwind.config.js` | Tailwind CSS 配置（颜色、字体等） |
| `postcss.config.js` | PostCSS 配置（处理 Tailwind） |
| `src/index.css` | 全局样式和 Tailwind 指令 |
| `package.json` | 项目依赖（包含 Tailwind） |

## 🎉 完成！

现在你的项目应该和 Downloads 版本的设计完全一致了！

