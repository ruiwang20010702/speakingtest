#!/usr/bin/env python3
"""
费用统计脚本
检查数据库中的费用记录，支持新的历史记录数组格式
"""
import asyncio
import sys
import os
from sqlalchemy import select, desc, func
from decimal import Decimal

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.database import AsyncSessionLocal
from src.adapters.repositories.models import TestModel


def sum_history_cost(history_list: list) -> tuple[Decimal, int]:
    """计算历史记录列表的总费用和总 tokens"""
    total_cost = Decimal(0)
    total_tokens = 0
    for record in history_list:
        total_cost += Decimal(str(record.get("cost", 0)))
        total_tokens += record.get("total_tokens", 0)
    return total_cost, total_tokens


def format_usage(tokens_used: dict) -> str:
    """格式化 tokens_used 显示（支持新旧格式）"""
    if not tokens_used:
        return ""
    
    try:
        parts = []
        
        # Part 1 历史记录
        p1_history = tokens_used.get("part1_history", [])
        if p1_history:
            p1_cost, p1_tokens = sum_history_cost(p1_history)
            parts.append(f"P1: {p1_tokens}t/{p1_cost:.4f}¥ ({len(p1_history)}次)")
        
        # Part 2 历史记录
        p2_history = tokens_used.get("part2_history", [])
        if p2_history:
            p2_cost, p2_tokens = sum_history_cost(p2_history)
            parts.append(f"P2: {p2_tokens}t/{p2_cost:.4f}¥ ({len(p2_history)}次)")
        
        # 测评汇总分析历史记录
        summary_history = tokens_used.get("summary_analysis_history", [])
        if summary_history:
            s_cost, s_tokens = sum_history_cost(summary_history)
            parts.append(f"汇总: {s_tokens}t/{s_cost:.4f}¥ ({len(summary_history)}次)")
        
        # 报告解读历史记录
        interp_history = tokens_used.get("interpretation_history", [])
        if interp_history:
            i_cost, i_tokens = sum_history_cost(interp_history)
            parts.append(f"解读: {i_tokens}t/{i_cost:.4f}¥ ({len(interp_history)}次)")
        
        if parts:
            return " | ".join(parts)
        
        # 兼容旧格式
        p1 = tokens_used.get("part1", {}).get("total_tokens", 0)
        p2 = tokens_used.get("part2", {}).get("total_tokens", 0)
        if p1 or p2:
            return f"P1: {p1}t, P2: {p2}t (旧格式)"
        
        return "无数据"
    except Exception as e:
        return f"解析错误: {e}"


async def check_costs():
    """检查费用统计"""
    async with AsyncSessionLocal() as session:
        # 获取有费用记录的测试，按创建时间倒序
        stmt = select(TestModel).where(TestModel.cost.isnot(None)).order_by(desc(TestModel.created_at)).limit(20)
        result = await session.execute(stmt)
        tests = result.scalars().all()
        
        # 获取总记录数
        count_stmt = select(func.count()).select_from(TestModel)
        count_result = await session.execute(count_stmt)
        total_count = count_result.scalar()
        
        if not tests:
            print(f"数据库中没有费用记录。(总测试数: {total_count})")
            print("注意：费用追踪是新功能，旧记录的 cost 字段为 NULL。")
            return

        print(f"\n{'ID':<6} | {'状态':<12} | {'总费用(¥)':<12} | {'详细费用'}")
        print("-" * 100)
        
        total_cost = Decimal(0)
        
        for test in tests:
            cost = test.cost or Decimal(0)
            total_cost += cost
            tokens_str = format_usage(test.tokens_used)
            print(f"{test.id:<6} | {test.status:<12} | {cost:<12.6f} | {tokens_str}")

        print("-" * 100)
        print(f"最近 {len(tests)} 条记录总费用: {total_cost:.6f} ¥")
        
        # 统计所有费用
        all_cost_stmt = select(func.sum(TestModel.cost)).where(TestModel.cost.isnot(None))
        all_cost_result = await session.execute(all_cost_stmt)
        all_cost = all_cost_result.scalar() or Decimal(0)
        print(f"数据库总费用: {all_cost:.6f} ¥")


if __name__ == "__main__":
    asyncio.run(check_costs())
