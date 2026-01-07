"""
Admin Controller
Handles aggregated statistics for the admin dashboard.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.infrastructure.auth import require_admin
from src.adapters.repositories.models import (
    StudentProfileModel, TestModel, ReportShareTokenModel, StudentEntryTokenModel
)

router = APIRouter()

class OverviewStats(BaseModel):
    total_students: int
    total_tests: int
    total_shares: int
    total_opens: int

class FunnelStats(BaseModel):
    scanned: int
    completed: int
    shared: int
    opened: int

class CostStats(BaseModel):
    total_tests: int
    estimated_cost_cny: float

@router.get(
    "/stats/overview",
    response_model=OverviewStats,
    summary="获取概览数据",
    description="获取系统总览数据：学生总数、测评总数、分享次数、打开次数。"
)
async def get_overview_stats(
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin)
):
    # Total Students
    stmt_students = select(func.count(StudentProfileModel.user_id))
    total_students = (await db.execute(stmt_students)).scalar() or 0
    
    # Total Tests
    stmt_tests = select(func.count(TestModel.id))
    total_tests = (await db.execute(stmt_tests)).scalar() or 0
    
    # Total Shares
    stmt_shares = select(func.count(ReportShareTokenModel.id))
    total_shares = (await db.execute(stmt_shares)).scalar() or 0
    
    # Total Opens (Sum of view_count)
    stmt_opens = select(func.sum(ReportShareTokenModel.view_count))
    total_opens = (await db.execute(stmt_opens)).scalar() or 0
    
    return OverviewStats(
        total_students=total_students,
        total_tests=total_tests,
        total_shares=total_shares,
        total_opens=total_opens
    )

@router.get(
    "/stats/funnel",
    response_model=FunnelStats,
    summary="获取漏斗数据",
    description="获取转化漏斗数据：扫码进入 -> 完成测评 -> 老师分享 -> 家长打开。"
)
async def get_funnel_stats(
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin)
):
    # 1. Scanned/Entry (Tokens created)
    # Note: Ideally we track 'is_used', but 'created' is a good proxy for 'Entry Intent' or 'Distributed'
    # Let's use 'is_used' for actual entries
    stmt_scanned = select(func.count(StudentEntryTokenModel.id)).where(StudentEntryTokenModel.is_used == True)
    scanned = (await db.execute(stmt_scanned)).scalar() or 0
    
    # 2. Completed Tests
    stmt_completed = select(func.count(TestModel.id)).where(TestModel.status == "completed")
    completed = (await db.execute(stmt_completed)).scalar() or 0
    
    # 3. Shared (Unique tests shared)
    stmt_shared = select(func.count(ReportShareTokenModel.id))
    shared = (await db.execute(stmt_shared)).scalar() or 0
    
    # 4. Opened (Unique shares opened at least once)
    stmt_opened = select(func.count(ReportShareTokenModel.id)).where(ReportShareTokenModel.view_count > 0)
    opened = (await db.execute(stmt_opened)).scalar() or 0
    
    return FunnelStats(
        scanned=scanned,
        completed=completed,
        shared=shared,
        opened=opened
    )

@router.get(
    "/stats/cost",
    response_model=CostStats,
    summary="获取成本估算",
    description="基于测评次数估算 API 成本。"
)
async def get_cost_stats(
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin)
):
    # Total Tests (including failed ones as they might have incurred cost, but let's count all)
    stmt_tests = select(func.count(TestModel.id))
    total_tests = (await db.execute(stmt_tests)).scalar() or 0
    
    # Estimated Cost per Test (CNY)
    # Xunfei Part 1: ~0.05 CNY (Estimate)
    # Qwen Part 2: ~0.01 CNY (Estimate)
    # Total: ~0.06 CNY
    cost_per_test = 0.06
    
    return CostStats(
        total_tests=total_tests,
        estimated_cost_cny=total_tests * cost_per_test
    )
