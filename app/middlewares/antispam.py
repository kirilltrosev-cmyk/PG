from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.services.anti_spam import AntiSpam


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.guard = AntiSpam()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user and not self.guard.allowed(user.id):
            if isinstance(event, CallbackQuery):
                await event.answer("Слишком быстро. Попробуйте еще раз через секунду.", show_alert=False)
                return None
            if isinstance(event, Message):
                return None
        return await handler(event, data)
