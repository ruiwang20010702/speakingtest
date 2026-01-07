"""
Import Student Use Case
Fetches student data from CRM and saves/updates it in the local database.
"""
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.adapters.repositories.models import StudentProfileModel, UserModel
from src.adapters.gateways.crm_client import CRMGateway, CRMStudentData


@dataclass
class ImportStudentRequest:
    """Request to import a student."""
    teacher_id: int
    teacher_email: str
    student_id: int


@dataclass
class ImportStudentResponse:
    """Response after import."""
    success: bool
    student_name: Optional[str] = None
    message: str = ""
    is_new: bool = False


class ImportStudentUseCase:
    """
    Import student from CRM.
    
    1. Call CRM API with teacher_email + student_id
    2. If found, create or update StudentProfileModel
    3. Ensure the student is linked to this teacher
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.crm_gateway = CRMGateway()
    
    async def execute(self, request: ImportStudentRequest) -> ImportStudentResponse:
        # 1. Fetch from CRM
        crm_data = await self.crm_gateway.get_student_info(
            user_id=request.student_id,
            ss_email=request.teacher_email
        )
        
        if not crm_data:
            return ImportStudentResponse(
                success=False,
                message="未找到该学生信息，请检查 ID 是否正确或是否在您名下"
            )
        
        # 2. Check if student exists
        stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == request.student_id)
        result = await self.db.execute(stmt)
        student = result.scalar_one_or_none()
        
        is_new = False
        now = datetime.utcnow()
        
        if not student:
            is_new = True
            # Create new student profile
            student = StudentProfileModel(
                user_id=crm_data.user_id,
                student_name=crm_data.real_name,
                external_source="crm_domestic_ss",
                external_user_id=str(crm_data.user_id),
                teacher_id=request.teacher_id,
                ss_email_addr=crm_data.ss_email_addr,
                ss_crm_name=crm_data.ss_crm_name,
                cur_age=crm_data.cur_age,
                cur_grade=crm_data.cur_grade,
                cur_level_desc=crm_data.cur_level_desc,
                main_last_buy_unit_name=crm_data.main_last_buy_unit_name,
                last_synced_at=now,
                created_at=now,
                updated_at=now
            )
            self.db.add(student)
            logger.info(f"Creating new student profile: {crm_data.user_id} ({crm_data.real_name})")
        else:
            # Update existing profile
            student.student_name = crm_data.real_name
            student.teacher_id = request.teacher_id  # Update teacher if changed
            student.ss_email_addr = crm_data.ss_email_addr
            student.ss_crm_name = crm_data.ss_crm_name
            student.cur_age = crm_data.cur_age
            student.cur_grade = crm_data.cur_grade
            student.cur_level_desc = crm_data.cur_level_desc
            student.main_last_buy_unit_name = crm_data.main_last_buy_unit_name
            student.last_synced_at = now
            student.updated_at = now
            logger.info(f"Updating student profile: {crm_data.user_id}")
            
        try:
            await self.db.commit()
            return ImportStudentResponse(
                success=True,
                student_name=student.student_name,
                message="导入成功",
                is_new=is_new
            )
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to save student: {e}")
            return ImportStudentResponse(
                success=False,
                message="保存学生信息失败"
            )
