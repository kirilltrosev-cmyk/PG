from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.common import main_menu
from app.repositories.finance import activate_check
from app.texts import t
from app.utils.users import current_user

router = Router()


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession, bot) -> None:
    settings = get_settings()
    user = await current_user(message, session)

    if message.text and message.text.startswith("/start check_"):
        token = message.text.removeprefix("/start check_").strip()
        status = await activate_check(session, token, user)
        await message.answer(t(user.language, "check_activated" if status == "ok" else "check_bad"))

    await message.answer(
        t(
            user.language,
            "welcome",
            name=user.first_name or "друг",
            project_name=settings.project_name,
            currency_name=settings.currency_name,
        ),
        reply_markup=main_menu(user.is_admin),
    )
