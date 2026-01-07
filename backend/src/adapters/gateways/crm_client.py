"""
CRM Gateway
Handles integration with 51Talk CRM API.
"""
import httpx
from typing import Optional, Dict, Any
from loguru import logger
from pydantic import BaseModel

from src.infrastructure.config import get_settings

settings = get_settings()


class CRMStudentData(BaseModel):
    """Student data model from CRM."""
    user_id: int
    real_name: str
    cur_age: int
    cur_grade: str
    cur_level_desc: str
    main_last_buy_unit_name: str
    is_upgrade: int
    ss_name: str
    ss_sm_name: str
    ss_dept4_name: str
    ss_group: str
    ss_crm_name: str
    ss_email_addr: str


class CRMGateway:
    """Gateway for CRM API interactions."""
    
    BASE_URL = "https://apiinterface.51talkjr.com/api/v1/domestic-ss/upgrade-28"
    
    async def get_student_info(self, user_id: int, ss_email: str) -> Optional[CRMStudentData]:
        """
        Fetch student info from CRM.
        
        Args:
            user_id: Student ID
            ss_email: Teacher's SS email
            
        Returns:
            CRMStudentData or None if not found/error
        """
        params = {
            "user_id": user_id,
            "ss_email_addr": ss_email
        }
        
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Fetching CRM data for student {user_id} (SS: {ss_email})")
                response = await client.get(self.BASE_URL, params=params, timeout=10.0)
                
                if response.status_code != 200:
                    logger.error(f"CRM API error: {response.status_code} - {response.text}")
                    return None
                
                data = response.json()
                
                if data.get("code") != 200:
                    logger.warning(f"CRM API returned non-200 code: {data}")
                    return None
                
                student_data = data.get("data")
                if not student_data:
                    logger.warning(f"CRM API returned no data for student {user_id}")
                    return None
                
                # Validate and parse
                return CRMStudentData(**student_data)
                
        except Exception as e:
            logger.exception(f"Failed to fetch CRM data: {e}")
            return None
