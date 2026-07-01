import asyncio
import logging

from aiogram import F
from aiogram.types import Message
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent
from aiogram.client.default import DefaultBotProperties

from app.config import get_settings
from app.database.session import init_db
from app.handlers import setup_routers
from app.middlewares.antispam import AntiSpamMiddleware
from app.middlewares.db import DbSessionMiddleware


async def on_error(event: ErrorEvent) -> None:
    logging.exception("Unhandled update error: %s", event.exception)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is empty. Fill .env before running the bot.")

    await init_db()
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

#    @dp.message()
#   async def debug_custom_emoji_id(message: Message):
#        entities = message.entities or message.caption_entities or []
#
#        found = []
#
#        for entity in entities:
#            if entity.type == "custom_emoji":
#                found.append(
#                    f"custom_emoji_id: {entity.custom_emoji_id}\n"
#                    f"offset: {entity.offset}\n"
#                    f"length: {entity.length}"
#                )
#
#        if found:
#            await message.answer("\n\n".join(found))
#        else:
#            await message.answer(
#                "Кастомный эмодзи не найден.\n\n"
#                "Отправь именно emoji из своего набора, не стикер и не картинку."
#            )

    dp.update.middleware(DbSessionMiddleware())
    dp.message.middleware(AntiSpamMiddleware())
    dp.callback_query.middleware(AntiSpamMiddleware())
    dp.include_router(setup_routers())
    dp.errors.register(on_error)

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Открыть главное меню"),
        ]
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
