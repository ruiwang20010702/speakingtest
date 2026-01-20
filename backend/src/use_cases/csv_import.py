"""
CSV Import Use Case

Handles bulk import of students from CSV file.
Optimized to avoid N+1 queries by batch loading existing students.
"""
import csv
import io
from dataclasses import dataclass
from typing import List, Dict, Optional

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
            
            # First pass: collect all rows and external_user_ids
            rows_data: List[Dict] = []
            external_ids: List[str] = []
            
            for row_num, row in enumerate(reader, start=2):
                total_rows += 1
                student_id = row.get('student_id', '').strip()
                student_name = row.get('student_name', '').strip()
                
                if not student_id or not student_name:
                    errors.append(f"Row {row_num}: Missing student_id or student_name")
                    continue
                
                rows_data.append({
                    'row_num': row_num,
                    'student_id': student_id,
                    'student_name': student_name,
                    'cur_age': row.get('cur_age'),
                    'cur_grade': row.get('cur_grade'),
                    'cur_level_desc': row.get('cur_level_desc')
                })
                external_ids.append(student_id)
            
            # Batch query: load all existing students by external_user_id (1 query instead of N)
            existing_students: Dict[str, StudentProfileModel] = {}
            if external_ids:
                    stmt = select(StudentProfileModel).where(
                    StudentProfileModel.external_user_id.in_(external_ids)
                    )
                    result = await self.db.execute(stmt)
                for student in result.scalars().all():
                    existing_students[student.external_user_id] = student
            
            # Second pass: process rows using the pre-loaded data
            for row_data in rows_data:
                try:
                    student_id = row_data['student_id']
                    student_name = row_data['student_name']
                    
                    existing = existing_students.get(student_id)
                    
                    if existing:
                        # Update existing student
                        existing.student_name = student_name
                        existing.teacher_id = teacher_id
                        existing.ss_email_addr = teacher_email
                        if row_data['cur_age']:
                            existing.cur_age = int(row_data['cur_age'])
                        if row_data['cur_grade']:
                            existing.cur_grade = row_data['cur_grade']
                        if row_data['cur_level_desc']:
                            existing.cur_level_desc = row_data['cur_level_desc']
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
                            cur_age=int(row_data['cur_age']) if row_data['cur_age'] else None,
                            cur_grade=row_data['cur_grade'],
                            cur_level_desc=row_data['cur_level_desc']
                        )
                        self.db.add(student)
                        imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_data['row_num']}: {str(e)}")
            
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
