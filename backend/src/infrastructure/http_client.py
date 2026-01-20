"""
全局 HTTP 客户端连接池

避免每次请求创建新的 AsyncClient，复用连接池提高性能。
所有外部 HTTP 请求应使用这个模块。
"""
import httpx
from typing import Optional

# 全局客户端实例
_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """
    获取全局 HTTP 客户端（延迟初始化）
    
    特性:
    - 连接池复用
    - 默认超时 30 秒
    - HTTP/2 支持
    
    Returns:
        全局 httpx.AsyncClient 实例
    """
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,    # 连接超时
                read=30.0,       # 读取超时
                write=30.0,      # 写入超时
                pool=10.0,       # 连接池获取超时
            ),
            limits=httpx.Limits(
                max_keepalive_connections=20,  # 保持活跃连接数
                max_connections=100,            # 最大连接数
                keepalive_expiry=30.0,          # 连接保活时间
            ),
            http2=True,  # 启用 HTTP/2
        )
    return _client


async def close_http_client():
    """关闭全局 HTTP 客户端（应用关闭时调用）"""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
