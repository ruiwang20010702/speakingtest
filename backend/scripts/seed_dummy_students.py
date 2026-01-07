import asyncio
import sys
import os

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from src.infrastructure.database import AsyncSessionLocal
from src.adapters.repositories.models import UserModel, StudentProfileModel

async def seed_dummy_students():
    teacher_email = "wangrui003@51talk.com"
    dummy_students = [
        {"id": "1928409", "name": "stu1928409", "grade": "四年级", "level": "L1", "unit": "Unit 1 Food"},
        {"id": "1928410", "name": "stu1928410", "grade": "五年级", "level": "L2", "unit": "Unit 2 Animals"},
        {"id": "1928411", "name": "stu1928411", "grade": "六年级", "level": "L3", "unit": "Unit 3 Sports"},
    ]

    async with AsyncSessionLocal() as session:
        # 1. Get or Create Teacher
        result = await session.execute(select(UserModel).where(UserModel.email == teacher_email))
        teacher = result.scalar_one_or_none()

        if not teacher:
            print(f"Creating teacher: {teacher_email}")
            teacher = UserModel(
                role="teacher",
                email=teacher_email,
                status=1
            )
            session.add(teacher)
            await session.commit()
            await session.refresh(teacher)
        else:
            print(f"Found teacher: {teacher_email} (ID: {teacher.id})")

        # 2. Create Students
        for stu_data in dummy_students:
            # Check if student user exists (using external_user_id as a way to track, but users table doesn't have it)
            # We'll assume the dummy ID is unique enough or check by name for this script
            # Actually, let's just check if a profile with this external_user_id exists
            
            result = await session.execute(select(StudentProfileModel).where(StudentProfileModel.external_user_id == stu_data["id"]))
            profile = result.scalar_one_or_none()

            if profile:
                print(f"Student {stu_data['name']} already exists. Updating info...")
                profile.teacher_id = teacher.id
                profile.cur_grade = stu_data["grade"]
                profile.cur_level_desc = stu_data["level"]
                profile.main_last_buy_unit_name = stu_data["unit"]
                profile.ss_crm_name = "51wangrui003"
                session.add(profile)
            else:
                print(f"Creating student: {stu_data['name']}")
                # Create User first
                student_user = UserModel(
                    role="student",
                    status=1
                )
                session.add(student_user)
                await session.flush() # Get ID

                # Create Profile
                profile = StudentProfileModel(
                    user_id=student_user.id,
                    student_name=stu_data["name"],
                    external_user_id=stu_data["id"],
                    teacher_id=teacher.id,
                    cur_grade=stu_data["grade"],
                    cur_level_desc=stu_data["level"],
                    main_last_buy_unit_name=stu_data["unit"],
                    ss_crm_name="51wangrui003"
                )
                session.add(profile)
        
        await session.commit()
        print("Dummy students seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_dummy_students())
