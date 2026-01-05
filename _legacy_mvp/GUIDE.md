# 口语测试系统 MVP - 使用指南

## 🎉 已完成功能

### ✅ 后端 (FastAPI + Gemini 2.5 Flash)
- **数据库**: SQLite 轻量级数据库
- **AI 评分**: Gemini 2.5 Flash 音频分析
- **API 接口**:
  - `GET /api/questions/levels` - 获取级别列表
  - `GET /api/questions/{level}/{unit}` - 获取题目
  - `POST /api/audio/upload` - 上传音频
  - `POST /api/scoring/evaluate` - AI 评分
  - `GET /api/scoring/history/{student}` - 历史记录
- **评分系统**: 60分制量化评分 + 5星评级
- **题库数据**: Level 1 完整题库（Unit 1-3 和 Unit 4-8）

### ✅ 前端 (React + Vite + TypeScript)
- **录音组件**: MediaRecorder API 浏览器录音
- **首页**: 学生信息输入 + 级别选择
- **API 客户端**: Axios 封装
- **现代化 UI**: 渐变背景 + 玻璃态卡片 + 动画

---

## 🚀 快速开始

### 1. 获取 Gemini API Key

访问 [Google AI Studio](https://aistudio.google.com/app/apikey) 创建 API Key

### 2. 后端设置

```bash
# 进入后端目录
cd server

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 GEMINI_API_KEY
```

### 3. 启动后端

```bash
cd server
uvicorn main:app --reload
```

后端运行在: `http://localhost:8000`  
API 文档: `http://localhost:8000/docs`

### 4. 前端设置

```bash
# 进入前端目录
cd client

# 安装依赖（如果还没安装）
npm install
```

### 5. 启动前端

```bash
cd client
npm run dev
```

前端运行在: `http://localhost:5173`

---

## 📋 测试流程（当前MVP）

### 当前可测试的功能：

1. **首页** ✅
   - 输入学生姓名
   - 选择级别（Level 1）
   - 选择单元（Unit 1-3 或 Unit 4-8）

2. **后端 API** ✅
   - 访问 http://localhost:8000/docs
   - 测试获取题目: `GET /api/questions/level1/unit1-3`
   - 查看完整的 API 文档和在线测试

3. **录音组件** ✅
   - 在开发者工具中可以测试 AudioRecorder 组件
   - 支持开始录音、停止、播放、重录

### 待完成的功能：

- ⏳ 测试页面（显示题目 + 三个部分录音）
- ⏳ 结果页面（显示评分 + 星级 + 详细反馈）
- ⏳ 历史记录页面

---

## 🎯 完整测试流程（规划）

一旦所有组件完成，完整流程将是：

1. **首页**: 输入"张三"，选择"Level 1 - Unit 1-3"，点击"开始测试"

2. **测试页 - Part 1**: 
   - 显示20个单词
   - 点击"开始录音"朗读这些单词
   - 点击"停止录音"
   - 可以播放检查，不满意可以"重新录音"
   - 点击"下一步"

3. **测试页 - Part 2**:
   - 显示12个单词 + 4个句子
   - 录音朗读
   - 点击"下一步"

4. **测试页 - Part 3**:
   - 显示12个问题，每个问题单独录音
   - 逐个回答所有问题
   - 点击"提交评分"

5. **等待 Gemini 分析**:
   - 显示加载动画
   - 后台调用 Gemini 2.5 Flash 分析三个音频

6. **结果页**:
   - 显示总分（/60）
   - 显示星级（⭐⭐⭐⭐⭐）
   - 显示三个部分的详细得分
   - 显示 Gemini 的反馈建议
   - 选项：重新测试 / 查看历史记录

---

## 🧪 手动 API 测试

### 1. 测试获取题目

```bash
curl http://localhost:8000/api/questions/level1/unit1-3
```

### 2. 测试上传音频并评分

使用 API 文档界面: http://localhost:8000/docs

1. 找到 `POST /api/scoring/evaluate`
2. 点击 "Try it out"
3. 填写:
   - student_name: 张三
   - level: level1
   - unit: unit1-3
   - part1_audio: (上传音频文件)
   - part2_audio: (上传音频文件)
   - part3_audio: (上传音频文件)
4. 点击 "Execute"

**注意**: 需要准备三个测试音频文件（可以录制一些简单的朗读）

---

## 🏗️ 项目结构

```
speakingtest/
├── server/                          # 后端
│   ├── main.py                      # FastAPI 入口 ✅
│   ├── database.py                  # 数据库配置 ✅
│   ├── models.py                    # 数据模型 ✅
│   ├── schemas.py                   # Pydantic 模型 ✅
│   ├── api/
│   │   ├── questions.py             # 题目 API ✅
│   │   ├── audio.py                 # 音频 API ✅
│   │   └── scoring.py               # 评分 API ✅
│   ├── services/
│   │   ├── gemini_client.py         # Gemini 客户端 ✅
│   │   └── gemini_scorer.py         # AI 评分服务 ✅
│   └── requirements.txt             # Python 依赖 ✅
│
├── client/                          # 前端
│   ├── src/
│   │   ├── components/
│   │   │   └── AudioRecorder.tsx    # 录音组件 ✅
│   │   ├── pages/
│   │   │   └── HomePage.tsx         # 首页 ✅
│   │   ├── services/
│   │   │   └── api.ts               # API 客户端 ✅
│   │   ├── types/
│   │   │   └── index.ts             # 类型定义 ✅
│   │   ├── styles/
│   │   │   └── index.css            # 全局样式 ✅
│   │   └── App.tsx                  # 应用主组件 ✅
│   ├── package.json                 # 依赖管理 ✅
│   └── vite.config.ts               # Vite 配置 ✅
│
├── test_questions_level1.json       # 题库数据 ✅
├── scoring_rubric.json              # 评分标准 ✅
└── README.md                        # 项目文档 ✅
```

---

## 🎨 UI 设计特点

- **渐变背景**: 紫色渐变营造高级感
- **玻璃态卡片**: backdrop-filter 实现半透明效果
- **动画效果**: 
  - 按钮 hover 上浮动画
  - 录音按钮脉冲动画
  - 加载旋转动画
- **响应式设计**: 适配移动端和桌面端

---

## 🔧 故障排除

### 后端启动失败
```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 重新安装依赖
pip install -r requirements.txt

# 检查 GEMINI_API_KEY 是否正确配置
cat .env
```

### 前端无法连接后端
```bash
# 确保后端运行在 8000 端口
# 检查 vite.config.ts 中的代理配置
# 检查浏览器控制台的错误信息
```

### Gemini API 调用失败
- 检查 API Key 是否有效
- 确认账户有可用额度
- 查看后端日志获取详细错误信息

---

## 📊 评分标准

### 量化评分（总分60分）
- **Part 1 - 词汇朗读**: 20分（20个单词 × 1分）
- **Part 2 - 自然拼读**: 16分（12个单词 × 0.5分 + 4个句子 × 2.5分）
- **Part 3 - 句子问答**: 24分（12个问题 × 2分）

### 星级转换
- ⭐⭐⭐⭐⭐ 5星: 56-60分（杰出）
- ⭐⭐⭐⭐ 4星: 48-55分（优秀）
- ⭐⭐⭐ 3星: 30-47分（良好）
- ⭐⭐ 2星: 1-29分（中等）
- ⭐ 1星: 0分（需努力）

---

## 🚀 下一步开发计划

1. **完成前端测试页面** (优先级：高)
   - 三个部分的题目展示
   - 每个部分的录音功能集成
   - 进度条显示

2. **完成结果页面** (优先级：高)
   - 评分展示（总分 + 星级）
   - 详细反馈显示
   - 圆形进度图表

3. **完成历史记录页面** (优先级：中)
   - 列表显示所有测试记录
   - 可点击查看详情

4. **优化和测试** (优先级：中)
   - 错误处理和用户提示
   - 加载状态优化
   - 移动端适配测试

5. **功能增强** (优先级：低)
   - 添加更多级别的题库
   - 导出测试报告（PDF）
   - 数据统计和分析

---

## 📝 许可证

MIT License
