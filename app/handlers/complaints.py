from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import Complaint
from app.texts import t
from app.utils.users import current_user

router = Router()


@router.callback_query(F.data.startswith("complain:"))
async def complain(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    task_id = int(callback.data.split(":")[1])
    exists = await session.execute(select(Complaint).where(Complaint.task_id == task_id, Complaint.user_id == user.id))
    if exists.scalar_one_or_none():
        await callback.answer("Жалоба уже принята.", show_alert=True)
        return
    session.add(Complaint(task_id=task_id, user_id=user.id, reason="Пользователь пожаловался через кнопку"))
    await callback.answer("Жалоба сохранена и попадет администратору.", show_alert=True)
