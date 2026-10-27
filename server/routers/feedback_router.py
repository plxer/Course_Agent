"""用户反馈路由"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import (
    get_admin_user,
    get_current_user,
    get_db,
    get_required_user,
)
from server.utils.common_utils import log_operation
from src.repositories.user_repository import UserRepository
from src.storage.postgres.manager import pg_manager
from src.storage.postgres.models_business import User, UserFeedback
from src.utils import logger
from src.utils.datetime_utils import utc_now_naive

router = APIRouter(prefix="/feedback", tags=["feedback"])


# =============================================================================
# === 请求和响应模型 ===
# =============================================================================


class FeedbackCreate(BaseModel):
    """创建反馈请求"""

    category: str = Field(default="general", pattern="^(general|bug|feature|improvement)$")
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=5000)
    contact: str | None = Field(default=None, max_length=255)


class FeedbackUpdate(BaseModel):
    """更新反馈请求"""

    status: str | None = Field(default=None, pattern="^(pending|processing|resolved|closed)$")
    admin_reply: str | None = Field(default=None, max_length=5000)


class FeedbackResponse(BaseModel):
    """反馈响应"""

    id: int
    user_id: int | None
    username: str | None
    category: str
    title: str
    content: str
    contact: str | None
    status: str
    admin_reply: str | None
    replied_by: str | None
    replied_at: str | None
    created_at: str
    updated_at: str


class FeedbackListResponse(BaseModel):
    """反馈列表响应"""

    total: int
    items: list[FeedbackResponse]


class FeedbackStats(BaseModel):
    """反馈统计"""

    total: int
    pending: int
    processing: int
    resolved: int
    closed: int


# =============================================================================
# === 用户反馈接口 ===
# =============================================================================


@router.post("", response_model=FeedbackResponse)
async def create_feedback(
    feedback_data: FeedbackCreate,
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """提交用户反馈（支持匿名提交）"""
    try:
        # 如果用户已登录，关联用户ID
        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        feedback = UserFeedback(
            user_id=user_id,
            username=username,
            category=feedback_data.category,
            title=feedback_data.title,
            content=feedback_data.content,
            contact=feedback_data.contact,
            status="pending",
        )

        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        # 记录操作日志（如果有登录用户）
        if current_user:
            await log_operation(
                db, current_user.id, "提交反馈", f"反馈标题: {feedback_data.title}", request
            )

        logger.info(f"用户反馈已提交: ID={feedback.id}, 标题={feedback_data.title}")
        return feedback.to_dict()

    except Exception as e:
        logger.error(f"提交反馈失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="提交反馈失败，请稍后重试",
        )


@router.get("/my", response_model=list[FeedbackResponse])
async def get_my_feedbacks(
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """获取当前用户的反馈列表"""
    result = await db.execute(
        select(UserFeedback)
        .where(UserFeedback.user_id == current_user.id)
        .order_by(desc(UserFeedback.created_at))
        .offset(skip)
        .limit(limit)
    )
    feedbacks = result.scalars().all()
    return [f.to_dict() for f in feedbacks]


# =============================================================================
# === 管理员反馈管理接口 ===
# =============================================================================


@router.get("/admin", response_model=FeedbackListResponse)
async def get_all_feedbacks(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, pattern="^(pending|processing|resolved|closed)$"),
    category: str | None = Query(None, pattern="^(general|bug|feature|improvement)$"),
):
    """获取所有反馈列表（管理员权限）"""
    # 构建查询条件
    query = select(UserFeedback)
    count_query = select(func.count(UserFeedback.id))

    if status:
        query = query.where(UserFeedback.status == status)
        count_query = count_query.where(UserFeedback.status == status)

    if category:
        query = query.where(UserFeedback.category == category)
        count_query = count_query.where(UserFeedback.category == category)

    # 执行计数查询
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 执行列表查询
    result = await db.execute(
        query.order_by(desc(UserFeedback.created_at)).offset(skip).limit(limit)
    )
    feedbacks = result.scalars().all()

    return {
        "total": total,
        "items": [f.to_dict() for f in feedbacks],
    }


@router.get("/admin/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取反馈统计数据（管理员权限）"""
    # 总数量
    total_result = await db.execute(select(func.count(UserFeedback.id)))
    total = total_result.scalar()

    # 各状态数量
    status_counts = {}
    for status_value in ["pending", "processing", "resolved", "closed"]:
        count_result = await db.execute(
            select(func.count(UserFeedback.id)).where(UserFeedback.status == status_value)
        )
        status_counts[status_value] = count_result.scalar()

    return {
        "total": total,
        "pending": status_counts["pending"],
        "processing": status_counts["processing"],
        "resolved": status_counts["resolved"],
        "closed": status_counts["closed"],
    }


@router.get("/admin/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_detail(
    feedback_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取反馈详情（管理员权限）"""
    result = await db.execute(
        select(UserFeedback).where(UserFeedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="反馈不存在",
        )

    return feedback.to_dict()


@router.put("/admin/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: int,
    update_data: FeedbackUpdate,
    request: Request,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """更新反馈状态或回复（管理员权限）"""
    result = await db.execute(
        select(UserFeedback).where(UserFeedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="反馈不存在",
        )

    # 更新状态
    if update_data.status is not None:
        feedback.status = update_data.status

    # 更新回复
    if update_data.admin_reply is not None:
        feedback.admin_reply = update_data.admin_reply
        feedback.replied_by = current_user.username
        feedback.replied_at = utc_now_naive()

    await db.commit()
    await db.refresh(feedback)

    # 记录操作日志
    await log_operation(
        db, current_user.id, "处理反馈", f"反馈ID: {feedback_id}, 状态: {feedback.status}", request
    )

    return feedback.to_dict()


@router.delete("/admin/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    request: Request,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """删除反馈（管理员权限）"""
    result = await db.execute(
        select(UserFeedback).where(UserFeedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="反馈不存在",
        )

    await db.delete(feedback)
    await db.commit()

    # 记录操作日志
    await log_operation(db, current_user.id, "删除反馈", f"反馈ID: {feedback_id}", request)

    return {"success": True, "message": "反馈已删除"}
