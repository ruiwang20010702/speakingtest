#!/usr/bin/env python3
"""
数据库初始化脚本
运行此脚本创建所有数据库表
"""
import os
import sys

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, DATABASE_URL

if __name__ == "__main__":
    print("=" * 50)
    print("数据库初始化")
    print("=" * 50)
    print(f"数据库URL: {DATABASE_URL[:60]}...")
    print()
    
    try:
        init_db()
        print()
        print("✅ 数据库初始化完成!")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)

