import json

from aiogram.types import ChatAdministratorRights, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, KeyboardButtonRequestChat, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.custom_emojis import button_emoji, button_emoji_id
from app.models.enums import TaskType
from app.models.task import Task
from app.utils.formatting import money


def keyboard_task_meta(task: Task) -> dict:
    if not task.filters_json:
        return {}
    try:
        payload = json.loads(task.filters_json)
    except (TypeError, ValueError):
        return {}
    return payload.get("meta") or {}


def ikb(
    text: str,
    callback_data: str | None = None,
    url: str | None = None,
    emoji_name: str | None = None,
    style: str | None = None,
) -> InlineKeyboardButton:
    kwargs = {"text": text}
    if emoji_name and not button_emoji_id(emoji_name):
        fallback = button_emoji(emoji_name)
        if fallback:
            kwargs["text"] = f"{fallback} {text}"
    if callback_data:
        kwargs["callback_data"] = callback_data
    if url:
        kwargs["url"] = url
    if emoji_name:
        emoji_id = button_emoji_id(emoji_name)
        if emoji_id:
            kwargs["icon_custom_emoji_id"] = emoji_id
    if style:
        kwargs["style"] = style
    try:
        return InlineKeyboardButton(**kwargs)
    except TypeError:
        fallback = f"{button_emoji(emoji_name)} " if emoji_name else ""
        kwargs.pop("icon_custom_emoji_id", None)
        kwargs.pop("style", None)
        kwargs["text"] = f"{fallback}{text}"
        return InlineKeyboardButton(**kwargs)


def rkb(text: str, emoji_name: str | None = None, style: str | None = None) -> KeyboardButton:
    kwargs = {"text": text}
    if emoji_name and not button_emoji_id(emoji_name):
        fallback = button_emoji(emoji_name)
        if fallback:
            kwargs["text"] = f"{fallback} {text}"
    if emoji_name:
        emoji_id = button_emoji_id(emoji_name)
        if emoji_id:
            kwargs["icon_custom_emoji_id"] = emoji_id
    if style:
        kwargs["style"] = style
    try:
        return KeyboardButton(**kwargs)
    except TypeError:
        fallback = f"{button_emoji(emoji_name)} " if emoji_name else ""
        kwargs.pop("icon_custom_emoji_id", None)
        kwargs.pop("style", None)
        kwargs["text"] = f"{fallback}{text}"
        return KeyboardButton(**kwargs)


REQUEST_CHANNEL_ID = 7101
REQUEST_GROUP_ID = 7102
REQUEST_BOOST_ADMIN_CHANNEL_ID = 7201
REQUEST_BOOST_ADMIN_GROUP_ID = 7202


def chat_admin_rights() -> ChatAdministratorRights:
    return ChatAdministratorRights(
        is_anonymous=False,
        can_manage_chat=True,
        can_delete_messages=False,
        can_manage_video_chats=False,
        can_restrict_members=False,
        can_promote_members=False,
        can_change_info=False,
        can_invite_users=True,
        can_post_stories=False,
        can_edit_stories=False,
        can_delete_stories=False,
        can_post_messages=False,
        can_edit_messages=False,
        can_pin_messages=False,
        can_manage_topics=False,
    )


def request_chat_button(text: str, request_id: int, chat_is_channel: bool) -> KeyboardButton:
    return KeyboardButton(
        text=text,
        request_chat=KeyboardButtonRequestChat(
            request_id=request_id,
            chat_is_channel=chat_is_channel,
            chat_has_username=True,
            user_administrator_rights=chat_admin_rights(),
            request_title=True,
            request_username=True,
            request_photo=False,
        ),
    )


def request_bot_admin_chat_button(text: str, request_id: int, chat_is_channel: bool) -> KeyboardButton:
    return KeyboardButton(
        text=text,
        request_chat=KeyboardButtonRequestChat(
            request_id=request_id,
            chat_is_channel=chat_is_channel,
            user_administrator_rights=chat_admin_rights(),
            bot_administrator_rights=chat_admin_rights(),
            bot_is_member=False,
            request_title=True,
            request_username=True,
            request_photo=False,
        ),
    )


def request_channel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [request_bot_admin_chat_button("Канал", REQUEST_CHANNEL_ID, True)],
            [rkb("Назад", "back")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def request_group_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [request_bot_admin_chat_button("Группа", REQUEST_GROUP_ID, False)],
            [rkb("Назад", "back")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def request_boost_target_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [request_chat_button("Канал", REQUEST_CHANNEL_ID, True)],
            [request_chat_button("Группа", REQUEST_GROUP_ID, False)],
            [rkb("Назад", "back")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def request_boost_admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [request_bot_admin_chat_button("Добавить бота в канал", REQUEST_BOOST_ADMIN_CHANNEL_ID, True)],
            [request_bot_admin_chat_button("Добавить бота в группу", REQUEST_BOOST_ADMIN_GROUP_ID, False)],
            [rkb("Скрыть клавиатуру", "back")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def boost_admin_inline_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(
        builder,
        "Добавить бота в канал",
        url=f"https://t.me/{bot_username}?startchannel&admin=invite_users",
        emoji_name="channel",
        style="primary",
    )
    add_button(
        builder,
        "Добавить бота в группу",
        url=f"https://t.me/{bot_username}?startgroup=true&admin=invite_users",
        emoji_name="referrals",
        style="primary",
    )
    builder.adjust(1)
    return builder.as_markup()


def add_button(
    builder: InlineKeyboardBuilder,
    text: str,
    callback_data: str | None = None,
    url: str | None = None,
    emoji_name: str | None = None,
    style: str | None = None,
) -> None:
    builder.add(ikb(text, callback_data=callback_data, url=url, emoji_name=emoji_name, style=style))


def telegram_url(value: str) -> str:
    link = (value or "").strip()
    if link.startswith("@"):
        return f"https://t.me/{link[1:]}"
    if link.startswith("t.me/"):
        return f"https://{link}"
    if link.startswith(("https://", "http://")):
        return link
    return link


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [rkb("Заработать", "earn"), rkb("Рекламировать", "ads")],
        [rkb("Чеки", "checks"), rkb("Профиль", "profile")],
        [rkb("Проверка подписки", "subscription_check")],
        [rkb("Полезные ссылки", "links"), rkb("Инструкция", "instruction")],
        [rkb("Язык", "language")],
    ]
    if is_admin:
        rows.append([rkb("Админка", "admin")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[ikb("Назад в меню", callback_data="menu:home", emoji_name="back")]])


def useful_links_keyboard(
    support_url: str | None = None,
    chat_url: str | None = None,
    news_url: str | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Инструкция по использованию", callback_data="links:guide", emoji_name="instruction")
    add_button(builder, "Правила сервиса", callback_data="links:rules", emoji_name="warning")
    add_button(builder, "Политика конфиденциальности", callback_data="links:policy", emoji_name="privacy")
    if support_url:
        add_button(builder, "Поддержка и сотрудничество", url=support_url, emoji_name="support")
    if chat_url:
        add_button(builder, "Чат", url=chat_url, emoji_name="group")
    if news_url:
        add_button(builder, "PR GRAM | NEWS", url=news_url, emoji_name="channel")
    add_button(builder, "Назад в меню", callback_data="menu:home", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def useful_links_back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "К полезным ссылкам", callback_data="links:main", emoji_name="links")
    add_button(builder, "Назад в меню", callback_data="menu:home", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def profile_keyboard(notifications_enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Пополнить баланс", callback_data="profile:topup", emoji_name="payment", style="primary")
    add_button(builder, "Рефералы", callback_data="profile:refs", emoji_name="referrals")
    add_button(builder, "Уровни", callback_data="profile:levels", emoji_name="levels")
    add_button(builder, "Мои задания", callback_data="ad:mine:profile", emoji_name="my_tasks")
    add_button(builder, "Язык", callback_data="profile:language", emoji_name="language")
    add_button(builder, "Отключить уведомления" if notifications_enabled else "Включить уведомления", callback_data="profile:toggle_notifications", emoji_name="notifications_off" if notifications_enabled else "notifications_on")
    add_button(builder, "Назад", callback_data="menu:home", emoji_name="back")
    builder.adjust(1, 2, 2, 1, 1)
    return builder.as_markup()


def profile_back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "В профиль", callback_data="profile:main", emoji_name="profile")
    add_button(builder, "В главное меню", callback_data="menu:home", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


TOPUP_TARIFFS = [
    (90_000, 50),
    (180_000, 100),
    (450_000, 250),
    (1_350_000, 750),
    (2_700_000, 1499),
    (4_500_000, 2499),
]


def topup_keyboard(currency_name: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for amount, stars in TOPUP_TARIFFS:
        amount_text = f"{amount:,}".replace(",", " ")
        add_button(builder, f"{amount_text} {currency_name} = {stars}", callback_data=f"profile:topup_pick:{amount}:{stars}", emoji_name="payment")
    add_button(builder, "Другая сумма", callback_data="profile:topup_custom", emoji_name="stars")
    add_button(builder, "Назад", callback_data="profile:main", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def topup_confirm_keyboard(amount: int, stars: int, test_mode: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if test_mode:
        add_button(builder, "Симулировать успешную оплату", callback_data=f"profile:topup_mock:{amount}:{stars}:paid", emoji_name="success", style="success")
        add_button(builder, "Симулировать ошибку оплаты", callback_data=f"profile:topup_mock:{amount}:{stars}:failed", emoji_name="error", style="danger")
        add_button(builder, "Симулировать ожидание", callback_data=f"profile:topup_mock:{amount}:{stars}:pending", emoji_name="warning")
    add_button(builder, "Подтвердить", callback_data=f"profile:topup_confirm:{amount}:{stars}", emoji_name="confirm", style="success")
    add_button(builder, "Отмена", callback_data="profile:topup", emoji_name="cancel", style="danger")
    builder.adjust(1 if test_mode else 2)
    return builder.as_markup()


def referrals_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Скопировать ссылку / Поделиться", callback_data="profile:ref_copy", emoji_name="copy")
    add_button(builder, "Статистика", callback_data="profile:refs_stats", emoji_name="statistics")
    add_button(builder, "Назад", callback_data="profile:main", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def levels_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Как получить XP", callback_data="profile:xp_help", emoji_name="levels")
    add_button(builder, "Назад", callback_data="profile:main", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def subscription_check_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Управлять группами", callback_data="op:groups", emoji_name="referrals", style="primary")
    add_button(builder, "Команды", callback_data="op:commands", emoji_name="commands")
    add_button(builder, "Добавить бота", callback_data="op:add_bot:main", emoji_name="success")
    add_button(builder, "Инструкция", callback_data="op:guide", emoji_name="instruction")
    add_button(builder, "Назад", callback_data="menu:home", emoji_name="back")
    builder.adjust(1, 2, 1, 1)
    return builder.as_markup()


def op_empty_groups_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Добавить группу", callback_data="op:add_group", emoji_name="success")
    add_button(builder, "Назад", callback_data="op:main", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def op_groups_keyboard(group_ids: list[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for group_id in group_ids:
        add_button(builder, f"Настроить #{group_id}", callback_data=f"op:group:{group_id}", emoji_name="settings")
    add_button(builder, "Обновить список", callback_data="op:groups", emoji_name="refresh")
    add_button(builder, "Назад", callback_data="op:main", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def op_group_keyboard(group_id: int, enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Выключить проверку" if enabled else "Включить проверку", callback_data=f"op:toggle:{group_id}", emoji_name="error" if enabled else "success", style="danger" if enabled else "success")
    add_button(builder, "Обязательные каналы", callback_data=f"op:channels:{group_id}", emoji_name="channel")
    add_button(builder, "Текст предупреждения", callback_data=f"op:warning:{group_id}", emoji_name="warning")
    add_button(builder, "Действие при нарушении", callback_data=f"op:actions:{group_id}", emoji_name="shield")
    add_button(builder, "Исключения / Whitelist", callback_data=f"op:whitelist:{group_id}", emoji_name="referrals")
    add_button(builder, "Статистика", callback_data=f"op:stats:{group_id}", emoji_name="statistics")
    add_button(builder, "Удалить группу из системы", callback_data=f"op:delete:{group_id}", emoji_name="delete", style="danger")
    add_button(builder, "Назад", callback_data="op:groups", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def op_channels_keyboard(group_id: int, channel_ids: list[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Добавить канал", callback_data=f"op:channel_add:{group_id}", emoji_name="channel")
    for channel_id in channel_ids:
        add_button(builder, f"Удалить #{channel_id}", callback_data=f"op:channel_delete:{group_id}:{channel_id}", emoji_name="delete", style="danger")
    add_button(builder, "Проверить доступ бота", callback_data=f"op:channel_check:{group_id}", emoji_name="refresh")
    add_button(builder, "Назад", callback_data=f"op:group:{group_id}", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def op_warning_keyboard(group_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Изменить текст", callback_data=f"op:warning_edit:{group_id}", emoji_name="edit")
    add_button(builder, "Сбросить на стандартный", callback_data=f"op:warning_reset:{group_id}", emoji_name="refresh")
    add_button(builder, "Назад", callback_data=f"op:group:{group_id}", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def op_actions_keyboard(group_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Только предупреждение", callback_data=f"op:action:{group_id}:warn", emoji_name="warning")
    add_button(builder, "Удалять сообщения", callback_data=f"op:action:{group_id}:delete", emoji_name="delete", style="danger")
    add_button(builder, "Временно ограничивать", callback_data=f"op:action:{group_id}:mute", emoji_name="warning")
    add_button(builder, "Исключать из группы", callback_data=f"op:action:{group_id}:kick", emoji_name="shield", style="danger")
    add_button(builder, "Назад", callback_data=f"op:group:{group_id}", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def op_whitelist_keyboard(group_id: int, item_ids: list[int], ignore_admins: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Добавить пользователя", callback_data=f"op:white_add:{group_id}", emoji_name="success")
    for item_id in item_ids:
        add_button(builder, f"Удалить #{item_id}", callback_data=f"op:white_delete:{group_id}:{item_id}", emoji_name="delete", style="danger")
    add_button(builder, f"Не проверять админов: {'включено' if ignore_admins else 'выключено'}", callback_data=f"op:white_admins:{group_id}", emoji_name="settings")
    add_button(builder, "Назад", callback_data=f"op:group:{group_id}", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def op_commands_keyboard(project_name: str, selected: str = "public") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    variants = [
        ("public", "Публичные каналы/чаты", "success"),
        ("private", "Приватные каналы/чаты", "shield"),
        ("invite", "ОП на пригласительную ссылку", "links"),
        ("ref", f"Реферальная ссылка {project_name}", "profile"),
        ("bot", "ОП на бота", "bot"),
    ]
    for key, label, emoji_name in variants:
        prefix = "✓ " if key == selected else ""
        add_button(builder, f"{prefix}{label}", callback_data=f"op:commands_info:{key}", emoji_name=emoji_name)
    add_button(builder, "Назад", callback_data="op:main", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def op_add_bot_keyboard(source: str = "commands") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Назад", callback_data=f"op:bot_token_back:{source}", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def op_add_group_keyboard(bot_username: str | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if bot_username:
        add_button(builder, "Добавить в группу", url=f"https://t.me/{bot_username}?startgroup=true", emoji_name="success", style="primary")
    add_button(builder, "Назад", callback_data="op:groups", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def op_check_user_keyboard(group_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Проверить подписку", callback_data=f"op:user_check:{group_id}", emoji_name="success", style="success")
    builder.adjust(1)
    return builder.as_markup()


def earn_keyboard(is_premium: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Каналы", callback_data=f"tasks:{TaskType.CHANNEL.value}:1", emoji_name="channel")
    add_button(builder, "Группы", callback_data=f"tasks:{TaskType.GROUP.value}:1", emoji_name="referrals")
    add_button(builder, "Посты", callback_data=f"tasks:{TaskType.POST.value}:1", emoji_name="post")
    add_button(builder, "Боты", callback_data=f"tasks:{TaskType.BOT.value}:1", emoji_name="bot")
    add_button(builder, "Реакции", callback_data="tasks:reaction_categories", emoji_name="reactions")
    if is_premium:
        add_button(builder, "Premium Boost", callback_data="tasks:boost_terms", emoji_name="boost")
    else:
        add_button(builder, "🔒 Premium Boost", callback_data="premium_locked", emoji_name="boost")
    builder.adjust(2)
    return builder.as_markup()


def reaction_categories_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Любые реакции", callback_data="tasks:reaction:any:1", emoji_name="reactions")
    add_button(builder, "Установленные реакции", callback_data="tasks:reaction:selected:1", emoji_name="stars")
    add_button(builder, "Назад", callback_data="earn", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def boost_terms_keyboard(currency_name: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, f"7 дней | 21 000 {currency_name}", callback_data="tasks:boost:7:1", emoji_name="boost")
    add_button(builder, f"30 дней | 90 000 {currency_name}", callback_data="tasks:boost:30:1", emoji_name="boost")
    add_button(builder, "Назад", callback_data="earn", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def empty_tasks_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "К категориям", callback_data="earn", emoji_name="earn")
    add_button(builder, "В главное меню", callback_data="menu:home", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def task_list_keyboard(
    tasks: list[Task],
    task_type: str,
    page: int,
    pages: int,
    currency_name: str,
    reaction_mode: str | None = None,
    boost_days: int | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    action_labels = {
        TaskType.BOT.value: "Перейти в бота",
        TaskType.CHANNEL.value: "Перейти в канал",
        TaskType.GROUP.value: "Перейти в группу",
        TaskType.POST.value: "Открыть пост",
        TaskType.REACTION.value: "Открыть пост",
        TaskType.BOOST.value: "Открыть задание",
        TaskType.VIEW.value: "Открыть пост",
    }
    action_labels[TaskType.BOOST.value] = "Зарядить"
    if task_type == TaskType.REACTION.value and reaction_mode:
        list_callback_prefix = f"tasks:reaction:{reaction_mode}"
    elif task_type == TaskType.BOOST.value and boost_days:
        list_callback_prefix = f"tasks:boost:{boost_days}"
    else:
        list_callback_prefix = f"tasks:{task_type}"
    for task in tasks:
        action = "Поставить реакцию" if task.type == TaskType.REACTION.value else action_labels.get(task.type, "Открыть задание")
        if task.type == TaskType.BOOST.value:
            days = keyboard_task_meta(task).get("boost_days", 7)
            button_text = f"+{money(task.reward)} {currency_name} | {days} дней"
        else:
            button_text = f"{action} | +{money(task.reward)} {currency_name}"
        add_button(
            builder,
            button_text,
            callback_data=f"task_view:{task.id}:{task_type}:{page}:{reaction_mode or boost_days or '-'}",
            emoji_name="bot" if task.type == TaskType.BOT.value else "links",
            style="primary",
        )
    if pages > 1:
        first_page = 1
        prev_page = max(1, page - 1)
        next_page = min(pages, page + 1)
        add_button(builder, str(first_page), callback_data=f"{list_callback_prefix}:{first_page}")
        add_button(builder, "<", callback_data=f"{list_callback_prefix}:{prev_page}")
        add_button(builder, str(page), callback_data="tasks:noop")
        add_button(builder, ">", callback_data=f"{list_callback_prefix}:{next_page}")
        add_button(builder, str(pages), callback_data=f"{list_callback_prefix}:{pages}")
    if task_type == TaskType.REACTION.value:
        back_callback = "tasks:reaction_categories"
    elif task_type == TaskType.BOOST.value:
        back_callback = "tasks:boost_terms"
    else:
        back_callback = "earn"
    add_button(builder, "Назад", callback_data=back_callback, emoji_name="back")
    builder.adjust(*([1] * len(tasks)), 5 if pages > 1 else 1, 1)
    return builder.as_markup()


def task_keyboard(
    task_id: int,
    task_type: str,
    url: str,
    page: int,
    pages: int,
    reaction_mode: str | None = None,
    boost_days: int | None = None,
    reaction_emoji: str | None = None,
    reaction_has_image: bool = False,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if task_type == TaskType.REACTION.value and reaction_mode == "selected" and reaction_emoji:
        action = f"{reaction_emoji} ← Нужна реакция"
    elif task_type == TaskType.REACTION.value and reaction_mode == "selected" and reaction_has_image:
        action = "Нужная реакция на скрине"
    elif task_type == TaskType.REACTION.value:
        action = "Перейти к посту"
    elif task_type == TaskType.BOOST.value:
        action = "Зарядить"
    else:
        action = "Открыть задание" if task_type in {TaskType.CHANNEL.value, TaskType.GROUP.value} else "Перейти и сделать proof"
    add_button(builder, action, url=telegram_url(url), emoji_name="links", style="primary")
    add_button(builder, "Проверить", callback_data=f"task_check:{task_id}", emoji_name="confirm")
    add_button(builder, "Пожаловаться", callback_data=f"complain:{task_id}", emoji_name="complaint")
    if task_type == TaskType.REACTION.value and reaction_mode:
        list_callback = f"tasks:reaction:{reaction_mode}:{page}"
    elif task_type == TaskType.BOOST.value and boost_days:
        list_callback = f"tasks:boost:{boost_days}:{page}"
    else:
        list_callback = f"tasks:{task_type}:{page}"
    add_button(builder, "К списку", callback_data=list_callback, emoji_name="back")
    add_button(builder, "К категориям", callback_data="earn", emoji_name="earn")
    builder.adjust(1, 2, 1, 1)
    return builder.as_markup()


def proof_submitted_keyboard(completion_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Открыть спор", callback_data=f"proof_dispute:{completion_id}", emoji_name="complaint", style="danger")
    add_button(builder, "К заданиям", callback_data="earn", emoji_name="earn")
    builder.adjust(1)
    return builder.as_markup()


def advertise_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Канал", callback_data=f"ad:start:{TaskType.CHANNEL.value}", emoji_name="channel")
    add_button(builder, "Группа", callback_data=f"ad:start:{TaskType.GROUP.value}", emoji_name="referrals")
    add_button(builder, "Пост", callback_data="ad:start:post", emoji_name="post")
    add_button(builder, "Бот", callback_data=f"ad:start:{TaskType.BOT.value}", emoji_name="bot")
    add_button(builder, "Реакции", callback_data=f"ad:start:{TaskType.REACTION.value}", emoji_name="reactions")
    add_button(builder, "Premium Boost", callback_data=f"ad:start:{TaskType.BOOST.value}", emoji_name="boost")
    add_button(builder, "Авто-задания", callback_data="ad:auto", emoji_name="auto_tasks")
    add_button(builder, "Мои задания", callback_data="ad:mine", emoji_name="my_tasks")
    add_button(builder, "Назад", callback_data="menu:home", emoji_name="back")
    builder.adjust(2, 2, 2, 1, 1, 1)
    return builder.as_markup()


def audience_keyboard(task_type: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Все пользователи", callback_data=f"ad:audience:{task_type}:all", emoji_name="referrals")
    add_button(builder, "Только Premium", callback_data=f"ad:audience:{task_type}:premium", emoji_name="premium")
    add_button(builder, "Настроить вручную", callback_data=f"ad:audience:{task_type}:custom", emoji_name="settings")
    add_button(builder, "Назад", callback_data="ad:back", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def post_format_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Просмотры", callback_data=f"ad:format:{TaskType.VIEW.value}", emoji_name="search")
    add_button(builder, "Реакции", callback_data=f"ad:format:{TaskType.REACTION.value}", emoji_name="reactions")
    add_button(builder, "Назад", callback_data="ad:back", emoji_name="back")
    builder.adjust(2, 1)
    return builder.as_markup()


def bot_format_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Только запуск", callback_data="ad:bot_format:simple", emoji_name="bot")
    add_button(builder, "Запуск + условия", callback_data="ad:bot_format:conditions", emoji_name="settings")
    add_button(builder, "Назад", callback_data="ad:back", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def bot_audience_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Доступно для всех пользователей", callback_data="ad:bot_audience:all", emoji_name="referrals")
    add_button(builder, "Только для пользователей с Telegram Premium", callback_data="ad:bot_audience:premium", emoji_name="premium")
    add_button(builder, "Назад", callback_data="ad:start:bot", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def reaction_audience_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Разрешить всем", callback_data="ad:reaction_audience:all", emoji_name="globe")
    add_button(builder, "Выбрать аудиторию", callback_data="ad:reaction_audience:choose", emoji_name="target")
    add_button(builder, "Назад", callback_data="ad:back", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def view_audience_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Разрешить всем", callback_data="ad:view_audience:all", emoji_name="globe")
    add_button(builder, "Выбрать аудиторию", callback_data="ad:view_audience:choose", emoji_name="target")
    add_button(builder, "Назад", callback_data="ad:start:post", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def reaction_mode_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Любые реакции", callback_data="ad:reaction_mode:any", emoji_name="reactions")
    add_button(builder, "Установленные реакции", callback_data="ad:reaction_mode:selected", emoji_name="stars")
    add_button(builder, "Назад", callback_data="ad:back", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


REACTION_LANGUAGE_OPTIONS = [
    ("uk", "🇺🇦 Українська"),
    ("ru", "🇷🇺 Русский"),
    ("en", "🇬🇧 English"),
    ("de", "🇩🇪 Deutsch"),
    ("zh", "🇨🇳 中文"),
    ("ar", "🇸🇦 العربية"),
    ("fa", "🇮🇷 فارسی"),
    ("es", "🇪🇸 Español"),
    ("id", "🇮🇩 Bahasa Indonesia"),
    ("pt", "🇧🇷 Português"),
    ("hi", "🇮🇳 हिन्दी"),
    ("bn", "🇧🇩 বাংলা"),
    ("uz", "🇺🇿 O'zbekcha"),
    ("tr", "🇹🇷 Türkçe"),
    ("kk", "🇰🇿 Қазақша"),
    ("fr", "🇫🇷 Français"),
]


def reaction_languages_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    selected_set = set(selected)
    for code, label in REACTION_LANGUAGE_OPTIONS:
        prefix = "✅ " if code in selected_set else ""
        builder.button(text=f"{prefix}{label}", callback_data=f"ad:reaction_lang:{code}")
    add_button(builder, "Сохранить и продолжить", callback_data="ad:reaction_lang_save", emoji_name="confirm")
    add_button(builder, "Назад", callback_data="ad:reaction_audience_menu", emoji_name="back")
    builder.adjust(3, 3, 3, 3, 3, 1, 1)
    return builder.as_markup()


def reaction_amount_keyboard(max_amount: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if max_amount > 0:
        builder.button(text=f"{max_amount} (максимум по балансу)", callback_data=f"ad:reaction_amount:{max_amount}")
    add_button(builder, "Назад", callback_data="ad:reaction_price_back", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def view_amount_keyboard(max_amount: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for amount in (10, 20, 50, 100):
        builder.button(text=str(amount), callback_data=f"ad:view_amount:{amount}")
    if max_amount > 0:
        builder.button(text=f"{max_amount} (Максимум для вашего баланса)", callback_data=f"ad:view_amount:{max_amount}")
    add_button(builder, "Назад", callback_data="ad:view_price_back", emoji_name="back")
    builder.adjust(4, 1, 1)
    return builder.as_markup()


def reaction_payment_keyboard(balance_total: str, stars_amount: int, currency_name: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💎 {balance_total} {currency_name}", callback_data="ad:reaction_pay:balance")
    builder.button(text=f"🌟 {stars_amount} Telegram Stars (-15%)", callback_data="ad:reaction_pay:stars")
    add_button(builder, "Назад", callback_data="ad:reaction_amount_back", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def ad_payment_keyboard(balance_total: str, stars_amount: int, currency_name: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💎 {balance_total} {currency_name}", callback_data="ad:pay:balance")
    builder.button(text=f"🌟 {stars_amount} Telegram Stars (-15%)", callback_data="ad:pay:stars")
    add_button(builder, "Назад", callback_data="ad:back", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def boost_term_keyboard(currency_name: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, f"7 дней | 21 000 {currency_name}", callback_data="ad:boost_term:7", emoji_name="boost")
    add_button(builder, f"30 дней | 90 000 {currency_name}", callback_data="ad:boost_term:30", emoji_name="boost")
    add_button(builder, "Назад", callback_data="ad:back", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def confirm_task_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Запустить", callback_data="ad:confirm", emoji_name="confirm", style="success")
    add_button(builder, "Отмена", callback_data="ad:back", emoji_name="cancel", style="danger")
    builder.adjust(2)
    return builder.as_markup()


def auto_tasks_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Добавить канал", callback_data="ad:auto_add", emoji_name="channel")
    add_button(builder, "Назад", callback_data="ad:back", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def my_tasks_keyboard(
    task_ids: list[int] | None = None,
    source: str = "ads",
    tab: str = "active",
    page: int = 1,
    pages: int = 1,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    back_target = "profile:main" if source == "profile" else "ad:back"
    for task_id in task_ids or []:
        add_button(builder, f"Открыть #{task_id}", callback_data=f"ad:task:{task_id}:{source}", emoji_name="search")
    add_button(builder, "Активные", callback_data=f"ad:mine:{source}:active:1", emoji_name="play")
    add_button(builder, "Все", callback_data=f"ad:mine:{source}:all:1", emoji_name="tasks")
    add_button(builder, "Архив", callback_data=f"ad:mine:{source}:archive:1", emoji_name="archive")
    add_button(builder, "Остановленные", callback_data=f"ad:mine:{source}:paused:1", emoji_name="pause")
    if pages > 1:
        prev_page = max(1, page - 1)
        next_page = min(pages, page + 1)
        add_button(builder, "<", callback_data=f"ad:mine:{source}:{tab}:{prev_page}")
        add_button(builder, f"{page}/{pages}", callback_data="tasks:noop")
        add_button(builder, ">", callback_data=f"ad:mine:{source}:{tab}:{next_page}")
    add_button(builder, "Заявки — реакции", callback_data=f"ad:mine_review:{TaskType.REACTION.value}:{source}", emoji_name="reactions")
    add_button(builder, "Заявки — боты", callback_data=f"ad:mine_review:{TaskType.BOT.value}:{source}", emoji_name="bot")
    add_button(builder, "Создать новое задание", callback_data="ad:back", emoji_name="ads")
    add_button(builder, "Удалить все мои задания", callback_data=f"ad:delete_all_confirm:{source}", emoji_name="delete", style="danger")
    add_button(builder, "Назад", callback_data=back_target, emoji_name="back")
    builder.adjust(*([1] * len(task_ids or [])), 4, *([3] if pages > 1 else []), 1, 1, 1, 1, 1)
    return builder.as_markup()


def archived_tasks_keyboard(task_ids: list[int], source: str = "ads") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for task_id in task_ids:
        add_button(builder, f"Открыть #{task_id}", callback_data=f"ad:task:{task_id}:{source}", emoji_name="search")
    add_button(builder, "Назад", callback_data=f"ad:mine:{source}", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def delete_all_tasks_confirm_keyboard(source: str = "ads") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Удалить все", callback_data=f"ad:delete_all:{source}", emoji_name="delete", style="danger")
    add_button(builder, "Отмена", callback_data=f"ad:mine:{source}", emoji_name="cancel")
    builder.adjust(2)
    return builder.as_markup()


def owner_proofs_keyboard(proof_ids: list[int], task_type: str, source: str = "ads") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for proof_id in proof_ids:
        add_button(builder, f"Открыть заявку #{proof_id}", callback_data=f"ad:proof:{proof_id}:{task_type}:{source}", emoji_name="proof")
    add_button(builder, "Назад", callback_data=f"ad:mine:{source}", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def owner_proof_card_keyboard(proof_id: int, task_type: str, source: str = "ads") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Принять", callback_data=f"ad:proof_approve:{proof_id}:{source}", emoji_name="confirm", style="success")
    add_button(builder, "Отклонить", callback_data=f"ad:proof_reject:{proof_id}:{source}", emoji_name="error", style="danger")
    add_button(builder, "К заявкам", callback_data=f"ad:mine_review:{task_type}:{source}", emoji_name="back")
    builder.adjust(2, 1)
    return builder.as_markup()


def my_task_detail_keyboard(task_id: int, status: str, source: str = "ads") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    back_target = "profile:main" if source == "profile" else "ad:back"
    if status in {"active", "moderation", "paused", "rejected"}:
        add_button(builder, "Архивировать", callback_data=f"ad:task_archive:{task_id}:{source}", emoji_name="delete", style="danger")
    add_button(builder, "Удалить", callback_data=f"ad:task_delete:{task_id}:{source}", emoji_name="delete", style="danger")
    add_button(builder, "К моим заданиям", callback_data=f"ad:mine:{source}", emoji_name="my_tasks")
    add_button(builder, "Назад", callback_data=back_target, emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def checks_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_button(builder, "Создать чек", callback_data="check:create", emoji_name="checks")
    add_button(builder, "Активировать чек", callback_data="check:activate", emoji_name="confirm")
    builder.adjust(1)
    return builder.as_markup()


def languages_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [ikb("🇺🇦 Українська", callback_data="lang:uk"), ikb("🇷🇺 Русский", callback_data="lang:ru")],
            [ikb("🇬🇧 English", callback_data="lang:en"), ikb("🇩🇪 Deutsch", callback_data="lang:de")],
            [ikb("🇨🇳 中文", callback_data="lang:zh"), ikb("🇸🇦 العربية", callback_data="lang:ar")],
            [ikb("🇮🇷 فارسی", callback_data="lang:fa"), ikb("🇪🇸 Español", callback_data="lang:es")],
            [ikb("🇮🇩 Bahasa Indonesia", callback_data="lang:id"), ikb("🇧🇷 Português", callback_data="lang:pt")],
            [ikb("🇮🇳 हिन्दी", callback_data="lang:hi"), ikb("🇧🇩 বাংলা", callback_data="lang:bn")],
            [ikb("🇺🇿 O‘zbekcha", callback_data="lang:uz"), ikb("🇹🇷 Türkçe", callback_data="lang:tr")],
            [ikb("🇰🇿 Қазақша", callback_data="lang:kk"), ikb("🇫🇷 Français", callback_data="lang:fr")],
            [ikb("Назад", callback_data="profile:main", emoji_name="back")],
        ]
    )
