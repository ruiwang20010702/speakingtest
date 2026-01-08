"""
Upload L0 word images to Aliyun OSS.
This script reads images from the frontend public folder and uploads them to OSS.
"""
import os
import asyncio
from pathlib import Path

import oss2
from loguru import logger

# OSS Configuration (用户提供的凭证)
OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID")
OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET")
OSS_ENDPOINT = "oss-cn-beijing.aliyuncs.com"
OSS_BUCKET_NAME = "ss-75-speakingtest"

# 本地图片目录
LOCAL_IMAGE_DIR = Path(__file__).parent.parent.parent / "frontend" / "student-h5" / "public" / "Word picture" / "level 0 all_clean"

# OSS 上传目录前缀
OSS_PREFIX = "questions/L0/"


def upload_images():
    """Upload all L0 images to OSS."""
    # 初始化 OSS 客户端
    auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
    
    if not LOCAL_IMAGE_DIR.exists():
        logger.error(f"本地图片目录不存在: {LOCAL_IMAGE_DIR}")
        return {}
    
    uploaded_urls = {}
    
    # 遍历目录中的所有图片
    for image_file in LOCAL_IMAGE_DIR.glob("*.png"):
        local_path = str(image_file)
        # 使用文件名作为 OSS key
        oss_key = f"{OSS_PREFIX}{image_file.name}"
        
        try:
            # 上传文件
            bucket.put_object_from_file(oss_key, local_path)
            
            # 生成公开访问 URL
            url = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{oss_key}"
            uploaded_urls[image_file.stem] = url
            
            logger.info(f"✅ 上传成功: {image_file.name} -> {url}")
        except Exception as e:
            logger.error(f"❌ 上传失败: {image_file.name} - {e}")
    
    return uploaded_urls


def generate_import_data(urls: dict):
    """Generate Python code for import script based on uploaded URLs."""
    print("\n# ===== 复制以下代码到 import_l0_questions.py =====\n")
    print("L0_WORDS = [")
    
    # 词汇映射
    words = [
        ("name", "名字"), ("six", "六"), ("hello", "你好"), ("mom", "妈妈"),
        ("dad", "爸爸"), ("grandma", "奶奶/外婆"), ("grandpa", "爷爷/外公"),
        ("chair", "椅子"), ("school", "学校"), ("bag", "包"), ("book", "书"),
        ("morning", "早上"), ("afternoon", "下午"), ("good", "好的"),
        ("clock", "时钟"), ("today", "今天"), ("watch", "手表"),
        ("lemon", "柠檬"), ("noodles", "面条"), ("rice", "米饭"),
    ]
    
    for i, (word, translation) in enumerate(words, 1):
        # 查找匹配的图片 URL
        matching_url = None
        for key, url in urls.items():
            if word.lower() in key.lower():
                matching_url = url
                break
        
        if matching_url:
            print(f'    {{"question_no": {i}, "question": "{word}", "translation": "{translation}", "image_url": "{matching_url}"}},')
        else:
            print(f'    {{"question_no": {i}, "question": "{word}", "translation": "{translation}", "image_url": None}},  # 未找到图片')
    
    print("]")


if __name__ == "__main__":
    print("=" * 50)
    print("L0 图片上传到 OSS")
    print("=" * 50)
    print(f"本地目录: {LOCAL_IMAGE_DIR}")
    print(f"OSS Bucket: {OSS_BUCKET_NAME}")
    print(f"OSS 前缀: {OSS_PREFIX}")
    print("=" * 50)
    
    # 检查目录
    if LOCAL_IMAGE_DIR.exists():
        images = list(LOCAL_IMAGE_DIR.glob("*.png"))
        print(f"找到 {len(images)} 张图片")
    else:
        print(f"⚠️ 目录不存在: {LOCAL_IMAGE_DIR}")
        print("请确认图片目录路径正确")
        exit(1)
    
    # 上传图片
    print("\n开始上传...")
    urls = upload_images()
    
    print(f"\n✅ 上传完成! 共上传 {len(urls)} 张图片")
    
    # 生成导入数据
    if urls:
        generate_import_data(urls)
