# 学生口语测试系统

基于 Gemini 2.5 Flash AI 的智能口语评分系统。

## 功能特点

- 🎤 **录音测试**：浏览器内录音，无需安装插件
- 🤖 **AI 智能评分**：使用 Google Gemini 2.5 Flash 直接分析音频
- 📊 **量化评分**：60分制量化评分 + 5星评级
- 📈 **详细反馈**：AI 提供发音、流畅度、准确性的详细反馈
- 📝 **历史记录**：保存学生的测试历史

## 技术栈

### 后端
- **FastAPI** - Python Web 框架
- **SQLite** - 轻量级数据库
- **Gemini 2.5 Flash** - Google AI 音频分析

### 前端
- **React 18** - UI 框架
- **Vite** - 构建工具
- **TypeScript** - 类型安全

## 快速开始

### 1. 后端设置

```bash
cd server

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 Gemini API Key
```

### 2. 启动后端

```bash
cd server
uvicorn main:app --reload
```

后端将运行在 `http://localhost:8000`

API 文档：`http://localhost:8000/docs`

### 3. 前端设置（即将完成）

```bash
cd client
npm install
npm run dev
```

前端将运行在 `http://localhost:5173`

## 获取 Gemini API Key

1. 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 创建 API Key
3. 复制到 `server/.env` 文件的 `GEMINI_API_KEY` 变量

## 评分标准

### 量化评分系统（总分60分）

- **Part 1 - 词汇朗读**：20分（20个单词，每个1分）
- **Part 2 - 自然拼读**：16分（12个单词6分 + 4个句子10分）
- **Part 3 - 句子问答**：24分（12个问题，每个2分）

### 星级转换

- ⭐⭐⭐⭐⭐ 5星：56-60分（杰出）
- ⭐⭐⭐⭐ 4星：48-55分（优秀）
- ⭐⭐⭐ 3星：30-47分（良好）
- ⭐⭐ 2星：1-29分（中等）
- ⭐ 1星：0分（需努力）

## 项目结构

```
speakingtest/
├── server/                     # 后端
│   ├── main.py                 # FastAPI 入口
│   ├── database.py             # 数据库配置
│   ├── models.py               # 数据库模型
│   ├── schemas.py              # Pydantic 模型
│   ├── api/                    # API 路由
│   │   ├── questions.py        # 题目 API
│   │   ├── audio.py            # 音频 API
│   │   └── scoring.py          # 评分 API
│   ├── services/               # 业务逻辑
│   │   ├── gemini_client.py    # Gemini 客户端
│   │   └── gemini_scorer.py    # AI 评分服务
│   └── requirements.txt
├── client/                     # 前端（开发中）
├── test_questions_level1.json  # Level 1 题库
├── scoring_rubric.json         # 评分标准
└── README.md
```

## API 接口

### 获取题目
```
GET /api/questions/{level}/{unit}
```

### 上传音频
```
POST /api/audio/upload
```

### 评分
```
POST /api/scoring/evaluate
Form Data:
  - student_name: 学生姓名
  - level: 级别（如 level1）
  - unit: 单元（如 unit1-3）
  - part1_audio: Part 1 音频文件
  - part2_audio: Part 2 音频文件
  - part3_audio: Part 3 音频文件
```

### 获取历史记录
```
GET /api/scoring/history/{student_name}
```

## 开发计划

- [x] 后端 API 实现
- [x] Gemini AI 评分集成
- [x] SQLite 数据库
- [ ] React 前端界面
- [ ] 录音功能
- [ ] 结果展示页面
- [ ] 历史记录查询

## 许可证

MIT License
