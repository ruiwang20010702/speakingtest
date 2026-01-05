# Parent H5 (家长端)

微信 H5 应用，家长通过老师分享的链接查看孩子的测评报告。

## 技术栈 (推荐)

- **Framework**: Vue 3 (轻量)
- **UI Library**: Vant (移动端组件库)
- **Build Tool**: Vite

## 页面列表

1. **报告页** - 通过 Token 访问，显示完整测评报告（分数、星级、逐题评语）

## 注意事项

- 页面为只读，无需登录
- 需要处理 Token 过期/撤回的错误提示

## 启动 (待实现)

```bash
npm install
npm run dev
```
