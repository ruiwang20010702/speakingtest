"""
Admin Controller
Handles aggregated statistics for the admin dashboard.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.infrastructure.auth import require_admin, require_teacher, decode_token, oauth2_scheme
from src.adapters.repositories.models import (
    StudentProfileModel, TestModel, ReportShareTokenModel, StudentEntryTokenModel
)

router = APIRouter()

class OverviewStats(BaseModel):
    total_students: int
    total_tests: int
    total_shares: int
    total_opens: int
    pending_followups: int
    failed_tasks: int

class FunnelStats(BaseModel):
    scanned: int
    completed: int
    shared: int
    opened: int

class CostStats(BaseModel):
    total_tests: int
    total_cost_cny: float           # 真实总成本（从数据库读取）
    avg_cost_per_test: float        # 真实平均单次成本
    estimated_cost_cny: float       # 兼容旧字段（保留）

@router.get(
    "/stats/overview",
    response_model=OverviewStats,
    summary="获取概览数据",
    description="获取系统总览数据：学生总数、测评总数、分享次数、打开次数。教师只能看到自己学生的数据。"
)
async def get_overview_stats(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    # Decode token to get user info
    token_data = decode_token(token)
    if token_data is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = token_data.user_id
    role = token_data.role
    
    # Check role - allow admin and teacher
    if role not in ("admin", "teacher"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # For teachers, filter by their students only
    if role == "teacher":
        # Get student IDs for this teacher
        stmt_student_ids = select(StudentProfileModel.user_id).where(
            StudentProfileModel.teacher_id == user_id
        )
        student_ids_result = await db.execute(stmt_student_ids)
        student_ids = [row[0] for row in student_ids_result.fetchall()]
        
        # Total Students (this teacher's students)
        total_students = len(student_ids)
        
        if student_ids:
            # Total Tests (only for this teacher's students)
            stmt_tests = select(func.count(TestModel.id)).where(
                TestModel.student_id.in_(student_ids)
            )
            total_tests = (await db.execute(stmt_tests)).scalar() or 0
            
            # Total Shares (only for this teacher's students' tests)
            stmt_shares = select(func.count(ReportShareTokenModel.id)).where(
                ReportShareTokenModel.test_id.in_(
                    select(TestModel.id).where(TestModel.student_id.in_(student_ids))
                )
            )
            total_shares = (await db.execute(stmt_shares)).scalar() or 0
            
            # Total Opens
            stmt_opens = select(func.sum(ReportShareTokenModel.view_count)).where(
                ReportShareTokenModel.test_id.in_(
                    select(TestModel.id).where(TestModel.student_id.in_(student_ids))
                )
            )
            total_opens = (await db.execute(stmt_opens)).scalar() or 0
            
            # Pending Follow-ups
            stmt_pending = select(func.count(TestModel.id)).where(
                TestModel.student_id.in_(student_ids),
                TestModel.status.in_(['pending', 'part1_done', 'processing', 'failed'])
            )
            pending_followups = (await db.execute(stmt_pending)).scalar() or 0
            
            # Failed Tasks
            stmt_failed = select(func.count(TestModel.id)).where(
                TestModel.student_id.in_(student_ids),
                TestModel.status == 'failed'
            )
            failed_tasks = (await db.execute(stmt_failed)).scalar() or 0
        else:
            total_tests = 0
            total_shares = 0
            total_opens = 0
            pending_followups = 0
            failed_tasks = 0
    else:
        # Admin: show all data
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
        
        # Pending Follow-ups (tests not completed)
        stmt_pending = select(func.count(TestModel.id)).where(
            TestModel.status.in_(['pending', 'part1_done', 'processing', 'failed'])
        )
        pending_followups = (await db.execute(stmt_pending)).scalar() or 0
        
        # Failed Tasks count
        stmt_failed = select(func.count(TestModel.id)).where(
            TestModel.status == 'failed'
        )
        failed_tasks = (await db.execute(stmt_failed)).scalar() or 0
    
    return OverviewStats(
        total_students=total_students,
        total_tests=total_tests,
        total_shares=total_shares,
        total_opens=total_opens,
        pending_followups=pending_followups,
        failed_tasks=failed_tasks
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
    summary="获取成本统计",
    description="获取真实的 API 调用成本统计（从数据库读取）。"
)
async def get_cost_stats(
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin)
):
    # TODO: 性能优化 - 当测评数据量超过 10 万条时，考虑以下方案：
    # 1. 内存缓存 + TTL（5分钟）：适合单实例部署
    # 2. Redis 缓存：适合多实例部署
    # 3. 数据库汇总表：实时增量更新，最精确
    # 当前实现：全表聚合查询（数据量小时性能足够）
    
    # Total Tests
    stmt_tests = select(func.count(TestModel.id))
    total_tests = (await db.execute(stmt_tests)).scalar() or 0
    
    # 真实总成本（从 tests.cost 字段求和）
    stmt_cost = select(func.sum(TestModel.cost))
    total_cost = (await db.execute(stmt_cost)).scalar() or 0
    total_cost_cny = float(total_cost)
    
    # 计算真实平均单次成本
    avg_cost_per_test = total_cost_cny / total_tests if total_tests > 0 else 0
    
    return CostStats(
        total_tests=total_tests,
        total_cost_cny=total_cost_cny,
        avg_cost_per_test=avg_cost_per_test,
        estimated_cost_cny=total_cost_cny  # 兼容旧字段，现在使用真实值
    )


# ============================================
# Teacher Management
# ============================================

from typing import List, Optional

class TeacherSummary(BaseModel):
    """Teacher summary for list view."""
    user_id: int
    email: str
    ss_crm_name: Optional[str] = None
    ss_dept4_name: Optional[str] = None
    student_count: int
    test_count: int
    share_count: int


class TeacherListResponse(BaseModel):
    """Paginated teacher list response."""
    total: int
    page: int
    limit: int
    total_students: int
    total_tests: int
    total_shares: int
    items: List[TeacherSummary]


class TeacherDetail(BaseModel):
    """Teacher detail with student distribution."""
    user_id: int
    email: str
    ss_crm_name: Optional[str] = None
    ss_name: Optional[str] = None
    ss_sm_name: Optional[str] = None
    ss_dept4_name: Optional[str] = None
    ss_group: Optional[str] = None
    student_count: int
    test_count: int
    completed_tests: int
    share_count: int
    students: List[dict]


from src.adapters.repositories.models import UserModel


@router.get(
    "/teachers",
    response_model=TeacherListResponse,
    summary="获取老师列表（分页）",
    description="获取所有老师的汇总信息，支持分页。"
)
async def list_teachers(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin)
):
    """Get list of all teachers with summary stats (paginated).
    
    Optimized: Uses batch queries instead of N+1 queries.
    - Before: 3 * N queries (N = number of teachers), ~8 seconds for 60 teachers
    - After: 5 queries total, ~200ms
    """
    # Validate pagination params
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 20
    
    offset = (page - 1) * limit
    
    # 1. Get total count of teachers
    stmt_count = select(func.count(UserModel.id)).where(UserModel.role == 'teacher')
    total = (await db.execute(stmt_count)).scalar() or 0
    
    if total == 0:
        return TeacherListResponse(
            total=0, page=page, limit=limit,
            total_students=0, total_tests=0, total_shares=0,
            items=[]
        )
    
    # 2. Get paginated teachers
    stmt = (
        select(UserModel)
        .where(UserModel.role == 'teacher')
        .order_by(UserModel.id)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    teachers = result.scalars().all()
    
    if not teachers:
        return TeacherListResponse(
            total=total, page=page, limit=limit,
            total_students=0, total_tests=0, total_shares=0,
            items=[]
        )
    
    teacher_ids = [t.id for t in teachers]
    
    # 3. Batch query: student count per teacher (1 query)
    stmt_students = (
        select(
            StudentProfileModel.teacher_id,
            func.count(StudentProfileModel.user_id).label('count')
        )
        .where(StudentProfileModel.teacher_id.in_(teacher_ids))
        .group_by(StudentProfileModel.teacher_id)
    )
    result = await db.execute(stmt_students)
    student_counts = {row.teacher_id: row.count for row in result.all()}
        
    # 4. Batch query: test count per teacher (1 query)
    stmt_tests = (
        select(
            StudentProfileModel.teacher_id,
            func.count(TestModel.id).label('count')
        )
        .select_from(TestModel)
        .join(StudentProfileModel, TestModel.student_id == StudentProfileModel.user_id)
        .where(StudentProfileModel.teacher_id.in_(teacher_ids))
        .group_by(StudentProfileModel.teacher_id)
    )
    result = await db.execute(stmt_tests)
    test_counts = {row.teacher_id: row.count for row in result.all()}
    
    # 5. Batch query: share count per teacher (1 query)
    stmt_shares = (
        select(
            ReportShareTokenModel.created_by,
            func.count(ReportShareTokenModel.id).label('count')
        )
        .where(ReportShareTokenModel.created_by.in_(teacher_ids))
        .group_by(ReportShareTokenModel.created_by)
    )
    result = await db.execute(stmt_shares)
    share_counts = {row.created_by: row.count for row in result.all()}
    
    # Assemble results
    items = [
        TeacherSummary(
            user_id=teacher.id,
            email=teacher.email or "",
            ss_crm_name=teacher.ss_crm_name,
            ss_dept4_name=teacher.ss_dept4_name,
            student_count=student_counts.get(teacher.id, 0),
            test_count=test_counts.get(teacher.id, 0),
            share_count=share_counts.get(teacher.id, 0)
        )
        for teacher in teachers
    ]
    
    # Calculate totals for current page
    total_students = sum(student_counts.values())
    total_tests = sum(test_counts.values())
    total_shares = sum(share_counts.values())
    
    return TeacherListResponse(
        total=total,
        page=page,
        limit=limit,
        total_students=total_students,
        total_tests=total_tests,
        total_shares=total_shares,
        items=items
    )


@router.get(
    "/teachers/{teacher_id}",
    response_model=TeacherDetail,
    summary="获取老师详情",
    description="获取指定老师的详细信息，包括学生分布。"
)
async def get_teacher_detail(
    teacher_id: int,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin)
):
    """Get teacher detail with student list."""
    # Get teacher
    stmt = select(UserModel).where(UserModel.id == teacher_id, UserModel.role == 'teacher')
    result = await db.execute(stmt)
    teacher = result.scalar_one_or_none()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found"
        )
    
    # Get students with test counts
    stmt_students = (
        select(
            StudentProfileModel.user_id,
            StudentProfileModel.student_name,
            func.count(TestModel.id).label('test_count')
        )
        .outerjoin(TestModel, TestModel.student_id == StudentProfileModel.user_id)
        .where(StudentProfileModel.teacher_id == teacher_id)
        .group_by(StudentProfileModel.user_id, StudentProfileModel.student_name)
    )
    result = await db.execute(stmt_students)
    students = [
        {"user_id": row.user_id, "student_name": row.student_name, "test_count": row.test_count}
        for row in result.all()
    ]
    
    # Aggregate counts
    student_count = len(students)
    test_count = sum(s['test_count'] for s in students)
    
    # Completed tests
    stmt_completed = (
        select(func.count(TestModel.id))
        .join(StudentProfileModel, TestModel.student_id == StudentProfileModel.user_id)
        .where(StudentProfileModel.teacher_id == teacher_id, TestModel.status == 'completed')
    )
    completed_tests = (await db.execute(stmt_completed)).scalar() or 0
    
    # Shares
    stmt_shares = select(func.count(ReportShareTokenModel.id)).where(
        ReportShareTokenModel.created_by == teacher_id
    )
    share_count = (await db.execute(stmt_shares)).scalar() or 0
    
    return TeacherDetail(
        user_id=teacher.id,
        email=teacher.email or "",
        ss_crm_name=teacher.ss_crm_name,
        ss_name=teacher.ss_name,
        ss_sm_name=teacher.ss_sm_name,
        ss_dept4_name=teacher.ss_dept4_name,
        ss_group=teacher.ss_group,
        student_count=student_count,
        test_count=test_count,
        completed_tests=completed_tests,
        share_count=share_count,
        students=students
    )


# ============================================
# Audit Log Query
# ============================================

from datetime import datetime
from src.adapters.repositories.models import AuditLogModel


class AuditLogItem(BaseModel):
    """Audit log entry."""
    id: int
    operator_id: int
    operator_email: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    details: Optional[dict] = None
    client_ip: Optional[str] = None
    created_at: datetime


class AuditLogResponse(BaseModel):
    """Paginated audit log response."""
    total: int
    page: int
    limit: int
    items: List[AuditLogItem]


@router.get(
    "/audit-logs",
    response_model=AuditLogResponse,
    summary="查询审计日志",
    description="分页查询系统审计日志，支持按操作类型、操作人筛选。"
)
async def query_audit_logs(
    action: Optional[str] = None,
    operator_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin)
):
    """Query audit logs with optional filters."""
    # Base query
    stmt = select(AuditLogModel).order_by(AuditLogModel.created_at.desc())
    count_stmt = select(func.count(AuditLogModel.id))
    
    # Apply filters
    if action:
        stmt = stmt.where(AuditLogModel.action == action)
        count_stmt = count_stmt.where(AuditLogModel.action == action)
    
    if operator_id:
        stmt = stmt.where(AuditLogModel.operator_id == operator_id)
        count_stmt = count_stmt.where(AuditLogModel.operator_id == operator_id)
    
    # Total count
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # Pagination
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)
    
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    # Get operator emails
    operator_ids = list(set(log.operator_id for log in logs if log.operator_id))
    emails = {}
    if operator_ids:
        stmt_users = select(UserModel.id, UserModel.email).where(UserModel.id.in_(operator_ids))
        result = await db.execute(stmt_users)
        emails = {row.id: row.email for row in result.all()}
    
    items = [
        AuditLogItem(
            id=log.id,
            operator_id=log.operator_id,
            operator_email=emails.get(log.operator_id),
            action=log.action,
            target_type=log.target_type,
            target_id=log.target_id,
            details=log.details,
            client_ip=log.client_ip,
            created_at=log.created_at
        )
        for log in logs
    ]
    
    return AuditLogResponse(
        total=total,
        page=page,
        limit=limit,
        items=items
    )


# ============================================
# Failed Task Management
# ============================================

class FailedTaskItem(BaseModel):
    """Failed task entry."""
    test_id: int
    student_name: Optional[str] = None
    student_id: int
    level: str
    unit: str
    status: str
    failure_reason: Optional[str] = None
    retry_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class FailedTasksResponse(BaseModel):
    """Failed tasks list response."""
    total: int
    items: List[FailedTaskItem]


class RetryTaskResponse(BaseModel):
    """Retry task response."""
    success: bool
    message: str
    test_id: int


@router.get(
    "/failed-tasks",
    response_model=FailedTasksResponse,
    summary="查看失败任务",
    description="查看所有失败的测评任务。卡住超过5分钟的任务会自动标记为失败。"
)
async def list_failed_tasks(
    max_retry: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin)
):
    """List all failed tests. Stuck tasks are auto-marked as failed."""
    from datetime import timedelta
    from src.infrastructure.timezone import now as china_now
    from sqlalchemy import or_, and_
    
    # 先将卡住的任务标记为 failed
    STUCK_THRESHOLD_MINUTES = 5
    stuck_threshold = china_now() - timedelta(minutes=STUCK_THRESHOLD_MINUTES)
    
    # 查找卡住的任务
    stuck_stmt = (
        select(TestModel)
        .where(
            or_(
                and_(
                    TestModel.status == 'part1_processing',
                    TestModel.updated_at < stuck_threshold
                ),
                and_(
                    TestModel.status == 'processing',
                    TestModel.updated_at < stuck_threshold
                )
            )
        )
    )
    stuck_result = await db.execute(stuck_stmt)
    stuck_tests = stuck_result.scalars().all()
    
    # 将卡住的任务标记为 failed
    for test in stuck_tests:
        original_status = test.status
        test.status = 'failed'
        test.failure_reason = f"任务处理超时（原状态: {original_status}，超过 {STUCK_THRESHOLD_MINUTES} 分钟未完成）"
        test.updated_at = china_now()
    
    if stuck_tests:
        await db.commit()
    
    # 查询所有失败的任务
    stmt = (
        select(TestModel, StudentProfileModel.student_name)
        .outerjoin(StudentProfileModel, TestModel.student_id == StudentProfileModel.user_id)
        .where(TestModel.status == 'failed')
        .order_by(TestModel.updated_at.desc())
    )
    
    if max_retry is not None:
        stmt = stmt.where(TestModel.retry_count <= max_retry)
    
    result = await db.execute(stmt)
    rows = result.all()
    
    items = [
        FailedTaskItem(
            test_id=test.id,
            student_name=student_name,
            student_id=test.student_id,
            level=test.level,
            unit=test.unit,
            status=test.status,
            failure_reason=test.failure_reason,
            retry_count=test.retry_count or 0,
            created_at=test.created_at,
            updated_at=test.updated_at
        )
        for test, student_name in rows
    ]
    
    return FailedTasksResponse(
        total=len(items),
        items=items
    )


@router.post(
    "/failed-tasks/{test_id}/retry",
    response_model=RetryTaskResponse,
    summary="重试失败任务",
    description="将失败的测评任务重新加入队列处理。"
)
async def retry_failed_task(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin)
):
    """Retry a failed test by re-enqueuing to message queue."""
    # Get test
    stmt = select(TestModel).where(TestModel.id == test_id)
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    if test.status != 'failed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Test status is '{test.status}', only 'failed' tests can be retried"
        )
    
    # Check retry limit (max 3 retries)
    MAX_RETRIES = 3
    if (test.retry_count or 0) >= MAX_RETRIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum retry limit ({MAX_RETRIES}) reached"
        )
    
    # Re-enqueue task
    try:
        from src.infrastructure.queue_service import Part2Task, enqueue_part2_task
        from src.adapters.repositories.models import QuestionModel
        
        # Get questions for this test
        stmt = select(QuestionModel).where(
            QuestionModel.level == test.level,
            QuestionModel.unit == test.unit,
            QuestionModel.part == 2,
            QuestionModel.is_active == True
        ).order_by(QuestionModel.question_no)
        result = await db.execute(stmt)
        questions = result.scalars().all()
        
        question_list = [
            {"no": q.question_no, "question": q.question, "reference_answer": q.reference_answer}
            for q in questions
        ]
        
        # Create and enqueue task
        import uuid
        task = Part2Task(
            task_id=f"retry-{test_id}-{str(uuid.uuid4())[:4]}",
            test_id=test_id,
            audio_url=test.part2_audio_url,
            questions=question_list
        )
        
        await enqueue_part2_task(task)
        
        # Update test status
        test.status = 'processing'
        test.failure_reason = None
        await db.commit()
        
        return RetryTaskResponse(
            success=True,
            message="Task re-enqueued for processing",
            test_id=test_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry task: {str(e)}"
        )


class RegenerateReportRequest(BaseModel):
    """请求重新生成报告"""
    reference_text: Optional[str] = None  # Part 1 的参考文本，如果不提供则从数据库获取


class RegenerateReportResponse(BaseModel):
    """重新生成报告响应"""
    success: bool
    message: str
    test_id: int
    part1_queued: bool = False
    part2_queued: bool = False


@router.post(
    "/tests/{test_id}/regenerate",
    response_model=RegenerateReportResponse,
    summary="重新生成报告",
    description="教师手动触发重新生成学生报告。要求两段音频的 OSS 链接都已保存。"
)
async def regenerate_report(
    test_id: int,
    request: RegenerateReportRequest = None,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_teacher)
):
    """
    教师手动重新生成学生报告。
    
    适用场景：
    - 任务卡住（part1_processing 或 processing 状态）
    - 任务失败（failed 状态）
    - 需要重新评测
    
    前提条件：
    - Part 1 音频链接已保存（part1_audio_url）
    - Part 2 音频链接已保存（part2_audio_url）
    """
    import uuid
    import logging
    from src.infrastructure.queue_service import Part1Task, Part2Task, enqueue_part1_task, enqueue_part2_task
    from src.adapters.repositories.models import QuestionModel
    from src.infrastructure.timezone import now as china_now
    
    logger = logging.getLogger(__name__)
    
    # 1. 获取测试信息
    stmt = select(TestModel).where(TestModel.id == test_id)
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测评记录不存在"
        )
    
    # 2. 检查 OSS 链接是否存在
    if not test.part1_audio_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Part 1 音频链接不存在，无法重新生成报告"
        )
    
    if not test.part2_audio_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Part 2 音频链接不存在，无法重新生成报告"
        )
    
    # 3. 检查重试次数限制
    MAX_RETRIES = 5
    if (test.retry_count or 0) >= MAX_RETRIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"已达到最大重试次数 ({MAX_RETRIES})，请联系技术支持"
        )
    
    # 4. 获取 Part 1 参考文本
    reference_text = request.reference_text if request else None
    if not reference_text:
        # 从数据库获取该 level/unit 的 Part 1 参考文本
        stmt = select(QuestionModel).where(
            QuestionModel.level == test.level,
            QuestionModel.unit == test.unit,
            QuestionModel.part == 1,
            QuestionModel.is_active == True
        ).limit(1)
        result = await db.execute(stmt)
        part1_question = result.scalar_one_or_none()
        if part1_question:
            reference_text = part1_question.question  # Part 1 的 question 就是参考文本
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"找不到 {test.level} - {test.unit} 的 Part 1 参考文本"
            )
    
    # 5. 获取 Part 2 题目
    stmt = select(QuestionModel).where(
        QuestionModel.level == test.level,
        QuestionModel.unit == test.unit,
        QuestionModel.part == 2,
        QuestionModel.is_active == True
    ).order_by(QuestionModel.question_no)
    result = await db.execute(stmt)
    questions = result.scalars().all()
    
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"找不到 {test.level} - {test.unit} 的 Part 2 题目"
        )
    
    question_list = [
        {"no": q.question_no, "question": q.question, "reference_answer": q.reference_answer or "无"}
        for q in questions
    ]
    
    # 6. 根据当前状态决定从哪里开始
    part1_queued = False
    part2_queued = False
    
    try:
        # 如果 Part 1 还没完成（pending, part1_processing, failed），从 Part 1 开始
        if test.status in ('pending', 'part1_processing', 'failed') or test.part1_score is None:
            task_id = f"regen-p1-{test_id}-{str(uuid.uuid4())[:4]}"
            task = Part1Task(
                task_id=task_id,
                test_id=test_id,
                audio_url=test.part1_audio_url,
                reference_text=reference_text
            )
            await enqueue_part1_task(task)
            test.status = 'part1_processing'
            part1_queued = True
            logger.info(f"重新生成报告: Part 1 任务已入队 task_id={task_id}")
        
        # 如果 Part 1 已完成，但 Part 2 没完成，只重试 Part 2
        elif test.status in ('part1_done', 'processing') or test.part2_score is None:
            task_id = f"regen-p2-{test_id}-{str(uuid.uuid4())[:4]}"
            task = Part2Task(
                task_id=task_id,
                test_id=test_id,
                audio_url=test.part2_audio_url,
                questions=question_list
            )
            await enqueue_part2_task(task)
            test.status = 'processing'
            part2_queued = True
            logger.info(f"重新生成报告: Part 2 任务已入队 task_id={task_id}")
        
        # 如果已经完成，但教师想重新生成，从 Part 1 开始
        elif test.status == 'completed':
            task_id = f"regen-p1-{test_id}-{str(uuid.uuid4())[:4]}"
            task = Part1Task(
                task_id=task_id,
                test_id=test_id,
                audio_url=test.part1_audio_url,
                reference_text=reference_text
            )
            await enqueue_part1_task(task)
            test.status = 'part1_processing'
            part1_queued = True
            logger.info(f"重新生成报告: 已完成测试重新评测，Part 1 任务已入队 task_id={task_id}")
        
        # 更新测试记录
        test.retry_count = (test.retry_count or 0) + 1
        test.failure_reason = f"教师手动触发重新生成 (第 {test.retry_count} 次)"
        test.updated_at = china_now()
        await db.commit()
        
        message_parts = []
        if part1_queued:
            message_parts.append("Part 1 评测任务已入队")
        if part2_queued:
            message_parts.append("Part 2 评测任务已入队")
        
        return RegenerateReportResponse(
            success=True,
            message="，".join(message_parts) + "，请等待处理完成",
            test_id=test_id,
            part1_queued=part1_queued,
            part2_queued=part2_queued
        )
        
    except Exception as e:
        logger.exception(f"重新生成报告失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新生成报告失败: {str(e)}"
        )


