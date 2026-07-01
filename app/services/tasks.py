from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TaskType
from app.models.task import Task
from app.models.user import User
from app.repositories.tasks import mark_paid


async def verify_subscription_task(bot: Bot, session: AsyncSession, task: Task, user: User) -> str:
    if task.type not in {TaskType.CHANNEL.value, TaskType.GROUP.value}:
        return "manual"
    if not task.target_chat_id:
        return "no_chat_id"
    try:
        member = await bot.get_chat_member(task.target_chat_id, user.telegram_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return "api_error"

    if member.status in {"member", "administrator", "creator"}:
        paid = await mark_paid(session, task, user)
        return "paid" if paid else "already"
    return "not_member"
