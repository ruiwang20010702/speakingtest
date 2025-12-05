"""
Gemini API 重试装饰器
处理网络不稳定和地域限制问题
"""
import time
import functools
from typing import Callable, Any

def retry_on_error(max_retries: int = 3, delay: float = 2.0, backoff: float = 2.0):
    """
    重试装饰器，用于处理Gemini API调用失败
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避倍数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_msg = str(e)
                    
                    # 检查是否是地域限制错误
                    if "User location is not supported" in error_msg:
                        print(f"⚠️ 地域限制错误 (尝试 {attempt + 1}/{max_retries + 1}): {error_msg}")
                    else:
                        print(f"⚠️ API调用失败 (尝试 {attempt + 1}/{max_retries + 1}): {error_msg}")
                    
                    if attempt < max_retries:
                        print(f"   等待 {current_delay:.1f} 秒后重试...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        print(f"❌ 达到最大重试次数，放弃")
            
            # 所有重试都失败，抛出最后的异常
            raise last_exception
        
        return wrapper
    return decorator
