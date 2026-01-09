"""
阿里云 OSS 客户端
用于上传和管理学生测评音频文件
"""
import os
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

import oss2
from loguru import logger

from src.infrastructure.config import get_settings

settings = get_settings()


@dataclass
class UploadResult:
    """OSS 上传结果"""
    success: bool
    url: Optional[str] = None
    key: Optional[str] = None
    error: Optional[str] = None


class OSSClient:
    """
    阿里云 OSS 客户端
    
    用于:
    - 上传学生音频 (Part 1/Part 2)
    - 生成访问 URL
    - 管理文件生命周期
    """
    
    def __init__(self):
        self.access_key_id = settings.OSS_ACCESS_KEY_ID
        self.access_key_secret = settings.OSS_ACCESS_KEY_SECRET
        self.endpoint = settings.OSS_ENDPOINT
        self.bucket_name = settings.OSS_BUCKET_NAME
        
        # 初始化 OSS 认证和 Bucket
        self.auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        self.bucket = oss2.Bucket(self.auth, self.endpoint, self.bucket_name)
    
    def _generate_key(self, test_id: int, part: str, extension: str = "mp3") -> str:
        """
        生成 OSS 文件路径
        
        格式: audio/{year}/{month}/{test_id}_{part}_{uuid}.{ext}
        
        Args:
            test_id: 测评 ID
            part: 部分 (part1/part2)
            extension: 文件扩展名
            
        Returns:
            OSS 对象键 (key)
        """
        now = datetime.now(timezone.utc)
        unique_id = str(uuid.uuid4())[:8]
        
        return f"audio/{now.year}/{now.month:02d}/{test_id}_{part}_{unique_id}.{extension}"
    
    async def upload_audio(
        self,
        audio_data: bytes,
        test_id: int,
        part: str,
        extension: str = "mp3"
    ) -> UploadResult:
        """
        上传音频文件到 OSS
        
        Args:
            audio_data: 音频二进制数据
            test_id: 测评 ID
            part: 部分标识 (part1/part2)
            extension: 文件扩展名
            
        Returns:
            UploadResult 包含 URL 或错误信息
        """
        key = self._generate_key(test_id, part, extension)
        
        try:
            # 上传文件 (Run in executor to avoid blocking)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.bucket.put_object(key, audio_data)
            )
            
            if result.status == 200:
                # 生成访问 URL
                url = f"https://{self.bucket_name}.{self.endpoint.replace('https://', '')}/{key}"
                
                logger.info(f"OSS 上传成功: {key}, 大小: {len(audio_data)} bytes")
                
                return UploadResult(
                    success=True,
                    url=url,
                    key=key
                )
            else:
                logger.error(f"OSS 上传失败: status={result.status}")
                return UploadResult(
                    success=False,
                    error=f"上传失败: HTTP {result.status}"
                )
                
        except oss2.exceptions.OssError as e:
            logger.exception(f"OSS 错误: {e}")
            return UploadResult(
                success=False,
                error=str(e)
            )
        except Exception as e:
            logger.exception(f"上传异常: {e}")
            return UploadResult(
                success=False,
                error=str(e)
            )
    
    def get_signed_url(self, key: str, expires: int = 3600) -> str:
        """
        生成带签名的临时访问 URL
        
        Args:
            key: OSS 对象键
            expires: 过期时间（秒），默认 1 小时
            
        Returns:
            带签名的 URL
        """
        return self.bucket.sign_url('GET', key, expires)
    
    def delete_audio(self, key: str) -> bool:
        """
        删除音频文件
        
        Args:
            key: OSS 对象键
            
        Returns:
            是否删除成功
        """
        try:
            self.bucket.delete_object(key)
            logger.info(f"OSS 删除成功: {key}")
            return True
        except Exception as e:
            logger.error(f"OSS 删除失败: {e}")
            return False


# ============================================
# 便捷函数
# ============================================

_oss_client: Optional[OSSClient] = None


def get_oss_client() -> OSSClient:
    """获取 OSS 客户端单例"""
    global _oss_client
    if _oss_client is None:
        _oss_client = OSSClient()
    return _oss_client


async def upload_test_audio(
    audio_data: bytes,
    test_id: int,
    part: str,
    extension: str = "mp3"
) -> UploadResult:
    """
    快速上传测评音频
    
    Usage:
        result = await upload_test_audio(audio_bytes, test_id=123, part="part1")
        if result.success:
            print(result.url)
    """
    client = get_oss_client()
    return await client.upload_audio(audio_data, test_id, part, extension)
