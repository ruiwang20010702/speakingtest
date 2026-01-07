import asyncio
import sys
import os
import json

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from src.infrastructure.database import AsyncSessionLocal
from src.adapters.repositories.models import QuestionModel

JSON_PATH = os.path.join(os.path.dirname(__file__), "../../_legacy_mvp/test_questions_level1.json")

async def seed_questions():
    if not os.path.exists(JSON_PATH):
        print(f"Error: JSON file not found at {JSON_PATH}")
        return

    with open(JSON_PATH, 'r') as f:
        data = json.load(f)

    async with AsyncSessionLocal() as session:
        print("Seeding questions from JSON...")
        
        for level_data in data.get("levels", []):
            level_name = level_data.get("level_name")
            # Map "Level 1" to "L1"
            level_code = "L1" if "Level 1" in level_name else level_name
            
            for section in level_data.get("sections", []):
                unit_name = section.get("section_name") # e.g., "Unit 1-3"
                
                for part in section.get("parts", []):
                    part_id = part.get("part_id")
                    part_type = part.get("type")
                    
                    items = part.get("items") or part.get("dialogues") or []
                    
                    print(f"Processing {level_code} - {unit_name} - Part {part_id} ({len(items)} items)")
                    
                    for item in items:
                        question_no = item.get("id")
                        
                        question_text = ""
                        reference_answer = None
                        
                        if part_id == 1: # Vocabulary / Word Reading
                            question_text = item.get("word")
                            reference_answer = item.get("word")
                        elif part_id == 2: # Sentences / Q&A
                            question_text = item.get("teacher")
                            options = item.get("student_options", [])
                            reference_answer = json.dumps(options, ensure_ascii=False)
                        
                        # Upsert
                        stmt = insert(QuestionModel).values(
                            level=level_code,
                            unit=unit_name,
                            part=part_id,
                            type=part_type,
                            question_no=question_no,
                            question=question_text,
                            reference_answer=reference_answer,
                            is_active=True
                        ).on_conflict_do_update(
                            constraint="uk_level_unit_part_question",
                            set_={
                                "question": question_text,
                                "reference_answer": reference_answer,
                                "type": part_type,
                                "is_active": True,
                                "updated_at": insert(QuestionModel).excluded.updated_at
                            }
                        )
                        
                        await session.execute(stmt)
        
        await session.commit()
        print("Questions seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_questions())
