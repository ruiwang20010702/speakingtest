"""
Upload word images to OSS and update database.

图片目录结构:
- word/word/L1/1/how.png  -> level=L1, 子目录可能代表 unit
- word/word/L3/shake.png  -> level=L3

OSS URL 格式:
https://ss-75-speakingtest.oss-cn-beijing.aliyuncs.com/questions/{level}/{unit}/{question_no}_{word}.png

用法:
    cd backend
    source venv/bin/activate
    python scripts/upload_word_images.py --dry-run   # 预览模式，不实际上传
    python scripts/upload_word_images.py             # 正式上传
"""
import os
import sys
import re
import asyncio
import argparse
from pathlib import Path
from urllib.parse import quote

import oss2
from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.config import get_settings
from src.adapters.repositories.models import QuestionModel

settings = get_settings()

# OSS 配置
OSS_ENDPOINT = "oss-cn-beijing.aliyuncs.com"
OSS_BUCKET_NAME = "ss-75-speakingtest"

# 图片目录
WORD_IMAGE_DIR = Path(__file__).parent.parent.parent / "word" / "word"


def normalize_word(word: str) -> str:
    """
    标准化单词，用于匹配。
    - 转小写
    - 去除首尾空格
    """
    return word.strip().lower()


def get_oss_key(level: str, unit: str, question_no: int, word: str) -> str:
    """
    生成 OSS key。
    格式: questions/{level}/{unit}/{question_no}_{word}.png
    
    注意: 文件名中的空格需要用下划线替换
    """
    # 清理 unit 名称，替换空格为下划线
    unit_clean = unit.replace(" ", "_").lower()
    # 清理单词，替换空格为下划线
    word_clean = word.replace(" ", "_").lower()
    
    return f"questions/{level}/{unit_clean}/{question_no}_{word_clean}.png"


def get_oss_url(oss_key: str) -> str:
    """生成公开访问 URL"""
    return f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{oss_key}"


async def get_all_questions(db: AsyncSession) -> list:
    """获取所有 Part 1 (word_reading) 题目"""
    stmt = select(QuestionModel).where(
        and_(
            QuestionModel.part == 1,  # Part 1 是单词朗读
            QuestionModel.is_active == True
        )
    ).order_by(QuestionModel.level, QuestionModel.unit, QuestionModel.question_no)
    
    result = await db.execute(stmt)
    return result.scalars().all()


def scan_images() -> dict:
    """
    扫描图片目录，返回 {(level, word_normalized): image_path} 的映射。
    
    目录结构:
    - word/word/L1/1/how.png
    - word/word/L3/shake.png
    """
    images = {}
    
    if not WORD_IMAGE_DIR.exists():
        logger.error(f"图片目录不存在: {WORD_IMAGE_DIR}")
        return images
    
    # 遍历 L1-L9 目录
    for level_dir in WORD_IMAGE_DIR.iterdir():
        if not level_dir.is_dir() or level_dir.name.startswith('.'):
            continue
        
        level = level_dir.name  # e.g., "L1", "L2"
        
        # 检查是否有子目录 (如 L1/1, L1/2)
        for item in level_dir.iterdir():
            if item.is_file() and item.suffix.lower() == '.png':
                # 直接在 level 目录下的图片
                word = item.stem  # 文件名去掉扩展名
                key = (level, normalize_word(word))
                images[key] = item
                
            elif item.is_dir() and not item.name.startswith('.'):
                # 子目录中的图片
                for img_file in item.glob("*.png"):
                    word = img_file.stem
                    key = (level, normalize_word(word))
                    images[key] = img_file
    
    return images


async def upload_and_update(
    db: AsyncSession,
    bucket: oss2.Bucket,
    question: QuestionModel,
    image_path: Path,
    dry_run: bool = False
) -> bool:
    """
    上传图片到 OSS 并更新数据库。
    
    Returns:
        True 如果成功，False 如果失败
    """
    oss_key = get_oss_key(
        level=question.level,
        unit=question.unit,
        question_no=question.question_no,
        word=question.question
    )
    oss_url = get_oss_url(oss_key)
    
    if dry_run:
        logger.info(f"[DRY-RUN] 将上传: {image_path.name} -> {oss_key}")
        logger.info(f"[DRY-RUN] 将更新: question_id={question.id}, image_url={oss_url}")
        return True
    
    try:
        # 上传到 OSS
        result = bucket.put_object_from_file(oss_key, str(image_path))
        
        if result.status != 200:
            logger.error(f"OSS 上传失败: {image_path.name}, status={result.status}")
            return False
        
        # 更新数据库
        question.image_url = oss_url
        await db.commit()
        
        logger.info(f"✅ 成功: {question.question} ({question.level}/{question.unit}) -> {oss_url}")
        return True
        
    except Exception as e:
        logger.exception(f"❌ 失败: {image_path.name} - {e}")
        await db.rollback()
        return False


async def main(dry_run: bool = False):
    """主函数"""
    logger.info("=" * 60)
    logger.info("  单词图片上传脚本")
    logger.info("=" * 60)
    logger.info(f"图片目录: {WORD_IMAGE_DIR}")
    logger.info(f"OSS Bucket: {OSS_BUCKET_NAME}")
    logger.info(f"模式: {'预览 (dry-run)' if dry_run else '正式上传'}")
    logger.info("=" * 60)
    
    # 检查 OSS 配置
    if not settings.OSS_ACCESS_KEY_ID or not settings.OSS_ACCESS_KEY_SECRET:
        logger.error("OSS 配置缺失，请检查环境变量 OSS_ACCESS_KEY_ID 和 OSS_ACCESS_KEY_SECRET")
        return
    
    # 初始化 OSS
    auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
    
    # 扫描图片
    logger.info("\n>>> 1. 扫描图片目录...")
    images = scan_images()
    logger.info(f"找到 {len(images)} 张图片")
    
    if not images:
        logger.warning("没有找到图片，退出")
        return
    
    # 连接数据库
    logger.info("\n>>> 2. 连接数据库...")
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 获取所有 Part 1 题目
        questions = await get_all_questions(db)
        logger.info(f"数据库中有 {len(questions)} 道 Part 1 题目")
        
        # 匹配并上传
        logger.info("\n>>> 3. 匹配并上传...")
        
        matched = 0
        uploaded = 0
        skipped = 0
        failed = 0
        not_matched_images = []
        not_matched_questions = []
        
        # 构建题目索引 {(level, word_normalized): [question1, question2, ...]}
        # 注意：同一个单词可能在多个 unit 中出现
        question_index = {}
        for q in questions:
            key = (q.level, normalize_word(q.question))
            if key not in question_index:
                question_index[key] = []
            question_index[key].append(q)
        
        # 记录已上传的 OSS key，避免重复上传同一张图片
        uploaded_oss_keys = {}
        
        # 遍历图片，尝试匹配
        for (level, word_norm), image_path in images.items():
            key = (level, word_norm)
            
            if key in question_index:
                questions_to_update = question_index[key]
                matched += len(questions_to_update)
                
                for question in questions_to_update:
                    # 检查是否已有 image_url
                    if question.image_url and not dry_run:
                        logger.debug(f"跳过 (已有图片): {question.question} ({question.level}/{question.unit})")
                        skipped += 1
                        continue
                    
                    # 生成 OSS key
                    oss_key = get_oss_key(
                        level=question.level,
                        unit=question.unit,
                        question_no=question.question_no,
                        word=question.question
                    )
                    
                    # 如果这个 OSS key 还没上传过，先上传
                    if oss_key not in uploaded_oss_keys:
                        if not dry_run:
                            try:
                                result = bucket.put_object_from_file(oss_key, str(image_path))
                                if result.status == 200:
                                    uploaded_oss_keys[oss_key] = get_oss_url(oss_key)
                                else:
                                    logger.error(f"OSS 上传失败: {image_path.name}, status={result.status}")
                                    failed += 1
                                    continue
                            except Exception as e:
                                logger.exception(f"❌ 上传失败: {image_path.name} - {e}")
                                failed += 1
                                continue
                        else:
                            uploaded_oss_keys[oss_key] = get_oss_url(oss_key)
                            logger.info(f"[DRY-RUN] 将上传: {image_path.name} -> {oss_key}")
                    
                    # 更新数据库
                    oss_url = uploaded_oss_keys[oss_key]
                    if dry_run:
                        logger.info(f"[DRY-RUN] 将更新: question_id={question.id}, {question.level}/{question.unit} -> {oss_url}")
                        uploaded += 1
                    else:
                        try:
                            question.image_url = oss_url
                            await db.commit()
                            logger.info(f"✅ 成功: {question.question} ({question.level}/{question.unit}) -> {oss_url}")
                            uploaded += 1
                        except Exception as e:
                            logger.exception(f"❌ 数据库更新失败: {question.question} - {e}")
                            await db.rollback()
                            failed += 1
            else:
                not_matched_images.append((level, image_path.stem, image_path))
        
        # 找出没有匹配到图片的题目
        matched_keys = set()
        for (level, word_norm), _ in images.items():
            matched_keys.add((level, word_norm))
        
        for q in questions:
            key = (q.level, normalize_word(q.question))
            if key not in matched_keys and not q.image_url:
                not_matched_questions.append(q)
        
        # 输出统计
        logger.info("\n" + "=" * 60)
        logger.info("  统计结果")
        logger.info("=" * 60)
        logger.info(f"图片总数: {len(images)}")
        logger.info(f"题目总数: {len(questions)}")
        logger.info(f"匹配成功: {matched}")
        logger.info(f"上传成功: {uploaded}")
        logger.info(f"跳过 (已有图片): {skipped}")
        logger.info(f"上传失败: {failed}")
        logger.info(f"图片未匹配: {len(not_matched_images)}")
        logger.info(f"题目缺图片: {len(not_matched_questions)}")
        
        # 输出未匹配的图片
        if not_matched_images:
            logger.warning("\n未匹配的图片 (数据库中没有对应题目):")
            for level, word, path in not_matched_images[:20]:  # 最多显示20个
                logger.warning(f"  - {level}: {word} ({path})")
            if len(not_matched_images) > 20:
                logger.warning(f"  ... 还有 {len(not_matched_images) - 20} 个")
        
        # 输出缺少图片的题目
        if not_matched_questions:
            logger.warning("\n缺少图片的题目:")
            for q in not_matched_questions[:20]:  # 最多显示20个
                logger.warning(f"  - {q.level}/{q.unit}: {q.question}")
            if len(not_matched_questions) > 20:
                logger.warning(f"  ... 还有 {len(not_matched_questions) - 20} 个")
    
    await engine.dispose()
    
    logger.info("\n✅ 脚本执行完成!")
    if dry_run:
        logger.info("提示: 这是预览模式，实际未上传。使用 --no-dry-run 或不带参数运行以实际上传。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="上传单词图片到 OSS 并更新数据库")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        default=False,
        help="预览模式，不实际上传和更新数据库"
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(dry_run=args.dry_run))
