"""
Email Service - Async SMTP 邮件发送
基于 /async-python-patterns 实现异步邮件发送
"""
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import aiosmtplib
from loguru import logger

from src.infrastructure.config import get_settings

settings = get_settings()


class EmailService:
    """
    异步邮件发送服务
    
    使用 aiosmtplib 实现非阻塞 SMTP 发送
    支持 SSL/TLS 连接
    """
    
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
        self.use_ssl = settings.SMTP_USE_SSL
    
    async def send_verification_code(
        self,
        to_email: str,
        code: str,
        expires_minutes: int = 5
    ) -> bool:
        """
        发送验证码邮件
        
        Args:
            to_email: 收件人邮箱
            code: 6位验证码
            expires_minutes: 过期时间（分钟）
            
        Returns:
            bool - True 表示发送成功
        """
        subject = f"【51Talk 口语测评】您的登录验证码是 {code}"
        
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #1890ff;">51Talk 口语测评系统</h2>
            <p>您好，</p>
            <p>您正在登录 51Talk 口语测评系统，验证码为：</p>
            <div style="background: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1890ff;">{code}</span>
            </div>
            <p style="color: #666;">验证码 {expires_minutes} 分钟内有效，请勿泄露给他人。</p>
            <p style="color: #999; font-size: 12px;">如果您没有请求此验证码，请忽略此邮件。</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">此邮件由系统自动发送，请勿回复。</p>
        </div>
        """
        
        return await self._send_email(to_email, subject, html_body)
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        发送邮件（底层方法）
        
        Args:
            to_email: 收件人
            subject: 主题
            html_body: HTML 正文
            text_body: 纯文本正文（可选）
            
        Returns:
            bool - 发送是否成功
        """
        if not self.host:
            logger.error("SMTP 未配置，无法发送邮件")
            return False
        
        try:
            # 构建邮件
            message = MIMEMultipart("alternative")
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Subject"] = subject
            
            # 添加纯文本版本（兜底）
            if text_body:
                message.attach(MIMEText(text_body, "plain", "utf-8"))
            
            # 添加 HTML 版本
            message.attach(MIMEText(html_body, "html", "utf-8"))
            
            # 发送
            logger.info(f"正在发送验证码邮件到 {to_email}")
            
            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                use_tls=self.use_ssl,
                timeout=10
            )
            
            logger.info(f"验证码邮件已发送到 {to_email}")
            return True
            
        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP 发送失败: {e}")
            return False
        except Exception as e:
            logger.exception(f"邮件发送异常: {e}")
            return False


# 单例
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """获取邮件服务单例"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
