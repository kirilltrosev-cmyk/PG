from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TaskStatus
from app.models.finance import Payment
from app.models.social import Complaint, Referral
from app.models.task import Task, TaskCompletion
from app.models.user import User


async def project_stats(session: AsyncSession) -> dict[str, int]:
    return {
        "users": int(await session.scalar(select(func.count(User.id))) or 0),
        "active_tasks": int(await session.scalar(select(func.count(Task.id)).where(Task.status == TaskStatus.ACTIVE.value)) or 0),
        "completed": int(await session.scalar(select(func.count(TaskCompletion.id))) or 0),
        "payments": int(await session.scalar(select(func.count(Payment.id))) or 0),
        "complaints": int(await session.scalar(select(func.count(Complaint.id))) or 0),
    }


async def referral_stats(session: AsyncSession, user_id: int) -> dict[str, int]:
    referrals = int(await session.scalar(select(func.count(Referral.id)).where(Referral.referrer_id == user_id)) or 0)
    earned = int(await session.scalar(select(func.coalesce(func.sum(Referral.bonus_amount), 0)).where(Referral.referrer_id == user_id)) or 0)
    return {"referrals_count": referrals, "referral_earned": earned}
