import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
sys.path.append(os.getcwd())

from src.infrastructure.database import AsyncSessionLocal
from src.adapters.repositories.models import QuestionModel
from sqlalchemy import select

async def check_questions():
    async with AsyncSessionLocal() as session:
        stmt = select(QuestionModel).where(QuestionModel.level == 'L0').order_by(QuestionModel.question_no)
        result = await session.execute(stmt)
        questions = result.scalars().all()
        
        print(f"Found {len(questions)} questions for L0:")
        for q in questions:
            if q.part == 1:
                print(f"  {q.question_no}. {q.question} (Ref: {q.reference_answer})")
                if q.question.lower() in ['dad', 'father']:
                    print(f"    -> FOUND TARGET WORD: {q.question}")

if __name__ == "__main__":
    asyncio.run(check_questions())
