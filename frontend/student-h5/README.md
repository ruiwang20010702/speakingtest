# Student H5 (学生端)

微信 H5 应用，学生通过老师发送的链接进入，完成 Part 1 朗读和 Part 2 问答测评。

## 技术栈 (推荐)

- **Framework**: Vue 3 (轻量)
- **UI Library**: Vant (移动端组件库)
- **Build Tool**: Vite
- **Audio**: MediaRecorder API

## 页面列表

1. **入口页** - Token 验证，显示学生信息和任务
2. **Part 1 朗读** - 显示文本，录音并实时上传（讯飞 WebSocket）
3. **Part 2 问答** - 显示问题，一次性录音后提交
4. **结果页** - 显示 Part 1 分数，引导联系老师获取完整报告

## 注意事项

- 需要 HTTPS 才能使用 MediaRecorder
- 需要处理微信 JSSDK 兼容性

## 启动 (待实现)

```bash
npm install
npm run dev
```
