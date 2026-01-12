"""
CSV Import Use Case

Handles bulk import of students from CSV file.
"""
import csv
import io
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.adapters.repositories.models import StudentProfileModel, UserModel


@dataclass
class CSVImportResult:
    """Result of CSV import operation."""
    success: bool
    total_rows: int
    imported_count: int
    updated_count: int
    failed_count: int
    errors: List[str]


class CSVImportUseCase:
    """
    Use case for importing students from CSV.
    
    CSV format (minimum):
    - student_id: External student ID (required)
    - student_name: Student name (required)
    
    Optional columns:
    - cur_age, cur_grade, cur_level_desc
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def execute(
        self,
        csv_content: str,
        teacher_id: int,
        teacher_email: str
    ) -> CSVImportResult:
        """
        Import students from CSV content.
        
        Args:
            csv_content: CSV file content as string
            teacher_id: ID of the importing teacher
            teacher_email: Email of the importing teacher
        
        Returns:
            CSVImportResult with import statistics
        """
        errors = []
        imported_count = 0
        updated_count = 0
        total_rows = 0
        
        try:
            # Parse CSV
            reader = csv.DictReader(io.StringIO(csv_content))
            
            # Validate required columns
            if not reader.fieldnames:
                return CSVImportResult(
                    success=False,
                    total_rows=0,
                    imported_count=0,
                    updated_count=0,
                    failed_count=0,
                    errors=["CSV file is empty or invalid"]
                )
            
            required_columns = ['student_id', 'student_name']
            missing = [col for col in required_columns if col not in reader.fieldnames]
            if missing:
                return CSVImportResult(
                    success=False,
                    total_rows=0,
                    imported_count=0,
                    updated_count=0,
                    failed_count=0,
                    errors=[f"Missing required columns: {', '.join(missing)}"]
                )
            
            for row_num, row in enumerate(reader, start=2):  # Start from 2 (header is 1)
                total_rows += 1
                
                try:
                    student_id = row.get('student_id', '').strip()
                    student_name = row.get('student_name', '').strip()
                    
                    if not student_id or not student_name:
                        errors.append(f"Row {row_num}: Missing student_id or student_name")
                        continue
                    
                    # Check if student exists
                    stmt = select(StudentProfileModel).where(
                        StudentProfileModel.external_user_id == student_id
                    )
                    result = await self.db.execute(stmt)
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        # Update existing student
                        existing.student_name = student_name
                        existing.teacher_id = teacher_id
                        existing.ss_email_addr = teacher_email
                        if row.get('cur_age'):
                            existing.cur_age = int(row['cur_age'])
                        if row.get('cur_grade'):
                            existing.cur_grade = row['cur_grade']
                        if row.get('cur_level_desc'):
                            existing.cur_level_desc = row['cur_level_desc']
                        updated_count += 1
                    else:
                        # Create new user and student profile
                        user = UserModel(role='student', status=1)
                        self.db.add(user)
                        await self.db.flush()
                        
                        student = StudentProfileModel(
                            user_id=user.id,
                            student_name=student_name,
                            external_source='csv_import',
                            external_user_id=student_id,
                            teacher_id=teacher_id,
                            ss_email_addr=teacher_email,
                            cur_age=int(row['cur_age']) if row.get('cur_age') else None,
                            cur_grade=row.get('cur_grade'),
                            cur_level_desc=row.get('cur_level_desc')
                        )
                        self.db.add(student)
                        imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            await self.db.commit()
            
            return CSVImportResult(
                success=True,
                total_rows=total_rows,
                imported_count=imported_count,
                updated_count=updated_count,
                failed_count=len(errors),
                errors=errors[:10]  # Limit errors to first 10
            )
            
        except Exception as e:
            await self.db.rollback()
            return CSVImportResult(
                success=False,
                total_rows=total_rows,
                imported_count=0,
                updated_count=0,
                failed_count=total_rows,
                errors=[f"Import failed: {str(e)}"]
            )
