"""
数据库配置 - 支持 SQLite 和 PostgreSQL
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Zeabur 会自动注入 POSTGRES_URI 环境变量用于内部连接
# 本地开发使用 SQLite
DATABASE_URL = os.getenv("POSTGRES_URI") or os.getenv("DATABASE_URL", "sqlite:///./speakingtest.db")

# SQLite 需要特殊的连接参数
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """初始化数据库表"""
    # 导入所有模型以确保它们被注册
    import models  # noqa
    Base.metadata.create_all(bind=engine)
    print(f"✅ 数据库表已创建: {DATABASE_URL[:50]}...")


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
