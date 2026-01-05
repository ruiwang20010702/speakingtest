"""
数据库配置 - 支持 SQLite 和 PostgreSQL
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Zeabur 会自动注入 ZEABUR_SERVICE_ID 等环境变量
# 如果检测到 Zeabur 环境，优先使用 POSTGRES_URI 或 DATABASE_URL
if os.getenv("ZEABUR_SERVICE_ID"):
    DATABASE_URL = os.getenv("POSTGRES_URI") or os.getenv("DATABASE_URL")
    print(f"👉 Detected Zeabur Environment. Using PostgreSQL: {DATABASE_URL}")
else:
    # 本地开发强制使用 SQLite，忽略 .env 中的 PostgreSQL 配置
    DATABASE_URL = "sqlite:///./speakingtest.db"
    print(f"👉 Detected Local Environment. Using SQLite: {DATABASE_URL}")

# 检查是否使用 PostgreSQL 但缺少驱动 (防御性编程)
if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
    try:
        import psycopg2
    except ImportError:
        print("⚠️  psycopg2 module not found. Falling back to local SQLite.")
        DATABASE_URL = "sqlite:///./speakingtest.db"

# SQLite 需要特殊的连接参数
connect_args = {}
if DATABASE_URL and "sqlite" in DATABASE_URL:
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
