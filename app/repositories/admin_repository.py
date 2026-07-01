from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.admin_log import AdminLog
from app.models.enums import CompletionStatus, TaskStatus
from app.models.finance import Payment
from app.models.social import Complaint, Referral
from app.models.task import Task, TaskCompletion
from app.models.user import User


def since(days: int) -> datetime:
    return datetime.utcnow() - timedelta(days=days)


async def log_admin_action(session: AsyncSession, admin_id: int, action: str, target_user_id: int | None = None, details: str | None = None) -> None:
    session.add(AdminLog(admin_id=admin_id, target_user_id=target_user_id, action=action, details=details, is_test=get_settings().test_mode))
    await session.flush()


async def admin_summary(session: AsyncSession) -> dict[str, int]:
    return {
        "users_count": int(await session.scalar(select(func.count(User.id))) or 0),
        "active_tasks_count": int(await session.scalar(select(func.count(Task.id)).where(Task.status == TaskStatus.ACTIVE.value)) or 0),
        "pending_proofs_count": int(await session.scalar(select(func.count(TaskCompletion.id)).where(TaskCompletion.status == CompletionStatus.DISPUTED.value)) or 0),
        "complaints_count": int(await session.scalar(select(func.count(Complaint.id)).where(Complaint.status == "new")) or 0),
    }


async def users_summary(session: AsyncSession) -> dict[str, int]:
    return {
        "users_count": int(await session.scalar(select(func.count(User.id))) or 0),
        "today_users_count": int(await session.scalar(select(func.count(User.id)).where(User.created_at >= since(1))) or 0),
        "week_users_count": int(await session.scalar(select(func.count(User.id)).where(User.created_at >= since(7))) or 0),
        "blocked_users_count": int(await session.scalar(select(func.count(User.id)).where(User.is_blocked == True)) or 0),
        "users_with_balance_count": int(await session.scalar(select(func.count(User.id)).where(User.balance > 0)) or 0),
    }


async def list_users(session: AsyncSession, page: int, per_page: int = 5, blocked: bool | None = None, order_by_balance: bool = False) -> tuple[list[User], int]:
    query = select(User)
    if blocked is not None:
        query = query.where(User.is_blocked == blocked)
    order = desc(User.balance) if order_by_balance else desc(User.created_at)
    total = int(await session.scalar(select(func.count()).select_from(query.subquery())) or 0)
    result = await session.execute(query.order_by(order).offset((page - 1) * per_page).limit(per_page))
    return list(result.scalars().all()), total


async def search_users(session: AsyncSession, query: str, limit: int = 8) -> list[User]:
    q = query.strip()
    stmt = select(User)
    if q.isdigit():
        stmt = stmt.where(or_(User.id == int(q), User.telegram_id == int(q)))
    else:
        needle = f"%{q.lstrip('@')}%"
        stmt = stmt.where(or_(User.username.ilike(needle), User.first_name.ilike(needle)))
    result = await session.execute(stmt.order_by(desc(User.created_at)).limit(limit))
    return list(result.scalars().all())


async def user_referrals_count(session: AsyncSession, user_id: int) -> int:
    return int(await session.scalar(select(func.count(Referral.id)).where(Referral.referrer_id == user_id)) or 0)


async def tasks_summary(session: AsyncSession) -> dict[str, int]:
    counts = {}
    for status in TaskStatus:
        counts[status.value] = int(await session.scalar(select(func.count(Task.id)).where(Task.status == status.value)) or 0)
    return counts


async def list_tasks_by_status(session: AsyncSession, status: str, page: int, per_page: int = 5) -> tuple[list[Task], int]:
    query = select(Task).where(Task.status == status)
    total = int(await session.scalar(select(func.count()).select_from(query.subquery())) or 0)
    result = await session.execute(query.order_by(desc(Task.created_at)).offset((page - 1) * per_page).limit(per_page))
    return list(result.scalars().all()), total


async def list_pending_proofs(session: AsyncSession, page: int, per_page: int = 5) -> tuple[list[TaskCompletion], int]:
    query = select(TaskCompletion).where(TaskCompletion.status == CompletionStatus.DISPUTED.value)
    total = int(await session.scalar(select(func.count()).select_from(query.subquery())) or 0)
    result = await session.execute(query.order_by(TaskCompletion.created_at).offset((page - 1) * per_page).limit(per_page))
    return list(result.scalars().all()), total


async def complaints_summary(session: AsyncSession) -> dict[str, int]:
    statuses = ["new", "processing", "accepted", "rejected", "reviewed"]
    return {status: int(await session.scalar(select(func.count(Complaint.id)).where(Complaint.status == status)) or 0) for status in statuses}


async def list_complaints(session: AsyncSession, status: str, page: int, per_page: int = 5) -> tuple[list[Complaint], int]:
    query = select(Complaint).where(Complaint.status == status)
    total = int(await session.scalar(select(func.count()).select_from(query.subquery())) or 0)
    result = await session.execute(query.order_by(desc(Complaint.created_at)).offset((page - 1) * per_page).limit(per_page))
    return list(result.scalars().all()), total


async def payments_summary(session: AsyncSession) -> dict[str, Decimal | int]:
    return {
        "today_payments_sum": Decimal(await session.scalar(select(func.coalesce(func.sum(Payment.amount_internal), 0)).where(Payment.status == "paid", Payment.created_at >= since(1))) or 0),
        "week_payments_sum": Decimal(await session.scalar(select(func.coalesce(func.sum(Payment.amount_internal), 0)).where(Payment.status == "paid", Payment.created_at >= since(7))) or 0),
        "month_payments_sum": Decimal(await session.scalar(select(func.coalesce(func.sum(Payment.amount_internal), 0)).where(Payment.status == "paid", Payment.created_at >= since(30))) or 0),
        "created_payments_count": int(await session.scalar(select(func.count(Payment.id)).where(Payment.status == "created")) or 0),
        "successful_payments_count": int(await session.scalar(select(func.count(Payment.id)).where(Payment.status == "paid")) or 0),
        "pending_payments_count": int(await session.scalar(select(func.count(Payment.id)).where(Payment.status == "pending")) or 0),
        "failed_payments_count": int(await session.scalar(select(func.count(Payment.id)).where(Payment.status == "failed")) or 0),
        "refunded_payments_count": int(await session.scalar(select(func.count(Payment.id)).where(Payment.status == "refunded")) or 0),
        "stars_received": int(await session.scalar(select(func.coalesce(func.sum(Payment.stars_amount), 0)).where(Payment.status == "paid", Payment.payment_currency == "XTR")) or 0),
        "currency_credited": Decimal(await session.scalar(select(func.coalesce(func.sum(Payment.amount_internal), 0)).where(Payment.status == "paid")) or 0),
    }


async def list_payments(session: AsyncSession, status: str | None, page: int, per_page: int = 5) -> tuple[list[Payment], int]:
    query = select(Payment)
    if status:
        query = query.where(Payment.status == status)
    total = int(await session.scalar(select(func.count()).select_from(query.subquery())) or 0)
    result = await session.execute(query.order_by(desc(Payment.created_at)).offset((page - 1) * per_page).limit(per_page))
    return list(result.scalars().all()), total


async def bot_statistics(session: AsyncSession) -> dict[str, Decimal | int]:
    return {
        "users_count": int(await session.scalar(select(func.count(User.id))) or 0),
        "today_users": int(await session.scalar(select(func.count(User.id)).where(User.created_at >= since(1))) or 0),
        "week_users": int(await session.scalar(select(func.count(User.id)).where(User.created_at >= since(7))) or 0),
        "month_users": int(await session.scalar(select(func.count(User.id)).where(User.created_at >= since(30))) or 0),
        "active_tasks": int(await session.scalar(select(func.count(Task.id)).where(Task.status == TaskStatus.ACTIVE.value)) or 0),
        "completed_tasks": int(await session.scalar(select(func.count(TaskCompletion.id)).where(TaskCompletion.status == CompletionStatus.PAID.value)) or 0),
        "pending_proofs": int(await session.scalar(select(func.count(TaskCompletion.id)).where(TaskCompletion.status == CompletionStatus.DISPUTED.value)) or 0),
        "complaints": int(await session.scalar(select(func.count(Complaint.id))) or 0),
        "total_user_balance": Decimal(await session.scalar(select(func.coalesce(func.sum(User.balance), 0))) or 0),
        "today_deposits": Decimal(await session.scalar(select(func.coalesce(func.sum(Payment.amount_internal), 0)).where(Payment.status == "paid", Payment.created_at >= since(1))) or 0),
        "month_deposits": Decimal(await session.scalar(select(func.coalesce(func.sum(Payment.amount_internal), 0)).where(Payment.status == "paid", Payment.created_at >= since(30))) or 0),
    }


async def list_logs(session: AsyncSession, page: int, per_page: int = 5) -> tuple[list[AdminLog], int]:
    query = select(AdminLog)
    total = int(await session.scalar(select(func.count()).select_from(query.subquery())) or 0)
    result = await session.execute(query.order_by(desc(AdminLog.created_at)).offset((page - 1) * per_page).limit(per_page))
    return list(result.scalars().all()), total


async def broadcast_targets(session: AsyncSession, audience: str) -> list[User]:
    query = select(User)
    if audience == "active":
        query = query.where(User.is_blocked == False)
    elif audience == "notifications":
        query = query.where(User.notifications_enabled == True, User.is_blocked == False)
    elif audience == "balance":
        query = query.where(User.balance > 0, User.is_blocked == False)
    result = await session.execute(query)
    return list(result.scalars().all())
