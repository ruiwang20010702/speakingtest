"""
CRM Service - 调用 51Talk CRM API 获取员工信息
"""
import httpx
import logging
from typing import Optional
from dataclasses import dataclass

from src.infrastructure.timezone import now as china_now

logger = logging.getLogger(__name__)

# CRM API 配置
CRM_API_BASE_URL = "https://apiinterface.51talkjr.com/api/v1"
CRM_API_TIMEOUT = 10.0  # 秒


@dataclass
class CRMUserInfo:
    """CRM 用户信息"""
    ss_name: Optional[str] = None
    ss_sm_name: Optional[str] = None
    ss_dept4_name: Optional[str] = None
    ss_group: Optional[str] = None
    ss_crm_name: Optional[str] = None
    ss_email_addr: Optional[str] = None


async def fetch_crm_user_info(email: str) -> Optional[CRMUserInfo]:
    """
    根据邮箱从 CRM 系统获取用户信息
    
    Args:
        email: 用户邮箱地址
        
    Returns:
        CRMUserInfo 对象，如果查询失败则返回 None
    """
    if not email:
        return None
    
    # 构建 API URL
    url = f"{CRM_API_BASE_URL}/domestic-ss/upgrade-28"
    params = {"ss_email_addr": email}
    
    try:
        async with httpx.AsyncClient(timeout=CRM_API_TIMEOUT) as client:
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                logger.warning(f"CRM API 返回非 200 状态码: {response.status_code}, email={email}")
                return None
            
            data = response.json()
            
            if data.get("code") != 200:
                logger.warning(f"CRM API 返回错误: {data.get('message')}, email={email}")
                return None
            
            user_data = data.get("data", {})
            
            if not user_data:
                logger.info(f"CRM API 未返回用户数据: email={email}")
                return None
            
            crm_info = CRMUserInfo(
                ss_name=user_data.get("ss_name"),
                ss_sm_name=user_data.get("ss_sm_name"),
                ss_dept4_name=user_data.get("ss_dept4_name"),
                ss_group=user_data.get("ss_group"),
                ss_crm_name=user_data.get("ss_crm_name"),
                ss_email_addr=user_data.get("ss_email_addr"),
            )
            
            logger.info(f"成功获取 CRM 用户信息: email={email}, crm_name={crm_info.ss_crm_name}")
            return crm_info
            
    except httpx.TimeoutException:
        logger.warning(f"CRM API 请求超时: email={email}")
        return None
    except httpx.RequestError as e:
        logger.warning(f"CRM API 请求失败: {e}, email={email}")
        return None
    except Exception as e:
        logger.error(f"CRM API 调用异常: {e}, email={email}")
        return None


async def update_user_crm_info(db, user, crm_info: CRMUserInfo) -> bool:
    """
    更新用户的 CRM 信息
    
    Args:
        db: 数据库会话
        user: UserModel 实例
        crm_info: CRM 用户信息
        
    Returns:
        是否更新成功
    """
    if not crm_info:
        return False
    
    try:
        # 只更新非空字段
        if crm_info.ss_name:
            user.ss_name = crm_info.ss_name
        if crm_info.ss_sm_name:
            user.ss_sm_name = crm_info.ss_sm_name
        if crm_info.ss_dept4_name:
            user.ss_dept4_name = crm_info.ss_dept4_name
        if crm_info.ss_group:
            user.ss_group = crm_info.ss_group
        if crm_info.ss_crm_name:
            user.ss_crm_name = crm_info.ss_crm_name
        
        # 记录同步时间
        user.crm_synced_at = china_now()
        
        await db.commit()
        logger.info(f"用户 CRM 信息已更新: user_id={user.id}, crm_name={crm_info.ss_crm_name}")
        return True
        
    except Exception as e:
        logger.error(f"更新用户 CRM 信息失败: {e}, user_id={user.id}")
        await db.rollback()
        return False
