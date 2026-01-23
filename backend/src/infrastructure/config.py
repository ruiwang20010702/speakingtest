"""
Application Configuration
Loads settings from environment variables with sensible defaults.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # App
    APP_NAME: str = "Speaking Test System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Frontend URLs
    FRONTEND_STUDENT_URL: str = "http://localhost:3001/s"  # Student H5 entry path
    FRONTEND_PARENT_URL: str = "http://localhost:3000"     # Parent H5
    FRONTEND_TEACHER_URL: str = "http://localhost:3002"    # Teacher Web
    
    # CORS (逗号分隔的允许域名，生产环境应配置具体域名)
    CORS_ORIGINS: str = ""  # 为空时允许所有域名（仅限开发环境）
    
    # 测试邮箱白名单 (逗号分隔，允许非 @51talk.com 邮箱登录)
    TEST_EMAIL_WHITELIST: str = ""  # 仅限测试环境使用
    
    # 管理员邮箱列表 (逗号分隔)
    ADMIN_EMAILS: str = ""  # 例如: "admin1@51talk.com,admin2@51talk.com"
    
    # CRM Mock 模式 (设为 true 则使用假数据，不调用真实 CRM API)
    USE_MOCK_CRM: bool = False
    
    # 测试认证模式 (设为 true 启用魔法验证码 888888 和测试邮箱白名单)
    ENABLE_TEST_AUTH: bool = False

    # 学生入口 Token 重复使用 (生产环境应为 False，防止链接泄露后被多次使用)
    ENABLE_TOKEN_REENTRY: bool = False

    # Database (PostgreSQL)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/speakingtest"
    DB_POOL_SIZE: int = 30  # 基础连接池大小（匹配数据库支持 100 并发）
    DB_MAX_OVERFLOW: int = 70  # 最大溢出连接数（总计最多 100 个连接）

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Cookie Security (httpOnly Cookie 替代 localStorage)
    COOKIE_NAME: str = "access_token"            # Cookie 名称
    COOKIE_DOMAIN: str = ""                      # Cookie 域名（为空时使用请求域名）
    COOKIE_SECURE: bool = True                   # 仅 HTTPS（生产环境必须为 True）
    COOKIE_SAMESITE: str = "lax"                 # SameSite 策略: strict/lax/none
    COOKIE_PATH: str = "/api"                    # Cookie 路径（仅 API 请求携带）

    # Xunfei API
    XUNFEI_APP_ID: str = ""
    XUNFEI_API_KEY: str = ""
    XUNFEI_API_SECRET: str = ""
    XUNFEI_MAX_CONCURRENT: int = 50  # API concurrency limit

    # Qwen API
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen3-omni-flash"  # 用于音频评测 (Part1/Part2)
    QWEN_PLUS_MODEL: str = "qwen-plus"     # 用于文本分析 (测评汇总/报告解读)
    QWEN_ENABLE_THINKING: bool = True      # 开启思考模式 (提高评测准确性)
    QWEN_THINKING_BUDGET: int = 2048       # 思考 token 上限
    
    # Qwen 并发与限速配置 (可根据账号配额调整)
    # qwen3-omni-flash: 默认 5 并发，60 RPM
    QWEN_OMNI_CONCURRENCY: int = 5         # omni 模型最大并发数
    QWEN_OMNI_RPM: int = 60                # omni 模型每分钟请求数
    # qwen-plus: 默认 10 并发，600 RPM
    QWEN_PLUS_CONCURRENCY: int = 10        # plus 模型最大并发数
    QWEN_PLUS_RPM: int = 600               # plus 模型每分钟请求数
    
    # 消费者配置
    QUEUE_PREFETCH_MULTIPLIER: int = 1     # prefetch = concurrency * multiplier
    QUEUE_DISABLE_SLEEP: bool = False      # 压测模式：禁用 sleep（仅限测试环境）

    # Aliyun OSS
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_ENDPOINT: str = ""
    OSS_BUCKET_NAME: str = ""
    
    # 上传性能配置
    UPLOAD_MAX_CONCURRENT: int = 20     # 最大并发上传数（防止内存爆炸）
    UPLOAD_MAX_SIZE_MB: int = 20        # 单文件最大大小（MB）

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # SMTP Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "51Talk 口语测评"
    SMTP_USE_SSL: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
