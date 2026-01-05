#!/usr/bin/env python3
"""
完整测试流程：运行测试、生成详细报告、导出到飞书、发送通知
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from services.feishu_client import FeishuClient, send_test_message_to_user


def main():
    load_dotenv()

    print("=" * 60)
    print("Python 智能测试与飞书导出")
    print("=" * 60)

    # 1. 运行测试
    print("\n📋 步骤 1: 运行 pytest 测试")
    import subprocess
    result = subprocess.run(
        ["pytest", "tests/", "-v", "--json-report", "--json-report-file=test_results.json"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("⚠️ 部分测试失败，但继续生成报告...")

    # 2. 读取测试结果
    print("\n📊 步骤 2: 解析测试结果")
    with open('test_results.json', 'r') as f:
        test_data = json.load(f)

    summary = test_data.get('summary', {})
    total = summary.get('total', 0)
    passed = summary.get('passed', 0)
    failed = summary.get('failed', 0)
    skipped = summary.get('skipped', 0)
    pass_rate = (passed / total * 100) if total > 0 else 0
    duration = test_data.get('duration', 0)  # duration 在顶层，不在 summary 中

    print(f"   总数: {total}, 通过: {passed}, 失败: {failed}, 跳过: {skipped}")
    print(f"   通过率: {pass_rate:.1f}%, 执行时间: {duration:.2f}s")

    # 3. 生成详细飞书报告
    print("\n📄 步骤 3: 生成详细测试报告到飞书")
    client = FeishuClient()
    doc_url = client.export_detailed_test_report(test_data)

    # 4. 发送飞书通知
    print("\n📤 步骤 4: 发送飞书通知")
    user_open_id = os.getenv("FEISHU_USER_OPEN_ID")

    if user_open_id:
        send_test_message_to_user(
            client=client,
            open_id=user_open_id,
            total=total,
            passed=passed,
            failed=failed,
            pass_rate=pass_rate,
            doc_url=doc_url,
            duration=duration
        )
    else:
        print("   ℹ️  未配置 FEISHU_USER_OPEN_ID，跳过飞书通知")

    # 总结
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print(f"📊 通过率: {pass_rate:.1f}% ({passed}/{total})")
    print(f"📄 详细报告: {doc_url}")
    print("=" * 60)


if __name__ == "__main__":
    main()
