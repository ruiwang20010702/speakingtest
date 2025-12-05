"""
FastAPI 主应用
学生口语测试系统后端
使用 Gemini 2.5 Flash 进行音频分析评分
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from database import engine, Base
from api import questions, audio, scoring

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 应用
app = FastAPI(
    title="Speaking Test API",
    description="学生口语测试系统 API - 使用 Gemini 2.5 Flash 进行智能评分",
    version="1.0.0"
)

# CORS 配置（允许前端跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # 前端开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(questions.router)
app.include_router(audio.router)
app.include_router(scoring.router)

# 静态文件服务（音频文件）
uploads_dir = Path("./uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "message": "Speaking Test API",
        "version": "1.0.0",
        "ai_model": "Gemini 2.5 Flash",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
