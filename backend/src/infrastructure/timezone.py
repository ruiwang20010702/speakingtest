"""
时区配置 - 统一使用东八区时间（北京时间）
"""
from datetime import datetime, timezone, timedelta

# 东八区时区 (UTC+8)
CHINA_TZ = timezone(timedelta(hours=8))


def now() -> datetime:
    """获取当前东八区时间"""
    return datetime.now(CHINA_TZ)


def utc_to_china(dt: datetime) -> datetime:
    """将 UTC 时间转换为东八区时间"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # 假设无时区的时间是 UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CHINA_TZ)


def china_to_utc(dt: datetime) -> datetime:
    """将东八区时间转换为 UTC 时间"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # 假设无时区的时间是东八区
        dt = dt.replace(tzinfo=CHINA_TZ)
    return dt.astimezone(timezone.utc)
