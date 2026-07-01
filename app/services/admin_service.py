import asyncio
from decimal import Decimal

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TaskStatus
from app.models.social import Complaint
from app.models.task import Task
from app.models.user import User
from app.repositories.admin_repository import log_admin_action


def parse_amount(value: str) -> Decimal | None:
    try:
        amount = Decimal(value.replace(" ", "").replace(",", "."))
    except Exception:
        return None
    return amount if amount >= 0 else None


async def apply_balance_action(session: AsyncSession, admin: User, target: User, action: str, amount: Decimal) -> str:
    before = target.balance
    if action == "add":
        target.balance += amount
    elif action == "subtract":
        if target.balance < amount:
            return "Недостаточно средств у пользователя."
        target.balance -= amount
    elif action == "set":
        target.balance = amount
    else:
        return "Неизвестное действие."
    await log_admin_action(session, admin.id, f"balance_{action}", target.id, f"{before} -> {target.balance}")
    return "Баланс обновлён."


async def set_user_block(session: AsyncSession, admin: User, target: User, blocked: bool) -> str:
    target.is_blocked = blocked
    await log_admin_action(session, admin.id, "user_block" if blocked else "user_unblock", target.id)
    return "Пользователь заблокирован." if blocked else "Пользователь разблокирован."


async def set_task_status(session: AsyncSession, admin: User, task: Task, status: str) -> str:
    task.status = status
    await log_admin_action(session, admin.id, f"task_{status}", task.creator_id, f"task_id={task.id}")
    return "Статус задания обновлён."


async def set_complaint_status(session: AsyncSession, admin: User, complaint: Complaint, status: str) -> str:
    complaint.status = status
    await log_admin_action(session, admin.id, f"complaint_{status}", complaint.user_id, f"complaint_id={complaint.id}")
    return "Статус жалобы обновлён."


async def run_broadcast(bot, users: list[User], text: str) -> dict[str, int]:
    sent = 0
    errors = 0
    for user in users:
        try:
            await bot.send_message(user.telegram_id, text)
            sent += 1
        except (TelegramBadRequest, TelegramForbiddenError):
            errors += 1
        await asyncio.sleep(0.05)
    return {"sent": sent, "errors": errors, "total": len(users)}
