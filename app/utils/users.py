from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.repositories.users import ensure_user


async def current_user(event: Message | CallbackQuery, session: AsyncSession) -> User:
    settings = get_settings()
    tg_user = event.from_user
    referrer_id = None
    if isinstance(event, Message) and event.text and event.text.startswith("/start ref_"):
        raw = event.text.removeprefix("/start ref_").strip()
        referrer_id = int(raw) if raw.isdigit() else None
    user = await ensure_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        admin_ids=settings.admins,
        is_premium=bool(getattr(tg_user, "is_premium", False)),
        referrer_telegram_id=referrer_id,
        referral_bonus=settings.referral_bonus,
    )
    return user
