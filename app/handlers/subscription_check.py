from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramUnauthorizedError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message
from html import escape
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.common import (
    op_actions_keyboard,
    op_add_bot_keyboard,
    op_add_group_keyboard,
    op_channels_keyboard,
    op_check_user_keyboard,
    op_commands_keyboard,
    op_empty_groups_keyboard,
    op_group_keyboard,
    op_groups_keyboard,
    op_warning_keyboard,
    op_whitelist_keyboard,
    subscription_check_keyboard,
)
from app.models.social import OpGroup
from app.repositories.op import (
    DEFAULT_SETTINGS,
    add_required_channel,
    connected_bots_by_owner_id,
    add_whitelist_user,
    delete_required_channel,
    delete_whitelist_user,
    group_stats,
    is_whitelisted,
    load_settings,
    log_event,
    owner_groups,
    required_channels,
    save_settings,
    upsert_group,
    upsert_connected_bot,
    whitelist_users,
)
from app.states import SubscriptionCheck
from app.texts import t
from app.utils.formatting import tree_list
from app.utils.menu_match import menu_variants
from app.utils.secrets import decrypt_token, encrypt_token, token_hint
from app.utils.users import current_user

router = Router()

ACTION_LABELS = {
    "warn": "только предупреждение",
    "delete": "удалять сообщения",
    "mute": "временно ограничивать",
    "kick": "исключать из группы",
}


def clean_chat_id(value: str) -> str:
    return value.strip().removeprefix("https://t.me/").removeprefix("http://t.me/").removeprefix("t.me/")


async def bot_is_chat_admin(bot, chat_id: int | str) -> bool:
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id, me.id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return False
    return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


def op_bot_admin_required_text(target_kind: str = "чате") -> str:
    return (
        f"Бот должен быть администратором в этом {target_kind}, иначе проверка подписки не сможет работать корректно.\n\n"
        "Добавьте бота администратором и повторите действие."
    )


async def show_main(target: Message | CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    user = await current_user(target, session)
    text = t(user.language, "op", project_name=settings.project_name)
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=subscription_check_keyboard())
    else:
        await target.answer(text, reply_markup=subscription_check_keyboard())


async def show_group(callback: CallbackQuery, session: AsyncSession, group_id: int) -> None:
    user = await current_user(callback, session)
    group = await session.get(OpGroup, group_id)
    if not group or group.owner_id != user.id:
        await callback.answer("Группа не найдена.", show_alert=True)
        return
    settings = load_settings(group)
    channels = await required_channels(session, group.id)
    await callback.message.edit_text(
        t(
            user.language,
            "op_group_card",
            title=escape(group.title),
            enabled="включено" if group.is_enabled else "выключено",
            channels_count=len(channels),
            action=ACTION_LABELS.get(settings["violation_action"], settings["violation_action"]),
            warning_text=escape(settings["warning_text"]),
        ),
        reply_markup=op_group_keyboard(group.id, group.is_enabled),
    )


async def check_user_subscriptions(bot, session: AsyncSession, group: OpGroup, user_id: int) -> tuple[bool, list[str]]:
    missing = []
    channels = await required_channels(session, group.id)
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel.channel_id, user_id)
        except (TelegramBadRequest, TelegramForbiddenError):
            missing.append(channel.title)
            continue
        if member.status not in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}:
            missing.append(channel.title)
    for connected_bot in await connected_bots_by_owner_id(session, group.owner_id):
        try:
            token = decrypt_token(connected_bot.token_secret)
        except (UnicodeDecodeError, ValueError):
            missing.append(f"бот @{connected_bot.username}")
            continue
        candidate = Bot(token=token)
        try:
            await candidate.get_chat(user_id)
        except (TelegramBadRequest, TelegramForbiddenError, TelegramUnauthorizedError):
            missing.append(f"бот @{connected_bot.username}")
        finally:
            await candidate.session.close()
    return not missing, missing


async def group_by_chat(session: AsyncSession, chat_id: int) -> OpGroup | None:
    result = await session.execute(select(OpGroup).where(OpGroup.chat_id == str(chat_id)))
    return result.scalar_one_or_none()


def command_enabled(group: OpGroup, command: str) -> bool:
    return load_settings(group)["commands"].get(command, True)


@router.message(StateFilter("*"), F.text.in_(menu_variants("Проверка подписки")))
async def op_message(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    await show_main(message, session)


@router.callback_query(F.data == "op:main")
async def op_main(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    await show_main(callback, session)
    await callback.answer()


@router.my_chat_member()
async def remember_group(event: ChatMemberUpdated, session: AsyncSession) -> None:
    if event.chat.type not in {"group", "supergroup"}:
        return
    if event.new_chat_member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}:
        owner = await current_user(event, session)
        await upsert_group(session, owner, str(event.chat.id), event.chat.title or str(event.chat.id))


@router.callback_query(F.data == "op:groups")
async def op_groups(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    groups = await owner_groups(session, user)
    if not groups:
        await callback.message.edit_text(t(user.language, "op_groups_empty"), reply_markup=op_empty_groups_keyboard())
        await callback.answer()
        return
    lines = []
    for index, group in enumerate(groups, start=1):
        settings = load_settings(group)
        channels = await required_channels(session, group.id)
        lines.append(
            f"{index}. {escape(group.title)}\n"
            f"   Статус: {'включено' if group.is_enabled else 'выключено'}\n"
            f"   Условий: {len(channels)}\n"
            f"   Действие: {ACTION_LABELS.get(settings['violation_action'], settings['violation_action'])}"
        )
    await callback.message.edit_text(t(user.language, "op_groups", items=tree_list(lines)), reply_markup=op_groups_keyboard([g.id for g in groups]))
    await callback.answer()


@router.callback_query(F.data.startswith("op:group:"))
async def op_group(callback: CallbackQuery, session: AsyncSession) -> None:
    await show_group(callback, session, int(callback.data.split(":")[2]))
    await callback.answer()


@router.callback_query(F.data.startswith("op:toggle:"))
async def op_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    group = await session.get(OpGroup, int(callback.data.split(":")[2]))
    if group:
        group.is_enabled = not group.is_enabled
        await show_group(callback, session, group.id)
    await callback.answer()


@router.callback_query(F.data.startswith("op:channels:"))
async def op_channels(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    group_id = int(callback.data.split(":")[2])
    channels = await required_channels(session, group_id)
    items = tree_list([f"#{item.id}: {item.title} ({item.channel_url})" for item in channels]) or "Список пока пуст."
    await callback.message.edit_text(t(user.language, "op_channels", items=items), reply_markup=op_channels_keyboard(group_id, [c.id for c in channels]))
    await callback.answer()


@router.callback_query(F.data.startswith("op:channel_add:"))
async def op_channel_add(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(callback, session)
    group_id = int(callback.data.split(":")[2])
    await state.set_state(SubscriptionCheck.waiting_channel)
    await state.update_data(op_group_id=group_id)
    await callback.message.edit_text(t(user.language, "op_channel_ask"))
    await callback.answer()


@router.message(SubscriptionCheck.waiting_channel)
async def op_channel_save(message: Message, session: AsyncSession, state: FSMContext, bot) -> None:
    user = await current_user(message, session)
    data = await state.get_data()
    group = await session.get(OpGroup, int(data["op_group_id"]))
    target = clean_chat_id(message.text or "")
    if not group or not target:
        await message.answer(t(user.language, "op_channel_bad"))
        await state.clear()
        return
    chat_id = target if target.startswith("-") else f"@{target.lstrip('@')}"
    try:
        chat = await bot.get_chat(chat_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        await message.answer(t(user.language, "op_channel_bad"))
        return
    if not await bot_is_chat_admin(bot, chat.id):
        target_kind = "канале" if chat.type == "channel" else "группе"
        await message.answer(op_bot_admin_required_text(target_kind))
        return
    await add_required_channel(session, group, str(chat.id), chat.title or chat.username or str(chat.id), f"https://t.me/{chat.username}" if chat.username else str(chat.id))
    await state.clear()
    await message.answer("Канал добавлен в обязательные условия.")


@router.callback_query(F.data.startswith("op:channel_delete:"))
async def op_channel_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    _, _, group_id, channel_id = callback.data.split(":")
    await delete_required_channel(session, int(channel_id), int(group_id))
    await callback.answer("Канал удалён.", show_alert=True)
    await op_channels(callback, session)


@router.callback_query(F.data.startswith("op:channel_check:"))
async def op_channel_check(callback: CallbackQuery) -> None:
    await callback.answer("Доступ проверяется при добавлении канала. Если канал приватный, добавьте бота администратором.", show_alert=True)


@router.callback_query(F.data.startswith("op:warning:"))
async def op_warning(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    group = await session.get(OpGroup, int(callback.data.split(":")[2]))
    settings = load_settings(group)
    await callback.message.edit_text(t(user.language, "op_warning", warning_text=settings["warning_text"]), reply_markup=op_warning_keyboard(group.id))
    await callback.answer()


@router.callback_query(F.data.startswith("op:warning_edit:"))
async def op_warning_edit(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(callback, session)
    await state.set_state(SubscriptionCheck.waiting_warning_text)
    await state.update_data(op_group_id=int(callback.data.split(":")[2]))
    await callback.message.edit_text(t(user.language, "op_warning_ask"))
    await callback.answer()


@router.message(SubscriptionCheck.waiting_warning_text)
async def op_warning_save(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    group = await session.get(OpGroup, int(data["op_group_id"]))
    settings = load_settings(group)
    settings["warning_text"] = message.text or DEFAULT_SETTINGS["warning_text"]
    save_settings(group, settings)
    await state.clear()
    await message.answer("Текст предупреждения сохранён.")


@router.callback_query(F.data.startswith("op:warning_reset:"))
async def op_warning_reset(callback: CallbackQuery, session: AsyncSession) -> None:
    group = await session.get(OpGroup, int(callback.data.split(":")[2]))
    settings = load_settings(group)
    settings["warning_text"] = DEFAULT_SETTINGS["warning_text"]
    save_settings(group, settings)
    await callback.answer("Текст сброшен.", show_alert=True)
    await show_group(callback, session, group.id)


@router.callback_query(F.data.startswith("op:actions:"))
async def op_actions(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    group_id = int(callback.data.split(":")[2])
    await callback.message.edit_text(t(user.language, "op_actions"), reply_markup=op_actions_keyboard(group_id))
    await callback.answer()


@router.callback_query(F.data.startswith("op:action:"))
async def op_action_set(callback: CallbackQuery, session: AsyncSession) -> None:
    _, _, group_id, action = callback.data.split(":")
    group = await session.get(OpGroup, int(group_id))
    settings = load_settings(group)
    settings["violation_action"] = action
    save_settings(group, settings)
    await callback.answer("Действие сохранено.", show_alert=True)
    await show_group(callback, session, group.id)


@router.callback_query(F.data.startswith("op:whitelist:"))
async def op_whitelist(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    group_id = int(callback.data.split(":")[2])
    group = await session.get(OpGroup, group_id)
    settings = load_settings(group)
    items = await whitelist_users(session, group_id)
    text_items = tree_list([f"#{item.id}: {item.username or item.user_id}" for item in items]) or "Список пуст."
    await callback.message.edit_text(
        t(user.language, "op_whitelist", items=text_items),
        reply_markup=op_whitelist_keyboard(group_id, [i.id for i in items], settings["ignore_admins"]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("op:white_add:"))
async def op_white_add(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(callback, session)
    await state.set_state(SubscriptionCheck.waiting_whitelist_user)
    await state.update_data(op_group_id=int(callback.data.split(":")[2]))
    await callback.message.edit_text(t(user.language, "op_whitelist_ask"))
    await callback.answer()


@router.message(SubscriptionCheck.waiting_whitelist_user)
async def op_white_save(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    value = (message.text or "").strip()
    await add_whitelist_user(session, int(data["op_group_id"]), value.lstrip("@"), value if value.startswith("@") else None)
    await state.clear()
    await message.answer("Пользователь добавлен в исключения.")


@router.callback_query(F.data.startswith("op:white_delete:"))
async def op_white_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    _, _, group_id, item_id = callback.data.split(":")
    await delete_whitelist_user(session, int(item_id), int(group_id))
    await callback.answer("Исключение удалено.", show_alert=True)


@router.callback_query(F.data.startswith("op:white_admins:"))
async def op_white_admins(callback: CallbackQuery, session: AsyncSession) -> None:
    group = await session.get(OpGroup, int(callback.data.split(":")[2]))
    settings = load_settings(group)
    settings["ignore_admins"] = not settings["ignore_admins"]
    save_settings(group, settings)
    await callback.answer("Настройка сохранена.", show_alert=True)
    await op_whitelist(callback, session)


@router.callback_query(F.data.startswith("op:stats:"))
async def op_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    group_id = int(callback.data.split(":")[2])
    stats = await group_stats(session, group_id)
    channels = await required_channels(session, group_id)
    await callback.message.edit_text(
        t(user.language, "op_stats", **stats, channels_count=len(channels)),
        reply_markup=op_group_keyboard(group_id, True),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("op:delete:"))
async def op_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    group_id = int(callback.data.split(":")[2])
    await session.execute(delete(OpGroup).where(OpGroup.id == group_id))
    await callback.answer("Группа удалена из системы.", show_alert=True)
    await op_groups(callback, session)


@router.callback_query(F.data == "op:commands")
async def op_commands(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    settings = get_settings()
    await callback.message.edit_text(
        op_commands_text("public", settings.project_name),
        reply_markup=op_commands_keyboard(settings.project_name, "public"),
    )
    await callback.answer()


def op_commands_text(kind: str, project_name: str) -> str:
    if kind == "private":
        return (
            "📋 <b>Как узнать ID</b>\n"
            "Напишите в этом меню → выберите канал/группу → скопируйте ID.\n\n"
            "⚙️ <b>Запуск ОП</b>\n"
            "<b>Формат:</b>\n"
            "<pre>/setup &lt;ID&gt; &lt;ссылка&gt; [лимит]</pre>\n\n"
            "<b>Примеры запуска:</b>\n"
            "<pre>/setup -100199452 https://t.me/+abc123</pre>\n"
            "Без ограничения.\n\n"
            "<pre>/setup -100199452 https://t.me/+abc123 1d</pre>\n"
            "Отключится через указанный период.\n\n"
            "<pre>/setup -100199452 https://t.me/+abc123 100</pre>\n"
            "ОП отключится, когда по ссылке будет 100 активных подписчиков. Учитываются только пользователи, которые остаются подписанными.\n\n"
            "<pre>/setup -100199452 https://t.me/+abc123 +100</pre>\n"
            "ОП отключится после 100 присоединений по ссылке. Знак + считает входы, отписки не учитываются.\n\n"
            "⏱ <b>Время:</b> <code>30s</code> · <code>15m</code> · <code>2h</code> · <code>1d</code>\n\n"
            "🛑 <b>Отключение:</b>\n"
            "<code>/unset &lt;ID&gt;</code> — отключить конкретную ОП\n"
            "<code>/unset</code> — отключить все\n"
            "Или через меню Активные ОП.\n\n"
            "Помощь: @prgram_help"
        )
    if kind == "invite":
        return (
            "⚙️ <b>Запуск ОП</b> <i>отправьте команду прямо здесь</i>\n"
            "<blockquote>"
            "<code>/setup_bot &lt;ваша реферальная ссылка&gt; [лимит]</code>\n"
            "<b>Примеры:</b>\n"
            "<code>/setup_bot https://t.me/gram_piarbot?start=123456789</code> — без ограничения\n"
            "<code>/setup_bot https://t.me/gram_piarbot?start=123456789 1d</code> — отключится через 24 ч"
            "</blockquote>\n\n"
            "<b>Формат времени:</b> <code>30s</code> · <code>15m</code> · <code>2h</code> · <code>1d</code>\n\n"
            "🛑 <b>Отключение ОП</b>\n"
            "<blockquote>"
            "<code>/unset &lt;ссылка&gt;</code> — отключить конкретную ОП\n"
            "<code>/unset</code> — отключить все\n"
            "Или через меню Активные ОП"
            "</blockquote>\n\n"
            "Помощь: @prgram_help"
        )
    if kind == "ref":
        return (
            "⚙️ <b>ОП на реферальную ссылку</b>\n\n"
            "Используйте этот режим, если нужно проверять переходы по реферальной ссылке проекта.\n\n"
            "<b>Формат:</b>\n"
            "<pre>/setup_ref &lt;ссылка&gt; [лимит]</pre>\n\n"
            "<b>Примеры:</b>\n"
            "<pre>/setup_ref https://t.me/gram_piarbot?start=123456789</pre>\n"
            "Без ограничения.\n\n"
            "<pre>/setup_ref https://t.me/gram_piarbot?start=123456789 1d</pre>\n"
            "Отключится через указанный период.\n\n"
            "⏱ <b>Время:</b> <code>30s</code> · <code>15m</code> · <code>2h</code> · <code>1d</code>\n\n"
            "Помощь: @prgram_help"
        )
    if kind == "bot":
        return (
            "⚠️ Работает только с ботами, которые передали API token.\n\n"
            "⚙️ <b>Запуск ОП</b> <i>отправьте команду прямо здесь</i>\n"
            "<blockquote>"
            "<code>/setup_bot &lt;@username или ID&gt; [лимит]</code>\n"
            "<b>Примеры:</b>\n"
            "<code>/setup_bot @gram_piarbot</code> — без ограничения\n"
            "<code>/setup_bot @gram_piarbot 7d</code> — отключится через 7 дней"
            "</blockquote>\n\n"
            "<b>Формат времени:</b> <code>30s</code> · <code>15m</code> · <code>2h</code> · <code>1d</code>\n\n"
            "🛑 <b>Отключение ОП</b>\n"
            "<blockquote>"
            "<code>/unset &lt;@username&gt;</code> — отключить конкретную ОП\n"
            "<code>/unset</code> — отключить все\n"
            "Или через меню Активные ОП"
            "</blockquote>\n\n"
            "Помощь: @prgram_help"
        )
    return (
        "📋 <b>Как узнать ID канала/группы</b>\n"
        "Напишите /id в этом меню → выберите нужный канал или группу → скопируйте ID.\n\n"
        "⚙️ <b>Запуск ОП</b> <i>отправьте команду прямо здесь</i>\n"
        "<blockquote>"
        "<code>/setup &lt;ID&gt; [лимит]</code>\n"
        "<b>Примеры:</b>\n"
        "<code>/setup -1001994526641</code> — без ограничения\n"
        "<code>/setup -1001994526641 1d</code> — отключится через 24 ч"
        "</blockquote>\n\n"
        "<b>Формат времени:</b> <code>30s</code> · <code>15m</code> · <code>2h</code> · <code>1d</code>\n\n"
        "🛑 <b>Отключение ОП</b>\n"
        "<blockquote>"
        "<code>/unset &lt;ID&gt;</code> — отключить конкретную ОП\n"
        "<code>/unset</code> — отключить все\n"
        "Или через меню Активные ОП"
        "</blockquote>\n\n"
        "Помощь: @prgram_help"
    )


@router.callback_query(F.data.startswith("op:commands_info:"))
async def op_commands_info(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    kind = callback.data.rsplit(":", 1)[-1]
    if kind not in {"public", "private", "invite", "ref", "bot"}:
        kind = "public"
    settings = get_settings()
    await callback.message.edit_text(
        op_commands_text(kind, settings.project_name),
        reply_markup=op_commands_keyboard(settings.project_name, kind),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("op:bot_token_back"))
async def op_bot_token_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    source = callback.data.split(":")[-1] if callback.data else "commands"
    if source == "main":
        await show_main(callback, session)
        return
    settings = get_settings()
    await callback.message.edit_text(
        op_commands_text("bot", settings.project_name),
        reply_markup=op_commands_keyboard(settings.project_name, "bot"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("op:cmd:"))
async def op_cmd_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    command = callback.data.split(":")[2]
    groups = await owner_groups(session, user)
    for group in groups:
        settings = load_settings(group)
        settings["commands"][command] = not settings["commands"].get(command, True)
        save_settings(group, settings)
    await callback.answer("Настройка команд обновлена.", show_alert=True)
    await op_commands(callback, session)


@router.callback_query(F.data.startswith("op:add_bot"))
async def op_add_bot(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(callback, session)
    parts = callback.data.split(":")
    source = parts[2] if len(parts) > 2 and parts[2] in {"main", "commands"} else "commands"
    await state.set_state(SubscriptionCheck.waiting_bot_token)
    await state.update_data(op_bot_source=source)
    await callback.message.edit_text(
        t(user.language, "op_add_bot", project_name=get_settings().project_name),
        reply_markup=op_add_bot_keyboard(source),
    )
    await callback.answer()


@router.callback_query(F.data == "op:add_group")
async def op_add_group(callback: CallbackQuery, session: AsyncSession, bot) -> None:
    me = await bot.get_me()
    await callback.message.edit_text(
        "Добавьте нашего бота в группу администратором, затем отправьте команду /reload прямо в этой группе.\n\n"
        "После этого группа появится в разделе управления.",
        reply_markup=op_add_group_keyboard(me.username),
    )
    await callback.answer()


@router.message(SubscriptionCheck.waiting_bot_token)
async def op_bot_token_save(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(message, session)
    data = await state.get_data()
    source = data.get("op_bot_source", "commands")
    token = (message.text or "").strip()
    if ":" not in token or len(token) < 20:
        await state.clear()
        await message.answer(
            "Подключение бота отменено: это не похоже на API-token из BotFather.\n\n"
            "Чтобы попробовать снова, откройте «ОП на бота» и нажмите «Добавить бота».",
            reply_markup=subscription_check_keyboard() if source == "main" else op_commands_keyboard(get_settings().project_name, "bot"),
        )
        return

    candidate = Bot(token=token)
    try:
        bot_info = await candidate.get_me()
    except (TelegramBadRequest, TelegramUnauthorizedError):
        await state.clear()
        await message.answer(
            "Не удалось подключить бота: Telegram не принял этот API-token.\n\n"
            "Проверьте токен в BotFather и начните подключение заново.",
            reply_markup=subscription_check_keyboard() if source == "main" else op_commands_keyboard(get_settings().project_name, "bot"),
        )
        return
    finally:
        await candidate.session.close()

    await upsert_connected_bot(
        session,
        user,
        str(bot_info.id),
        bot_info.username or str(bot_info.id),
        bot_info.full_name,
        encrypt_token(token),
        token_hint(token),
    )
    await state.clear()
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await message.answer(
        f"Бот @{bot_info.username or bot_info.id} подключён к проверке подписки.\n\n"
        "Теперь его можно использовать в режиме «ОП на бота». API-token сохранён в защищённом виде.",
        reply_markup=op_commands_keyboard(get_settings().project_name, "bot"),
    )


@router.callback_query(F.data == "op:guide")
async def op_guide(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    await callback.message.edit_text(t(user.language, "op_guide"), reply_markup=subscription_check_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("op:user_check:"))
async def op_user_check(callback: CallbackQuery, session: AsyncSession, bot) -> None:
    group = await session.get(OpGroup, int(callback.data.split(":")[2]))
    ok, missing = await check_user_subscriptions(bot, session, group, callback.from_user.id)
    await log_event(session, group.id, callback.from_user.id, "check_ok" if ok else "check_failed", {"missing": missing})
    await callback.answer("Проверка пройдена." if ok else "Не выполнены условия: " + ", ".join(missing), show_alert=True)


@router.message(Command("check"), F.chat.type.in_({"group", "supergroup"}))
async def group_check_command(message: Message, session: AsyncSession, bot) -> None:
    group = await group_by_chat(session, message.chat.id)
    if not group or not command_enabled(group, "check") or not message.from_user:
        return
    ok, missing = await check_user_subscriptions(bot, session, group, message.from_user.id)
    await log_event(session, group.id, message.from_user.id, "check_ok" if ok else "check_failed", {"missing": missing})
    await message.answer("Проверка пройдена." if ok else "Не хватает подписки: " + ", ".join(missing))


@router.message(Command("status"), F.chat.type.in_({"group", "supergroup"}))
async def group_status_command(message: Message, session: AsyncSession) -> None:
    group = await group_by_chat(session, message.chat.id)
    if not group or not command_enabled(group, "status"):
        return
    channels = await required_channels(session, group.id)
    await message.answer(
        f"Проверка подписки: {'включена' if group.is_enabled else 'выключена'}\n"
        f"Обязательных каналов: {len(channels)}"
    )


@router.message(Command("op"), F.chat.type.in_({"group", "supergroup"}))
async def group_op_command(message: Message, session: AsyncSession) -> None:
    group = await group_by_chat(session, message.chat.id)
    if not group or not command_enabled(group, "op"):
        return
    channels = await required_channels(session, group.id)
    links = "\n".join(channel.channel_url for channel in channels) or "Условия пока не настроены."
    await message.answer("Обязательные условия:\n" + links, reply_markup=op_check_user_keyboard(group.id))


@router.message(Command("reload"), F.chat.type.in_({"group", "supergroup"}))
async def group_reload_command(message: Message, session: AsyncSession, bot) -> None:
    if not message.from_user:
        return
    if not await bot_is_chat_admin(bot, message.chat.id):
        await message.answer(op_bot_admin_required_text("группе"))
        return
    owner = await current_user(message, session)
    await upsert_group(session, owner, str(message.chat.id), message.chat.title or str(message.chat.id))
    await message.answer("Группа обновлена. Теперь она должна появиться в разделе управления проверкой подписки.")


@router.message(Command("id"))
async def op_id_command(message: Message, session: AsyncSession) -> None:
    if message.chat.type in {"group", "supergroup"}:
        await message.answer(f"ID этого чата: <code>{message.chat.id}</code>")
        return
    user = await current_user(message, session)
    groups = await owner_groups(session, user)
    if not groups:
        await message.answer("Подключённых групп пока нет. Добавьте бота в нужный чат администратором и отправьте /reload в группе.")
        return
    items = tree_list([f"{escape(group.title)}: <code>{escape(group.chat_id)}</code>" for group in groups])
    await message.answer("Ваши подключённые группы:\n\n" + items)


@router.message(Command("help"), F.chat.type.in_({"group", "supergroup"}))
async def group_help_command(message: Message, session: AsyncSession) -> None:
    group = await group_by_chat(session, message.chat.id)
    if not group or not command_enabled(group, "help"):
        return
    await message.answer("/check — проверить подписку\n/status — статус проверки\n/op — условия подписки\n/help — помощь")


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def group_subscription_guard(message: Message, session: AsyncSession, bot) -> None:
    if not message.from_user or message.from_user.is_bot:
        return
    result = await session.execute(select(OpGroup).where(OpGroup.chat_id == str(message.chat.id), OpGroup.is_enabled == True))
    group = result.scalar_one_or_none()
    if not group:
        return
    settings = load_settings(group)
    if await is_whitelisted(session, group.id, message.from_user.id, message.from_user.username):
        return
    if settings["ignore_admins"]:
        try:
            member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}:
                return
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
    ok, missing = await check_user_subscriptions(bot, session, group, message.from_user.id)
    if ok:
        await log_event(session, group.id, message.from_user.id, "check_ok")
        return

    channels = await required_channels(session, group.id)
    links = "\n".join(f"- {channel.channel_url}" for channel in channels)
    warning = settings["warning_text"].format(
        user_name=message.from_user.full_name,
        group_title=group.title,
        required_links=links,
        BOT_NAME=get_settings().project_name,
    )
    await message.answer(warning + "\n\n" + links, reply_markup=op_check_user_keyboard(group.id))
    await log_event(session, group.id, message.from_user.id, "check_failed", {"missing": missing})

    action = settings["violation_action"]
    if action == "delete":
        try:
            await message.delete()
            await log_event(session, group.id, message.from_user.id, "message_deleted")
        except TelegramBadRequest:
            pass
    elif action in {"mute", "kick"}:
        await message.answer("Для ограничений нужны права администратора. Настройка сохранена, но действие не применено.")
