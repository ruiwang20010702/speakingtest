"""
Import L0 questions and words from the frontend mock data into the database.
This script seeds the questions table with Part 1 (words) and Part 2 (Q&A) data.
"""
import asyncio
from sqlalchemy import select, delete

from src.infrastructure.database import AsyncSessionLocal
from src.adapters.repositories.models import QuestionModel


# L0 Word Reading Data (Part 1) - 使用 OSS URL
OSS_BASE = "https://ss-75-speakingtest.oss-cn-beijing.aliyuncs.com/questions/L0"

L0_WORDS = [
    {"question_no": 1, "question": "name", "translation": "名字", "image_url": f"{OSS_BASE}/name_签名场景版.png"},
    {"question_no": 2, "question": "six", "translation": "六", "image_url": f"{OSS_BASE}/six_图标.png"},
    {"question_no": 3, "question": "hello", "translation": "你好", "image_url": f"{OSS_BASE}/hello_图标.png"},
    {"question_no": 4, "question": "mom", "translation": "妈妈", "image_url": f"{OSS_BASE}/mom_图标.png"},
    {"question_no": 5, "question": "dad", "translation": "爸爸", "image_url": f"{OSS_BASE}/dad_图标.png"},  # 需要补充图片
    {"question_no": 6, "question": "grandma", "translation": "奶奶/外婆", "image_url": f"{OSS_BASE}/grandma_图标.png"},
    {"question_no": 7, "question": "grandpa", "translation": "爷爷/外公", "image_url": f"{OSS_BASE}/grandpa_图标.png"},
    {"question_no": 8, "question": "chair", "translation": "椅子", "image_url": f"{OSS_BASE}/chair_图标.png"},
    {"question_no": 9, "question": "school", "translation": "学校", "image_url": f"{OSS_BASE}/school_图标.png"},
    {"question_no": 10, "question": "bag", "translation": "包", "image_url": f"{OSS_BASE}/bag_图标.png"},
    {"question_no": 11, "question": "book", "translation": "书", "image_url": f"{OSS_BASE}/book_图标.png"},
    {"question_no": 12, "question": "morning", "translation": "早上", "image_url": f"{OSS_BASE}/morning_图标.png"},
    {"question_no": 13, "question": "afternoon", "translation": "下午", "image_url": f"{OSS_BASE}/afternoon_图标.png"},
    {"question_no": 14, "question": "good", "translation": "好的", "image_url": f"{OSS_BASE}/good_图标.png"},
    {"question_no": 15, "question": "clock", "translation": "时钟", "image_url": f"{OSS_BASE}/clock_图标.png"},
    {"question_no": 16, "question": "today", "translation": "今天", "image_url": f"{OSS_BASE}/today_图标.png"},
    {"question_no": 17, "question": "watch", "translation": "手表", "image_url": f"{OSS_BASE}/watch_图标.png"},
    {"question_no": 18, "question": "lemon", "translation": "柠檬", "image_url": f"{OSS_BASE}/lemon_图标.png"},
    {"question_no": 19, "question": "noodles", "translation": "面条", "image_url": f"{OSS_BASE}/noodles_图标.png"},
    {"question_no": 20, "question": "rice", "translation": "米饭", "image_url": f"{OSS_BASE}/rice_图标.png"},
]

# L0 Q&A Data (Part 2)
L0_QA = [
    {"question_no": 1, "question": "What's your name?", "reference_answer": "My name is ..."},
    {"question_no": 2, "question": "How old are you?", "reference_answer": "I am ... years old."},
    {"question_no": 3, "question": "Who is she?", "reference_answer": "She is my ..."},
    {"question_no": 4, "question": "Who is he?", "reference_answer": "He is my ..."},
    {"question_no": 5, "question": "What is this?", "reference_answer": "This is a/an ..."},
    {"question_no": 6, "question": "What is that?", "reference_answer": "That is a/an ..."},
    {"question_no": 7, "question": "How are you?", "reference_answer": "I am fine/good/happy."},
    {"question_no": 8, "question": "When do you eat lunch?", "reference_answer": "I eat lunch at ..."},
    {"question_no": 9, "question": "Do you like apples?", "reference_answer": "Yes, I do. / No, I don't."},
    {"question_no": 10, "question": "Do you want to eat rice?", "reference_answer": "Yes, I do. / No, I don't."},
    {"question_no": 11, "question": "What color is this?", "reference_answer": "It is red/blue/green..."},
    {"question_no": 12, "question": "Can you count to ten?", "reference_answer": "One, two, three..."},
]


async def import_l0_questions():
    """Import L0 questions into the database."""
    async with AsyncSessionLocal() as session:
        level = "L0"
        unit = "All"  # L0 uses a single set of questions
        
        # Clear existing L0 questions
        await session.execute(
            delete(QuestionModel).where(QuestionModel.level == level)
        )
        
        # Import Part 1 (Words)
        for word in L0_WORDS:
            q = QuestionModel(
                level=level,
                unit=unit,
                part=1,
                type="word_reading",
                question_no=word["question_no"],
                question=word["question"],
                translation=word["translation"],
                image_url=word["image_url"],
            )
            session.add(q)
        print(f"✅ Imported {len(L0_WORDS)} Part 1 words for L0")
        
        # Import Part 2 (Q&A)
        for qa in L0_QA:
            q = QuestionModel(
                level=level,
                unit=unit,
                part=2,
                type="question_answer",
                question_no=qa["question_no"],
                question=qa["question"],
                reference_answer=qa["reference_answer"],
            )
            session.add(q)
        print(f"✅ Imported {len(L0_QA)} Part 2 questions for L0")
        
        await session.commit()
        print("\n✅ L0 question import completed!")


if __name__ == "__main__":
    asyncio.run(import_l0_questions())
