"""
Question Seed Script
Populates the database with sample questions for testing.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from src.infrastructure.database import AsyncSessionLocal
from src.adapters.repositories.models import QuestionModel


# Sample questions for L1 Unit 1 (based on test_qwen_omni.py)
L1_UNIT1_QUESTIONS = [
    {"question_no": 1, "question": "How are you?", "reference_answer": "I'm fine, thank you. / I'm good."},
    {"question_no": 2, "question": "Are you happy today?", "reference_answer": "Yes, I am. / No, I'm not."},
    {"question_no": 3, "question": "How old are you?", "reference_answer": "I am ... years old."},
    {"question_no": 4, "question": "What grade are you in?", "reference_answer": "I am in grade ..."},
    {"question_no": 5, "question": "Do you have sisters or brothers?", "reference_answer": "Yes, I do. / No, I don't."},
    {"question_no": 6, "question": "How many sisters or brothers do you have?", "reference_answer": "I have ... sister(s)/brother(s)."},
    {"question_no": 7, "question": "What can you see in your room?", "reference_answer": "I can see a bed/desk/chair..."},
    {"question_no": 8, "question": "What time is it now?", "reference_answer": "It is ... o'clock."},
    {"question_no": 9, "question": "When do you wake up?", "reference_answer": "I wake up at ..."},
    {"question_no": 10, "question": "What is your favorite food?", "reference_answer": "My favorite food is ..."},
    {"question_no": 11, "question": "Do you like English?", "reference_answer": "Yes, I like English. / No, I don't."},
    {"question_no": 12, "question": "Can you count from one to twenty?", "reference_answer": "One, two, three...twenty."},
]


async def seed_questions():
    """Seed the database with sample questions."""
    print("=" * 60)
    print("Question Seed Script")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        # Check if questions already exist
        stmt = select(QuestionModel).where(
            QuestionModel.level == "L1",
            QuestionModel.unit == "Unit 1"
        )
        result = await db.execute(stmt)
        existing = result.scalars().all()
        
        if existing:
            print(f"Found {len(existing)} existing questions for L1 - Unit 1")
            print("Skipping seed (use --force to overwrite)")
            return
        
        # Insert questions
        print("Inserting questions for L1 - Unit 1...")
        for q in L1_UNIT1_QUESTIONS:
            question = QuestionModel(
                level="L1",
                unit="Unit 1",
                question_no=q["question_no"],
                question=q["question"],
                reference_answer=q["reference_answer"]
            )
            db.add(question)
        
        await db.commit()
        print(f"✅ Inserted {len(L1_UNIT1_QUESTIONS)} questions")
    
    print("=" * 60)
    print("Done!")


if __name__ == "__main__":
    asyncio.run(seed_questions())
