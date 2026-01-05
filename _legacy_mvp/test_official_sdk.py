#!/usr/bin/env python3
"""
使用讯飞官方SDK测试语音评测
"""
import os
import base64
from xfyunsdkspeech.ise_client import IseClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 配置
APP_ID = os.getenv("XUNFEI_APP_ID", "88992227")
API_KEY = os.getenv("XUNFEI_API_KEY", "c424a9342ede9d24b58b4bc5be4d78de")
API_SECRET = os.getenv("XUNFEI_API_SECRET", "MDc4ODk1Mjg2ZDhhYmUwYTgzZDdjYWI5")


def test_read_sentence():
    """测试朗读评测"""
    print("\n" + "="*50)
    print("📖 测试朗读评测 (read_sentence)")
    print("="*50)
    
    client = IseClient(
        app_id=APP_ID,
        api_key=API_KEY,
        api_secret=API_SECRET,
        aue="raw",
        group="pupil",
        ent="en_vip",
        category="read_sentence",
    )
    
    file_path = "car.pcm"
    with open(file_path, 'rb') as f:
        for chunk in client.stream('\uFEFF' + "I like the car", f):
            if chunk.get("data"):
                result = str(base64.b64decode(chunk["data"]), 'utf-8')
                logger.info(f"返回结果: {result[:500]}...")
            else:
                logger.info(f"返回结果: {chunk}")


def test_topic():
    """测试话题评测"""
    print("\n" + "="*50)
    print("🎤 测试话题评测 (topic)")
    print("="*50)
    
    client = IseClient(
        app_id=APP_ID,
        api_key=API_KEY,
        api_secret=API_SECRET,
        aue="raw",
        group="pupil",
        ent="en_vip",
        category="topic",
    )
    
    file_path = "car.pcm"
    with open(file_path, 'rb') as f:
        for chunk in client.stream('\uFEFF' + "What kind of car do you like?", f):
            if chunk.get("data"):
                result = str(base64.b64decode(chunk["data"]), 'utf-8')
                logger.info(f"返回结果: {result[:500]}...")
            else:
                logger.info(f"返回结果: {chunk}")


def test_topic_with_format():
    """测试话题评测（使用[topic]格式）"""
    print("\n" + "="*50)
    print("🎤 测试话题评测 (topic with [topic] format)")
    print("="*50)
    
    client = IseClient(
        app_id=APP_ID,
        api_key=API_KEY,
        api_secret=API_SECRET,
        aue="raw",
        group="pupil",
        ent="en_vip",
        category="topic",
    )
    
    file_path = "car.pcm"
    text = "[topic]\nWhat kind of car do you like?"
    
    with open(file_path, 'rb') as f:
        for chunk in client.stream('\uFEFF' + text, f):
            if chunk.get("data"):
                result = str(base64.b64decode(chunk["data"]), 'utf-8')
                logger.info(f"返回结果: {result[:500]}...")
            else:
                logger.info(f"返回结果: {chunk}")


if __name__ == "__main__":
    try:
        # 先测试朗读评测确认基本功能
        test_read_sentence()
    except Exception as e:
        logger.error(f"朗读评测失败: {e}")
    
    print("\n" + "-"*50 + "\n")
    
    try:
        # 测试topic评测
        test_topic()
    except Exception as e:
        logger.error(f"话题评测失败: {e}")
    
    print("\n" + "-"*50 + "\n")
    
    try:
        # 测试带格式的topic评测
        test_topic_with_format()
    except Exception as e:
        logger.error(f"话题评测(格式)失败: {e}")

