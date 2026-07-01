import json
from math import ceil
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.common import (
    advertise_keyboard,
    archived_tasks_keyboard,
    audience_keyboard,
    auto_tasks_keyboard,
    ad_payment_keyboard,
    bot_audience_keyboard,
    boost_term_keyboard,
    boost_admin_inline_keyboard,
    boost_terms_keyboard,
    bot_format_keyboard,
    confirm_task_keyboard,
    delete_all_tasks_confirm_keyboard,
    empty_tasks_keyboard,
    my_tasks_keyboard,
    my_task_detail_keyboard,
    owner_proof_card_keyboard,
    owner_proofs_keyboard,
    proof_submitted_keyboard,
    post_format_keyboard,
    reaction_amount_keyboard,
    reaction_audience_keyboard,
    reaction_categories_keyboard,
    reaction_languages_keyboard,
    reaction_mode_keyboard,
    reaction_payment_keyboard,
    REQUEST_CHANNEL_ID,
    REQUEST_GROUP_ID,
    REQUEST_BOOST_ADMIN_CHANNEL_ID,
    REQUEST_BOOST_ADMIN_GROUP_ID,
    request_boost_admin_keyboard,
    request_boost_target_keyboard,
    request_channel_keyboard,
    request_group_keyboard,
    task_keyboard,
    task_list_keyboard,
    view_amount_keyboard,
    view_audience_keyboard,
)
from app.models.enums import MANUAL_PROOF_TYPES, CompletionStatus, TaskStatus, TaskType
from app.models.social import Complaint
from app.models.task import Task, TaskCompletion
from app.models.user import User
from app.repositories.tasks import (
    active_count_by_type,
    create_pending_proof,
    create_task,
    creator_pending_completions,
    get_completion,
    list_active,
    list_created_by_user,
    pending_completions_for_task,
    task_meta,
)
from app.repositories.users import add_balance, charge_balance
from app.services.payments import complete_stars_payment, create_stars_topup, send_stars_invoice
from app.services.tasks import verify_subscription_task
from app.states import CreateTask, ManualProof
from app.texts import t
from app.utils.formatting import money, status_label, tree_list
from app.utils.test_mode import is_test_mode, test_mode_line
from app.utils.users import current_user

router = Router()
TASKS_PER_PAGE = 10
MY_TASKS_PER_PAGE = 8

TASK_LABELS = {
    TaskType.CHANNEL.value: "Канал",
    TaskType.GROUP.value: "Группа",
    TaskType.POST.value: "Пост",
    TaskType.BOT.value: "Бот",
    TaskType.REACTION.value: "Реакции",
    TaskType.BOOST.value: "Premium Boost",
    TaskType.VIEW.value: "Просмотры поста",
}

AUDIENCE_LABELS = {
    "all": "все пользователи",
    "premium": "только Premium",
    "custom": "ручная настройка",
}

MIN_TASK_REWARDS = {
    (TaskType.CHANNEL.value, "all"): Decimal("750"),
    (TaskType.CHANNEL.value, "custom"): Decimal("750"),
    (TaskType.CHANNEL.value, "premium"): Decimal("1400"),
    (TaskType.GROUP.value, "all"): Decimal("1000"),
    (TaskType.GROUP.value, "custom"): Decimal("1000"),
    (TaskType.GROUP.value, "premium"): Decimal("1500"),
    (TaskType.VIEW.value, "all"): Decimal("100"),
}
BOT_MIN_REWARDS = {
    ("simple", "all"): Decimal("900"),
    ("simple", "premium"): Decimal("1400"),
    ("conditions", "all"): Decimal("3000"),
    ("conditions", "premium"): Decimal("4000"),
}
BOOST_PRICES = {
    7: Decimal("21000"),
    30: Decimal("90000"),
}
REACTION_MIN_REWARD = Decimal("600")
REACTION_FILTER_SURCHARGE = Decimal("100")
REACTION_RECOMMENDED_REWARD = Decimal("1000")
REACTION_COMMISSION_RATE = Decimal("0.15")
REACTION_STARS_DISCOUNT_RATE = Decimal("0.15")
VIEW_MIN_REWARD = Decimal("100")
VIEW_FILTER_SURCHARGE = Decimal("25")
VIEW_RECOMMENDED_REWARD = Decimal("300")
REACTION_LANG_LABELS = {
    "uk": "🇺🇦 Українська",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "de": "🇩🇪 Deutsch",
    "zh": "🇨🇳 中文",
    "ar": "🇸🇦 العربية",
    "fa": "🇮🇷 فارسی",
    "es": "🇪🇸 Español",
    "id": "🇮🇩 Bahasa Indonesia",
    "pt": "🇧🇷 Português",
    "hi": "🇮🇳 हिन्दी",
    "bn": "🇧🇩 বাংলা",
    "uz": "🇺🇿 O'zbekcha",
    "tr": "🇹🇷 Türkçe",
    "kk": "🇰🇿 Қазақша",
    "fr": "🇫🇷 Français",
}


def min_task_reward(task_type: str, audience: str | None, meta: dict | None = None) -> Decimal:
    if task_type == TaskType.BOT.value:
        mode = (meta or {}).get("bot_format", "simple")
        return BOT_MIN_REWARDS.get((mode, audience or "all"), Decimal("0"))
    return MIN_TASK_REWARDS.get((task_type, audience or "all"), Decimal("0"))


def boost_price(days: int) -> Decimal:
    return BOOST_PRICES.get(days, BOOST_PRICES[7])


def reaction_min_reward(selected_languages: list[str] | None = None) -> Decimal:
    if selected_languages:
        return REACTION_MIN_REWARD + REACTION_FILTER_SURCHARGE
    return REACTION_MIN_REWARD


def view_min_reward(selected_languages: list[str] | None = None) -> Decimal:
    if selected_languages:
        return VIEW_MIN_REWARD + VIEW_FILTER_SURCHARGE
    return VIEW_MIN_REWARD


def reaction_balance_total(base_total: Decimal) -> Decimal:
    return (base_total * (Decimal("1") + REACTION_COMMISSION_RATE)).quantize(Decimal("0.01"))


def reaction_stars_amount(base_total: Decimal, currency_per_star: int) -> int:
    discounted = base_total * (Decimal("1") - REACTION_STARS_DISCOUNT_RATE)
    return max(1, ceil(discounted / Decimal(currency_per_star)))


def reaction_audience_text(selected_languages: list[str] | None, currency_name: str) -> str:
    labels = [REACTION_LANG_LABELS.get(code, code) for code in selected_languages or []]
    audience = "\n".join(labels) if labels else "Все пользователи"
    return (
        "🎯 <b>Аудитория:</b>\n"
        f"{audience}\n\n"
        "Выберите, кому будет доступно задание на реакцию.\n\n"
        f"💡 Фильтр по языку добавляет +{money(REACTION_FILTER_SURCHARGE)} {currency_name} "
        "к минимальной цене за одно выполнение."
    )


def reaction_price_text(selected_languages: list[str] | None, currency_name: str, show_demand_tip: bool = False) -> str:
    minimum = reaction_min_reward(selected_languages)
    demand_tip = (
        "💡 Сейчас на реакции высокий спрос. Чтобы быстрее попасть в верхние позиции, "
        f"рекомендуем ставить не ниже {money(REACTION_RECOMMENDED_REWARD)} {currency_name}.\n\n"
        if show_demand_tip
        else ""
    )
    return (
        "Установите стоимость за 1 реакцию.\n"
        f"Чтобы разместить задание, на балансе должно быть достаточно {currency_name}.\n\n"
        f"🔴 Минимальная цена за ед. — {money(minimum)} {currency_name}\n\n"
        f"{demand_tip}"
        "Введите цену за одну реакцию."
    )


async def show_reaction_price_step(callback: CallbackQuery, session: AsyncSession, state: FSMContext, selected_languages: list[str] | None) -> None:
    settings = get_settings()
    active_reactions = await active_count_by_type(session, TaskType.REACTION.value)
    await state.set_state(CreateTask.waiting_reaction_price)
    await callback.message.edit_text(
        reaction_price_text(
            selected_languages,
            settings.currency_name,
            show_demand_tip=active_reactions >= 50,
        )
    )


def reaction_amount_text(reward: Decimal, balance: Decimal, currency_name: str) -> tuple[str, int]:
    one_with_fee = reaction_balance_total(reward)
    max_amount = int(balance // one_with_fee) if one_with_fee > 0 else 0
    text = (
        f"🔔 При оплате {currency_name} действует комиссия 15%.\n\n"
        "💡 Донат от 50 ⭐ отключает комиссию на 24 часа. Каждые следующие 50 ⭐ продлевают период ещё на 24 часа.\n\n"
        f"💵 Стоимость одной реакции: {money(reward)} {currency_name}\n"
        f"💰 Ваш баланс: {money(balance)} {currency_name}\n\n"
        "Введите количество реакций или выберите готовый вариант.\n\n"
        f"Максимум для вашего баланса: {max_amount}"
    )
    return text, max_amount


def reaction_payment_text(currency_name: str) -> str:
    return (
        "Выберите способ оплаты задания:\n\n"
        f"🔔 При оплате {currency_name} действует комиссия 15%.\n"
        "💡 Через Telegram Stars комиссия не применяется, а расчёт идёт со скидкой 15%."
    )


def ad_payment_text(currency_name: str) -> str:
    return (
        "Выберите способ оплаты задания:\n\n"
        f"🔔 При оплате {currency_name} действует комиссия 15%.\n"
        "💡 При оплате Telegram Stars комиссия не применяется, а сумма считается со скидкой 15%."
    )


def view_audience_text(selected_languages: list[str] | None, currency_name: str) -> str:
    labels = [REACTION_LANG_LABELS.get(code, code) for code in selected_languages or []]
    audience = "\n".join(labels) if labels else "🌐 без ограничений"
    return (
        f"🎯 <b>Аудитория:</b> {audience}\n\n"
        "Выберите целевую аудиторию задания.\n\n"
        f"💡 +{money(VIEW_FILTER_SURCHARGE)} {currency_name} к мин. цене за 1 выполнение при применении фильтра"
    )


def view_price_text(selected_languages: list[str] | None, currency_name: str, show_demand_tip: bool = False) -> str:
    minimum = view_min_reward(selected_languages)
    demand_tip = (
        "💡 Рекомендация: сейчас повышенный спрос на размещение заданий,\n"
        f"поэтому если вы хотите попасть на первые страницы — установите цену не ниже: {money(VIEW_RECOMMENDED_REWARD)} {currency_name}.\n\n"
        if show_demand_tip
        else ""
    )
    return (
        "Установите стоимость за 1 просмотр поста\n"
        f"Чтобы разместить задание, у Вас должно быть достаточно {currency_name} на Вашем счету\n\n"
        f"🔴 Минимальная цена за од. — {money(minimum)} {currency_name}\n\n"
        f"{demand_tip}"
        "📝 Введите цену за один просмотр:"
    )


def view_amount_text(reward: Decimal, balance: Decimal, max_amount: int, currency_name: str) -> str:
    return (
        f"{ad_payment_text(currency_name)}\n\n"
        f"💵 Стоимость одного просмотра: {money(reward)} {currency_name}\n"
        f"💰 Ваш баланс: {money(balance)} {currency_name}\n\n"
        "📝 Введите количество просмотров, или выберите:\n\n"
        f"Максимум для вашего баланса: {max_amount}"
    )


def bot_audience_text(mode: str, currency_name: str) -> str:
    all_min = BOT_MIN_REWARDS[(mode, "all")]
    premium_min = BOT_MIN_REWARDS[(mode, "premium")]
    return (
        "Выберите тип аккаунта:\n\n"
        "1️⃣ <b>Все пользователи</b> — доступно всем пользователям проекта, подходит для быстрого набора широкой аудитории.\n"
        f"🔴 Минимальная цена за ед. — {money(all_min)} {currency_name}\n\n"
        "2️⃣ <b>Только Telegram Premium</b> 🌟 — доступно только пользователям с Telegram Premium, аудитория обычно качественнее.\n"
        f"🔴 Минимальная цена за ед. — {money(premium_min)} {currency_name}"
    )


def ad_payment_totals(base_total: Decimal, currency_per_star: int) -> tuple[Decimal, int]:
    return reaction_balance_total(base_total), reaction_stars_amount(base_total, currency_per_star)


def reaction_url_text() -> str:
    return (
        "Отправьте ссылку на пост, где нужно поставить реакцию.\n\n"
        "Подойдут форматы:\n"
        "https://t.me/username/123\n"
        "https://t.me/c/123/456\n"
        "https://t.me/c/1234567890/123/123"
    )


def chat_target_text(task_type: str) -> str:
    if task_type == TaskType.CHANNEL.value:
        return (
            "Выберите канал для продвижения.\n\n"
            "Критерии:\n"
            "• канал должен быть публичным;\n"
            "• у вас должны быть права администратора: добавлять пользователей."
        )
    return (
        "Выберите группу для продвижения.\n\n"
        "Критерии:\n"
        "• группа должна быть публичной;\n"
        "• у вас должны быть права администратора: приглашать пользователей по ссылке."
    )


def boost_target_text() -> str:
    return (
        "Отправьте ссылку для Telegram Boost.\n\n"
        "Нужна именно ссылка вида:\n"
        "https://t.me/boost/username\n\n"
        "Бота также нужно добавить администратором в канал, чтобы позже можно было проверять удержание Boost."
    )


def chat_target_url(chat_shared) -> str:
    username = getattr(chat_shared, "username", None)
    if username:
        return f"https://t.me/{username}"
    return f"tg://resolve?domain={chat_shared.chat_id}"


async def safe_edit_text(message: Message, text: str, reply_markup=None) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise


async def replace_task_message(message: Message, text: str, reply_markup=None) -> None:
    if message.photo:
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
        await message.answer(text, reply_markup=reply_markup)
        return
    await safe_edit_text(message, text, reply_markup=reply_markup)


async def notify_task_owner_about_proof(bot, session: AsyncSession, task: Task, proof: TaskCompletion, performer_name: str) -> None:
    owner = await session.get(User, task.creator_id)
    if not owner or not owner.notifications_enabled:
        return
    settings = get_settings()
    text = (
        "🧾 <b>Новая заявка на проверку</b>\n\n"
        + tree_list(
            [
                f"Заявка: #{proof.id}",
                f"Задание: #{task.id}",
                f"Тип: {TASK_LABELS.get(task.type, task.type)}",
                f"Исполнитель: {escape(performer_name)}",
                f"Награда: {money(proof.reward)} {settings.currency_name}",
            ]
        )
        + "\n\nОткройте заявку, проверьте скриншот и примите решение."
    )
    try:
        await bot.send_message(
            owner.telegram_id,
            text,
            reply_markup=owner_proofs_keyboard([proof.id], task.type, "ads"),
        )
    except (TelegramBadRequest, TelegramForbiddenError):
        return


async def auto_pay_pending_proofs_for_task(session: AsyncSession, task: Task) -> tuple[int, Decimal]:
    paid_count = 0
    paid_total = Decimal("0")
    pending = await pending_completions_for_task(session, task.id)
    for proof in pending:
        proof.status = CompletionStatus.PAID.value
        await add_balance(session, proof.user_id, proof.reward)
        task.completed_count += 1
        paid_count += 1
        paid_total += proof.reward
    if task.completed_count >= task.total_limit:
        task.status = TaskStatus.COMPLETED.value
    return paid_count, paid_total


def cancellation_refund_amount(task: Task) -> Decimal:
    unused_count = max(task.total_limit - task.completed_count, 0)
    if unused_count <= 0:
        return Decimal("0")
    return (task.reward * Decimal(unused_count) * Decimal("0.85")).quantize(Decimal("0.01"))


async def refund_cancelled_task(session: AsyncSession, task: Task) -> Decimal:
    refund = cancellation_refund_amount(task)
    if refund > 0:
        await add_balance(session, task.creator_id, refund)
    return refund


def cancellation_summary(paid_count: int, paid_total: Decimal, refund: Decimal) -> str:
    settings = get_settings()
    lines = []
    if paid_count:
        lines.append(
            f"Заявки на проверку оплачены автоматически: {paid_count} шт. на {money(paid_total)} {settings.currency_name}."
        )
    if refund > 0:
        lines.append(f"Возврат за неиспользованный остаток: {money(refund)} {settings.currency_name} с удержанием комиссии 15%.")
    else:
        lines.append("Неиспользованного остатка для возврата нет.")
    return "\n\n" + "\n".join(lines)


async def cancel_task_money(session: AsyncSession, task: Task) -> tuple[int, Decimal, Decimal]:
    paid_count, paid_total = await auto_pay_pending_proofs_for_task(session, task)
    refund = await refund_cancelled_task(session, task)
    if refund > 0:
        task.total_limit = task.completed_count
    return paid_count, paid_total, refund


async def delete_task_permanently(session: AsyncSession, task: Task) -> tuple[int, Decimal, Decimal]:
    paid_count, paid_total, refund = await cancel_task_money(session, task)
    await session.execute(delete(Complaint).where(Complaint.task_id == task.id))
    await session.execute(delete(TaskCompletion).where(TaskCompletion.task_id == task.id))
    await session.delete(task)
    await session.flush()
    return paid_count, paid_total, refund


async def show_owner_proof(callback: CallbackQuery, proof: TaskCompletion, task: Task, source: str) -> None:
    hold_until = parse_datetime(proof.checked_at) if task.type == TaskType.BOOST.value else None
    details = [
        f"Задание: #{task.id}",
        f"Тип: {TASK_LABELS.get(task.type, task.type)}",
        f"Награда: {money(proof.reward)} {get_settings().currency_name}",
        f"Состояние: {status_label(proof.status)}",
        f"Скрин: {'приложен' if proof.proof_file_id else 'не приложен'}",
    ]
    if hold_until:
        details.append(f"Удерживать до: {hold_until.strftime('%d.%m.%Y %H:%M')}")
    text = (
        f"Заявка #{proof.id}\n\n"
        + tree_list(details)
    )
    reply_markup = owner_proof_card_keyboard(proof.id, task.type, source)
    if proof.proof_file_id:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=reply_markup)
            return
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await callback.message.answer_photo(proof.proof_file_id, caption=text, reply_markup=reply_markup)
        return
    await replace_task_message(callback.message, text, reply_markup=reply_markup)


def is_valid_target(value: str) -> bool:
    return value.startswith(("https://t.me/", "http://t.me/", "t.me/", "@"))


def normalize_target_url(value: str) -> str:
    target = value.strip()
    if target.startswith("@"):
        return f"https://t.me/{target[1:]}"
    if target.startswith("t.me/"):
        return f"https://{target}"
    return target


def is_valid_boost_url(value: str) -> bool:
    url = normalize_target_url(value)
    return url.startswith(("https://t.me/boost/", "http://t.me/boost/", "tg://boost"))


def boost_username_from_url(value: str) -> str | None:
    url = normalize_target_url(value).split("?", 1)[0].rstrip("/")
    marker = "/boost/"
    if marker not in url:
        return None
    username = url.rsplit(marker, 1)[-1].strip("/")
    return username or None


def naive_utc(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, int):
        return datetime.utcfromtimestamp(value)
    return None


async def user_has_active_boost(bot, task: Task, user: User) -> bool | None:
    if not task.target_chat_id:
        return None
    try:
        boosts = await bot.get_user_chat_boosts(chat_id=task.target_chat_id, user_id=user.telegram_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return None
    now = datetime.utcnow()
    for boost in boosts.boosts:
        expiration = naive_utc(getattr(boost, "expiration_date", None))
        if expiration is None or expiration > now:
            return True
    return False


def boost_task_text(task: Task, currency_name: str) -> str:
    meta = task_meta(task)
    days = int(meta.get("boost_days", 7))
    available = max(task.total_limit - task.completed_count, 0)
    title = escape(meta.get("boost_target_title") or task.title)
    return (
        f"<b>{title}</b>\n\n"
        f"⚠️ <b>Условия:</b> Boost нужно удерживать {days} полных дней. "
        "Если снять Boost раньше срока, часть награды может быть списана пропорционально неиспользованному времени.\n\n"
        "⚠️ <b>Уведомление:</b> после окончания срока удержания вы получите сообщение, "
        "когда Boost можно будет снять без штрафа.\n\n"
        f"🟢 Доступно для выполнения: {available} заданий\n\n"
        f"Награда: {money(task.reward)} {currency_name}"
    )


def boost_hold_until(task: Task) -> datetime:
    meta = task_meta(task)
    days = int(meta.get("boost_days", 7))
    return datetime.utcnow() + timedelta(days=days)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


async def verify_boost_task(bot, session: AsyncSession, task: Task, user: User) -> str:
    has_boost = await user_has_active_boost(bot, task, user)
    if has_boost is None:
        return "no_chat_id" if not task.target_chat_id else "api_error"
    if not has_boost:
        return "no_boost"

    completion = await get_completion(session, task.id, user.id)
    if completion and completion.status == CompletionStatus.PAID.value:
        return "already"

    now = datetime.utcnow()
    if completion and completion.status == CompletionStatus.PENDING.value:
        hold_until = parse_datetime(completion.checked_at)
        if hold_until and now < hold_until:
            return "wait"
        completion.status = CompletionStatus.PAID.value
        await add_balance(session, completion.user_id, completion.reward)
        task.completed_count += 1
        if task.completed_count >= task.total_limit:
            task.status = TaskStatus.COMPLETED.value
        return "paid"

    completion = await create_pending_proof(session, task, user, None)
    if not completion:
        return "already"
    completion.checked_at = boost_hold_until(task).isoformat(timespec="seconds")
    return "pending"


def title_for_task(task_type: str, url: str, meta: dict) -> str:
    label = TASK_LABELS.get(task_type, "Задание")
    if task_type == TaskType.BOOST.value and meta.get("boost_days"):
        label = f"{label} на {meta['boost_days']} дней"
    return label


def description_for_task(task_type: str, meta: dict) -> str:
    if task_type == TaskType.BOOST.value:
        days = meta.get("boost_days", 7)
        return f"Поставьте Premium Boost на {days} дней. Не снимайте boost раньше срока, иначе награда может быть списана."
    if task_type == TaskType.BOT.value and meta.get("conditions"):
        return f"Запустите бота и выполните условия: {meta['conditions']}"
    if task_type == TaskType.REACTION.value:
        if meta.get("reaction_mode") == "selected" and meta.get("reaction_emoji"):
            return f"Поставьте реакцию {meta['reaction_emoji']} на пост и отправьте скриншот подтверждения."
        if meta.get("reaction_mode") == "selected" and meta.get("reaction_image_file_id"):
            return "Поставьте реакцию, указанную на скриншоте, и отправьте скриншот подтверждения."
        return "Поставьте любую реакцию на пост и отправьте скриншот подтверждения."
    if task_type == TaskType.VIEW.value:
        return "Откройте публикацию и отправьте скриншот просмотра."
    return "Выполните действие и нажмите проверку."


async def show_ad_cabinet(callback: CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    await callback.message.edit_text(
        t(
            user.language,
            "advertise",
            project_name=settings.project_name,
            balance=money(user.balance),
            currency_name=settings.currency_name,
        ),
        reply_markup=advertise_keyboard(),
    )


def reaction_mode_label(mode: str | None) -> str:
    return "выбранные реакции" if mode == "selected" else "любые реакции"


def reaction_category_text(any_count: int, selected_count: int) -> str:
    return (
        "Выберите категорию реакций.\n"
        f"Любые: {any_count}\n"
        f"Выбранные: {selected_count}\n\n"
        "Любые реакции — исполнитель может поставить любую реакцию на своё усмотрение.\n\n"
        "Выбранные реакции — нужно поставить реакцию, указанную автором задания."
    )


def boost_terms_text(currency_name: str) -> str:
    return (
        "⚡ <b>Выберите период буста:</b>\n\n"
        f"📊 7 дней: 21 000 {currency_name}\n"
        f"📊 30 дней: 90 000 {currency_name}"
    )


def reaction_mode_setup_text() -> str:
    return (
        "Выберите тип задания с реакциями.\n\n"
        "Любые реакции — исполнитель может поставить любую реакцию.\n\n"
        "Установленные реакции — исполнитель должен поставить конкретную реакцию, которую вы укажете."
    )


def reaction_task_text(task: Task, currency_name: str) -> str:
    meta = task_meta(task)
    selected = meta.get("reaction_mode") == "selected"
    intro = "Поставьте указанную реакцию" if selected else "Поставьте любую реакцию"
    details = [
        f"Награда: {money(task.reward)} {currency_name}",
    ]
    reaction = meta.get("reaction_emoji")
    if selected and reaction:
        details.append(f"Нужная реакция: {reaction}")
    elif selected and meta.get("reaction_image_file_id"):
        details.append("Нужная реакция: указана на скриншоте")
    return (
        f"Задание #{task.id}\n"
        f"{intro}\n\n"
        "Отправьте скриншот, на котором чётко видно, что реакция поставлена для подтверждения оплаты.\n\n"
        "⚠️ Если в канале запрещены скриншоты, отправьте скрин без содержимого. По правилам автор всё равно должен оплатить выполнение.\n\n"
        + tree_list(details)
    )


@router.callback_query(F.data == "tasks:noop")
async def tasks_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == "tasks:reaction_categories")
async def reaction_categories(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    any_tasks, any_count = await list_active(session, TaskType.REACTION.value, user, 1, per_page=1, reaction_mode="any")
    selected_tasks, selected_count = await list_active(session, TaskType.REACTION.value, user, 1, per_page=1, reaction_mode="selected")
    await callback.message.edit_text(
        reaction_category_text(any_count, selected_count),
        reply_markup=reaction_categories_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "tasks:boost_terms")
async def boost_terms(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    if not user.is_premium:
        await callback.answer("Это задание доступно только владельцам Telegram Premium.", show_alert=True)
        return
    settings = get_settings()
    await callback.message.edit_text(
        boost_terms_text(settings.currency_name),
        reply_markup=boost_terms_keyboard(settings.currency_name),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tasks:") & (F.data != "tasks:noop"))
async def list_tasks(callback: CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    parts = callback.data.split(":")
    reaction_mode = None
    boost_days = None
    if len(parts) == 4 and parts[1] == "reaction":
        task_type = TaskType.REACTION.value
        reaction_mode = parts[2]
        page_raw = parts[3]
    elif len(parts) == 4 and parts[1] == "boost":
        task_type = TaskType.BOOST.value
        boost_days = int(parts[2])
        page_raw = parts[3]
    else:
        _, task_type, page_raw = parts
    page = int(page_raw)
    if task_type == TaskType.BOOST.value and not user.is_premium:
        await callback.answer("Это задание доступно только владельцам Telegram Premium.", show_alert=True)
        return
    if boost_days:
        all_boost_tasks, _total = await list_active(session, task_type, user, 1, per_page=1000)
        matching = [task for task in all_boost_tasks if int(task_meta(task).get("boost_days", 7)) == boost_days]
        total = len(matching)
        start = max(page - 1, 0) * TASKS_PER_PAGE
        tasks = matching[start : start + TASKS_PER_PAGE]
    else:
        tasks, total = await list_active(session, task_type, user, page, per_page=TASKS_PER_PAGE, reaction_mode=reaction_mode)
    if not tasks:
        reply_markup = boost_terms_keyboard(settings.currency_name) if boost_days else empty_tasks_keyboard()
        await callback.message.edit_text(t(user.language, "no_tasks"), reply_markup=reply_markup)
        await callback.answer()
        return
    pages = max(1, (total + TASKS_PER_PAGE - 1) // TASKS_PER_PAGE)
    await callback.message.edit_text(
        t(
            user.language,
            "task_list",
            total=total,
            page=page,
            pages=pages,
        ),
        reply_markup=task_list_keyboard(tasks, task_type, page, pages, settings.currency_name, reaction_mode=reaction_mode, boost_days=boost_days),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task_view:"))
async def task_view(callback: CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    parts = callback.data.split(":")
    _, task_id_raw, task_type, page_raw = parts[:4]
    context = parts[4] if len(parts) > 4 and parts[4] != "-" else None
    reaction_mode = context if task_type == TaskType.REACTION.value else None
    boost_days = int(context) if task_type == TaskType.BOOST.value and context and context.isdigit() else None
    page = int(page_raw)
    task = await session.get(Task, int(task_id_raw))
    if not task or task.status != TaskStatus.ACTIVE.value:
        await callback.answer("Задание уже недоступно.", show_alert=True)
        await callback.message.edit_text(t(user.language, "no_tasks"), reply_markup=empty_tasks_keyboard())
        return
    if task.type == TaskType.REACTION.value:
        task_text = reaction_task_text(task, settings.currency_name)
    elif task.type == TaskType.BOOST.value:
        task_text = boost_task_text(task, settings.currency_name)
    elif task.type == TaskType.BOT.value:
        task_text = (
            "⚠️ Перейдите в бот, нажмите Start и сделайте скриншот, где видно, что бот запущен.\n\n"
            "Если появится капча, пройдите её. Остальные условия выполнять не нужно.\n\n"
            "Отправьте скриншот сюда для проверки."
        )
    else:
        task_text = t(
            user.language,
            "task_card",
            id=task.id,
            title=escape(task.title),
            task_details=tree_list(
                [
                    f"Награда: {money(task.reward)} {settings.currency_name}",
                ]
            ),
        )
    meta = task_meta(task)
    markup = task_keyboard(
        task.id,
        task_type,
        task.target_url,
        page,
        1,
        reaction_mode=reaction_mode,
        boost_days=boost_days,
        reaction_emoji=meta.get("reaction_emoji"),
        reaction_has_image=bool(meta.get("reaction_image_file_id")),
    )
    if task.type == TaskType.REACTION.value and meta.get("reaction_image_file_id"):
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await callback.message.answer_photo(
            meta["reaction_image_file_id"],
            caption=task_text,
            reply_markup=markup,
        )
    else:
        await replace_task_message(callback.message, task_text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("task_check:"))
async def check_task(callback: CallbackQuery, session: AsyncSession, bot, state: FSMContext) -> None:
    task_id = int(callback.data.split(":")[1])
    task = await session.get(Task, task_id)
    user = await current_user(callback, session)
    if not task:
        await callback.answer("Задание не найдено", show_alert=True)
        return
    if task.type == TaskType.BOOST.value:
        status = await verify_boost_task(bot, session, task, user)
        messages = {
            "pending": "Boost найден. Заявка создана, теперь удерживайте Boost до окончания срока.",
            "wait": "Boost найден, но срок удержания ещё не закончился. Проверьте позже.",
            "paid": "Boost удержан нужный срок. Награда начислена.",
            "already": "Это задание уже было засчитано.",
            "no_boost": "Boost от вашего аккаунта пока не найден. Нажмите «Зарядить» и повторите проверку.",
            "no_chat_id": "Для этого задания нет chat_id канала, поэтому доступна только ручная проверка владельцем.",
            "api_error": "Не удалось проверить Boost. Убедитесь, что бот добавлен администратором в канал.",
        }
        if status == "no_chat_id":
            meta = task_meta(task)
            days = int(meta.get("boost_days", 7))
            await state.set_state(ManualProof.waiting_screenshot)
            await state.update_data(task_id=task.id)
            await callback.message.answer(
                f"Пришлите скриншот, где видно, что Boost поставлен.\n\n"
                f"Boost нужно удерживать {days} дней. Заявку можно будет принять после окончания этого срока."
            )
        await callback.answer(messages.get(status, "Проверка Boost завершилась неизвестным статусом."), show_alert=True)
        return
    if task.type in {item.value for item in MANUAL_PROOF_TYPES}:
        await state.set_state(ManualProof.waiting_screenshot)
        await state.update_data(task_id=task.id)
        await callback.message.answer("Пришлите скриншот подтверждения одним изображением.")
        await callback.answer()
        return
    status = await verify_subscription_task(bot, session, task, user)
    messages = {
        "paid": "Проверка пройдена, награда начислена.",
        "already": "Это задание уже было засчитано.",
        "not_member": "Подписка не найдена. Выполните действие и повторите проверку.",
        "api_error": "Telegram не дал проверить подписку. Убедитесь, что бот имеет доступ к каналу/группе.",
        "no_chat_id": "У задания не указан chat_id для автоматической проверки.",
    }
    await callback.answer(messages.get(status, "Задание требует ручной проверки."), show_alert=True)


@router.message(ManualProof.waiting_screenshot, F.photo)
async def receive_proof(message: Message, session: AsyncSession, state: FSMContext, bot) -> None:
    data = await state.get_data()
    task = await session.get(Task, int(data["task_id"]))
    user = await current_user(message, session)
    if task:
        completion = await create_pending_proof(session, task, user, message.photo[-1].file_id)
        if completion:
            if task.type == TaskType.BOOST.value:
                completion.checked_at = boost_hold_until(task).isoformat(timespec="seconds")
            await notify_task_owner_about_proof(bot, session, task, completion, message.from_user.full_name if message.from_user else user.first_name or str(user.telegram_id))
            if task.type == TaskType.BOOST.value:
                hold_until = parse_datetime(completion.checked_at)
                hold_line = f"\n\nBoost нужно удерживать до: {hold_until.strftime('%d.%m.%Y %H:%M')}" if hold_until else ""
                await message.answer(
                    "Заявка по Boost отправлена владельцу задания.\n\n"
                    "Награда будет начислена после проверки и окончания срока удержания."
                    f"{hold_line}",
                    reply_markup=proof_submitted_keyboard(completion.id),
                )
                await state.clear()
                return
            await message.answer(
                "Заявка отправлена владельцу задания на проверку.\n\n"
                f"Если владелец не ответит в течение {get_settings().proof_dispute_delay_hours} ч., откройте спор. Тогда заявку проверит администратор.",
                reply_markup=proof_submitted_keyboard(completion.id),
            )
        else:
            await message.answer("Это задание уже отправлялось на проверку.")
    await state.clear()


@router.callback_query(F.data.startswith("proof_dispute:"))
async def open_proof_dispute(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    settings = get_settings()
    completion_id = int(callback.data.split(":")[1])
    proof = await session.get(TaskCompletion, completion_id)
    if not proof or proof.user_id != user.id:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return
    if proof.status != CompletionStatus.PENDING.value:
        await callback.answer("По этой заявке уже нельзя открыть спор.", show_alert=True)
        return
    can_dispute_at = proof.created_at + timedelta(hours=settings.proof_dispute_delay_hours)
    if datetime.utcnow() < can_dispute_at:
        remaining = can_dispute_at - datetime.utcnow()
        hours_left = max(1, int((remaining.total_seconds() + 3599) // 3600))
        await callback.answer(f"Спор можно открыть, если владелец не ответит. Осталось примерно {hours_left} ч.", show_alert=True)
        return
    proof.status = CompletionStatus.DISPUTED.value
    await callback.message.edit_text(
        "Спор открыт. Заявка передана администраторам на проверку.\n\n"
        "Решение администратора будет окончательным."
    )
    await callback.answer()


async def show_reaction_setup(callback: CallbackQuery, user: User, state: FSMContext, meta: dict | None = None) -> None:
    await state.update_data(task_type=TaskType.REACTION.value, meta=meta or {})
    await callback.message.edit_text(
        t(user.language, "ad_reaction_intro") + "\n\n" + reaction_mode_setup_text(),
        reply_markup=reaction_mode_keyboard(),
    )


async def show_reaction_audience_setup(callback: CallbackQuery, user: User, state: FSMContext) -> None:
    selected_languages = ["ru"]
    data = await state.get_data()
    await state.update_data(
        task_type=TaskType.REACTION.value,
        audience_type="custom",
        filters={"languages": selected_languages},
        meta=data.get("meta", {}),
    )
    await callback.message.edit_text(
        reaction_audience_text(selected_languages, get_settings().currency_name),
        reply_markup=reaction_audience_keyboard(),
    )


@router.callback_query(F.data == "ad:back")
async def ad_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    await show_ad_cabinet(callback, session)
    await callback.answer()


@router.callback_query(F.data.startswith("ad:start:"))
async def ad_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(callback, session)
    task_type = callback.data.split(":")[2]
    await state.clear()
    await state.update_data(task_type=task_type, meta={})

    if task_type == TaskType.CHANNEL.value:
        await callback.message.edit_text(
            t(user.language, "ad_channel_intro", currency_name=get_settings().currency_name),
            reply_markup=audience_keyboard(task_type),
        )
    elif task_type == TaskType.GROUP.value:
        await callback.message.edit_text(
            t(user.language, "ad_group_intro", currency_name=get_settings().currency_name),
            reply_markup=audience_keyboard(task_type),
        )
    elif task_type == TaskType.POST.value:
        await callback.message.edit_text(t(user.language, "ad_post_intro"), reply_markup=post_format_keyboard())
    elif task_type == TaskType.BOT.value:
        await callback.message.edit_text(t(user.language, "ad_bot_intro"), reply_markup=bot_format_keyboard())
    elif task_type == TaskType.REACTION.value:
        await show_reaction_setup(callback, user, state)
    elif task_type == TaskType.BOOST.value:
        await callback.message.edit_text(
            t(user.language, "ad_boost_intro", currency_name=get_settings().currency_name),
            reply_markup=boost_term_keyboard(get_settings().currency_name),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("ad:audience:"))
async def ad_audience(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(callback, session)
    _, _, task_type, audience = callback.data.split(":")
    await state.update_data(task_type=task_type, audience_type=audience)
    if audience == "custom":
        await state.set_state(CreateTask.waiting_manual_filters)
        await callback.message.edit_text(t(user.language, "ad_manual_filters"))
    elif task_type in {TaskType.CHANNEL.value, TaskType.GROUP.value}:
        await state.set_state(CreateTask.waiting_chat_target)
        await callback.message.answer(
            chat_target_text(task_type),
            reply_markup=request_channel_keyboard() if task_type == TaskType.CHANNEL.value else request_group_keyboard(),
        )
    else:
        await state.set_state(CreateTask.waiting_url)
        await callback.message.edit_text(t(user.language, "ad_send_url"))
    await callback.answer()


@router.message(CreateTask.waiting_manual_filters)
async def ad_manual_filters(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    task_type = data.get("task_type")
    await state.update_data(filters={"audience_note": message.text or ""})
    if task_type in {TaskType.CHANNEL.value, TaskType.GROUP.value}:
        await state.set_state(CreateTask.waiting_chat_target)
        await message.answer(
            "Фильтры сохранены.\n\n" + chat_target_text(task_type),
            reply_markup=request_channel_keyboard() if task_type == TaskType.CHANNEL.value else request_group_keyboard(),
        )
    else:
        await state.set_state(CreateTask.waiting_url)
        await message.answer("Фильтры сохранены. Теперь отправьте ссылку на объект продвижения.")


@router.callback_query(F.data.startswith("ad:format:"))
async def ad_post_format(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(callback, session)
    task_type = callback.data.split(":")[2]
    await state.update_data(task_type=task_type, audience_type="all", meta={"post_format": task_type})
    if task_type == TaskType.REACTION.value:
        await show_reaction_setup(callback, user, state, meta={"post_format": task_type})
    else:
        await state.update_data(task_type=TaskType.VIEW.value, audience_type="all", filters={"languages": []}, meta={"post_format": task_type})
        await callback.message.edit_text(
            view_audience_text([], get_settings().currency_name),
            reply_markup=view_audience_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("ad:bot_format:"))
async def ad_bot_format(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(callback, session)
    settings = get_settings()
    mode = callback.data.split(":")[2]
    await state.update_data(task_type=TaskType.BOT.value, meta={"bot_format": mode})
    await callback.message.edit_text(
        bot_audience_text(mode, settings.currency_name),
        reply_markup=bot_audience_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ad:bot_audience:"))
async def ad_bot_audience(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(callback, session)
    audience = callback.data.split(":")[2]
    data = await state.get_data()
    meta = data.get("meta", {})
    mode = meta.get("bot_format", "simple")
    await state.update_data(task_type=TaskType.BOT.value, audience_type=audience, meta=meta)
    if mode == "conditions":
        await state.set_state(CreateTask.waiting_bot_conditions)
        await callback.message.edit_text("Опишите дополнительные условия для исполнителя одним сообщением.")
    else:
        await state.set_state(CreateTask.waiting_url)
        await callback.message.edit_text(t(user.language, "ad_send_url"))
    await callback.answer()


@router.message(CreateTask.waiting_bot_conditions)
async def ad_bot_conditions(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    meta = data.get("meta", {})
    meta["conditions"] = message.text or ""
    await state.update_data(meta=meta)
    await state.set_state(CreateTask.waiting_url)
    await message.answer("Условия записаны. Теперь отправьте ссылку или username бота.")


@router.message(CreateTask.waiting_chat_target, F.chat_shared)
async def ad_chat_target(message: Message, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    user = await current_user(message, session)
    data = await state.get_data()
    task_type = data.get("task_type")
    chat_shared = message.chat_shared
    if not chat_shared:
        await message.answer("Не удалось получить выбранный чат. Попробуйте ещё раз.")
        return
    expected_request = REQUEST_CHANNEL_ID if task_type == TaskType.CHANNEL.value else REQUEST_GROUP_ID
    if chat_shared.request_id != expected_request:
        await message.answer("Выберите подходящий тип: канал для рекламы канала или группу для рекламы группы.")
        return
    target_url = chat_target_url(chat_shared)
    meta = data.get("meta", {})
    meta["target_title"] = chat_shared.title or ""
    meta["target_username"] = chat_shared.username or ""
    await state.update_data(
        target_url=target_url,
        target_chat_id=str(chat_shared.chat_id),
        meta=meta,
    )
    minimum = min_task_reward(task_type or "", data.get("audience_type"), meta)
    min_line = f"\nМинимальная цена: {money(minimum)} {settings.currency_name}" if minimum > 0 else ""
    await state.set_state(CreateTask.waiting_reward)
    await message.answer(
        f"Выбран чат: {escape(chat_shared.title or target_url)}\n\n"
        + t(user.language, "ad_send_reward", currency_name=settings.currency_name, min_line=min_line),
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(CreateTask.waiting_chat_target)
async def ad_chat_target_invalid(message: Message, state: FSMContext) -> None:
    if (message.text or "").endswith("Назад") or (message.text or "") == "Назад":
        await state.clear()
        await message.answer("Выбор отменён.", reply_markup=ReplyKeyboardRemove())
        return
    await message.answer("Выберите канал или группу через кнопку Telegram ниже.")


@router.callback_query(F.data.startswith("ad:reaction_mode:"))
async def ad_reaction_mode(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(callback, session)
    mode = callback.data.split(":")[2]
    data = await state.get_data()
    meta = data.get("meta", {})
    meta["reaction_mode"] = mode
    if mode == "selected":
        await state.update_data(meta=meta)
        await state.set_state(CreateTask.waiting_reaction_emoji)
        await callback.message.edit_text(
            "Отправьте реакцию, которую нужно будет поставить исполнителям.\n\n"
            "Например: 🔥 или ❤️\n\n"
            "Если нужны Premium-реакции, пришлите скриншот, где видно, какие реакции нужно нажать."
        )
    else:
        meta.pop("reaction_emoji", None)
        await state.update_data(meta=meta)
        await show_reaction_audience_setup(callback, user, state)
    await callback.answer()


@router.message(CreateTask.waiting_reaction_emoji, F.photo)
async def ad_reaction_emoji_photo(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await current_user(message, session)
    data = await state.get_data()
    meta = data.get("meta", {})
    meta["reaction_mode"] = "selected"
    meta["reaction_image_file_id"] = message.photo[-1].file_id
    meta.pop("reaction_emoji", None)
    await state.update_data(meta=meta)
    selected_languages = ["ru"]
    await state.update_data(
        task_type=TaskType.REACTION.value,
        audience_type="custom",
        filters={"languages": selected_languages},
    )
    await message.answer(
        "Скриншот с нужными реакциями сохранён.\n\n" + reaction_audience_text(selected_languages, get_settings().currency_name),
        reply_markup=reaction_audience_keyboard(),
    )


@router.message(CreateTask.waiting_reaction_emoji, F.text)
async def ad_reaction_emoji(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(message, session)
    reaction = (message.text or "").strip()
    if not reaction or len(reaction) > 8:
        await message.answer("Отправьте одну реакцию коротким сообщением, например 🔥.")
        return
    data = await state.get_data()
    meta = data.get("meta", {})
    meta["reaction_mode"] = "selected"
    meta["reaction_emoji"] = reaction
    meta.pop("reaction_image_file_id", None)
    await state.update_data(meta=meta)
    selected_languages = ["ru"]
    await state.update_data(
        task_type=TaskType.REACTION.value,
        audience_type="custom",
        filters={"languages": selected_languages},
    )
    await message.answer(
        reaction_audience_text(selected_languages, get_settings().currency_name),
        reply_markup=reaction_audience_keyboard(),
    )


@router.callback_query(F.data == "ad:reaction_audience:all")
async def ad_reaction_audience_all(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await current_user(callback, session)
    await state.update_data(audience_type="all", filters={"languages": []})
    await show_reaction_price_step(callback, session, state, [])
    await callback.answer()


@router.callback_query(F.data == "ad:reaction_audience_menu")
async def ad_reaction_audience_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(callback, session)
    settings = get_settings()
    data = await state.get_data()
    selected = (data.get("filters") or {}).get("languages") or ["ru"]
    if data.get("task_type") == TaskType.VIEW.value:
        await safe_edit_text(
            callback.message,
            view_audience_text(selected, settings.currency_name),
            reply_markup=view_audience_keyboard(),
        )
        await callback.answer()
        return
    await safe_edit_text(
        callback.message,
        t(user.language, "ad_reaction_intro") + "\n\n" + reaction_audience_text(selected, settings.currency_name),
        reply_markup=reaction_audience_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "ad:reaction_audience:choose")
async def ad_reaction_audience_choose(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    data = await state.get_data()
    filters = data.get("filters", {})
    selected = filters.get("languages") or ["ru"]
    await state.update_data(audience_type="custom", filters={"languages": selected})
    await safe_edit_text(
        callback.message,
        reaction_audience_text(selected, settings.currency_name),
        reply_markup=reaction_languages_keyboard(selected),
    )
    await callback.answer()


async def show_view_price_step(callback: CallbackQuery, session: AsyncSession, state: FSMContext, selected_languages: list[str]) -> None:
    settings = get_settings()
    active_views = await active_count_by_type(session, TaskType.VIEW.value)
    await state.set_state(CreateTask.waiting_view_price)
    await safe_edit_text(
        callback.message,
        view_price_text(selected_languages, settings.currency_name, show_demand_tip=active_views >= 50),
    )


@router.callback_query(F.data == "ad:view_audience:all")
async def ad_view_audience_all(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await current_user(callback, session)
    await state.update_data(task_type=TaskType.VIEW.value, audience_type="all", filters={"languages": []})
    await show_view_price_step(callback, session, state, [])
    await callback.answer()


@router.callback_query(F.data == "ad:view_audience:choose")
async def ad_view_audience_choose(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await current_user(callback, session)
    selected = ["ru"]
    await state.update_data(task_type=TaskType.VIEW.value, audience_type="custom", filters={"languages": selected})
    await callback.message.edit_text(
        view_audience_text(selected, get_settings().currency_name),
        reply_markup=reaction_languages_keyboard(selected),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ad:reaction_lang:"))
async def ad_reaction_lang_toggle(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    code = callback.data.split(":")[2]
    data = await state.get_data()
    selected = list((data.get("filters") or {}).get("languages") or [])
    if code in selected:
        selected.remove(code)
    else:
        selected.append(code)
    await state.update_data(audience_type="custom" if selected else "all", filters={"languages": selected})
    text = (
        view_audience_text(selected, settings.currency_name)
        if data.get("task_type") == TaskType.VIEW.value
        else reaction_audience_text(selected, settings.currency_name)
    )
    await safe_edit_text(
        callback.message,
        text,
        reply_markup=reaction_languages_keyboard(selected),
    )
    await callback.answer()


@router.callback_query(F.data == "ad:reaction_lang_save")
async def ad_reaction_lang_save(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    selected = (data.get("filters") or {}).get("languages") or []
    await state.update_data(audience_type="custom" if selected else "all")
    if data.get("task_type") == TaskType.VIEW.value:
        await show_view_price_step(callback, session, state, selected)
        await callback.answer()
        return
    await show_reaction_price_step(callback, session, state, selected)
    await callback.answer()


@router.callback_query(F.data == "ad:reaction_price_back")
async def ad_reaction_price_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    selected = (data.get("filters") or {}).get("languages") or []
    await show_reaction_price_step(callback, session, state, selected)
    await callback.answer()


@router.message(CreateTask.waiting_reaction_price)
async def ad_reaction_price(message: Message, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    user = await current_user(message, session)
    value = (message.text or "").replace(",", ".").strip()
    try:
        reward = Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        await message.answer("Введите корректную цену за одну реакцию.")
        return
    if reward <= 0 or not reward.is_finite():
        await message.answer("Цена должна быть больше нуля.")
        return
    data = await state.get_data()
    selected = (data.get("filters") or {}).get("languages") or []
    minimum = reaction_min_reward(selected)
    if reward < minimum:
        await message.answer(f"Минимальная цена для выбранной аудитории: {money(minimum)} {settings.currency_name}.")
        return
    text, max_amount = reaction_amount_text(reward, user.balance, settings.currency_name)
    await state.update_data(reward=str(reward))
    await state.set_state(CreateTask.waiting_reaction_amount)
    await message.answer(text, reply_markup=reaction_amount_keyboard(max_amount))


@router.callback_query(F.data == "ad:reaction_amount_back")
async def ad_reaction_amount_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    data = await state.get_data()
    reward = Decimal(data.get("reward", "0"))
    if reward <= 0:
        selected = (data.get("filters") or {}).get("languages") or []
        await show_reaction_price_step(callback, session, state, selected)
    else:
        text, max_amount = reaction_amount_text(reward, user.balance, settings.currency_name)
        await state.set_state(CreateTask.waiting_reaction_amount)
        await callback.message.edit_text(text, reply_markup=reaction_amount_keyboard(max_amount))
    await callback.answer()


@router.callback_query(F.data.startswith("ad:reaction_amount:"))
async def ad_reaction_amount_pick(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    amount = int(callback.data.split(":")[2])
    await show_reaction_payment_choice(callback, session, state, amount)


@router.message(CreateTask.waiting_reaction_amount)
async def ad_reaction_amount(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not (message.text or "").isdigit():
        await message.answer("Введите целое количество реакций.")
        return
    await show_reaction_payment_choice(message, session, state, int(message.text))


async def show_reaction_payment_choice(event: CallbackQuery | Message, session: AsyncSession, state: FSMContext, amount: int) -> None:
    settings = get_settings()
    user = await current_user(event, session)
    if amount <= 0:
        text = "Количество реакций должно быть больше нуля."
        if isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
        else:
            await event.answer(text)
        return
    data = await state.get_data()
    reward = Decimal(data["reward"])
    base_total = reward * amount
    balance_total = reaction_balance_total(base_total)
    stars = reaction_stars_amount(base_total, settings.currency_per_star)
    await state.update_data(limit=amount, base_total=str(base_total), total=str(balance_total), reaction_stars=stars)
    text = reaction_payment_text(settings.currency_name)
    markup = reaction_payment_keyboard(money(balance_total), stars, settings.currency_name)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=markup)
        await event.answer()
    else:
        await event.answer(text, reply_markup=markup)


@router.callback_query(F.data == "ad:view_price_back")
async def ad_view_price_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    selected = (data.get("filters") or {}).get("languages") or []
    await show_view_price_step(callback, session, state, selected)
    await callback.answer()


@router.message(CreateTask.waiting_view_price)
async def ad_view_price(message: Message, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    user = await current_user(message, session)
    value = (message.text or "").replace(",", ".").strip()
    try:
        reward = Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        await message.answer("Введите корректную цену за один просмотр.")
        return
    if reward <= 0 or not reward.is_finite():
        await message.answer("Цена должна быть больше нуля.")
        return
    data = await state.get_data()
    selected = (data.get("filters") or {}).get("languages") or []
    minimum = view_min_reward(selected)
    if reward < minimum:
        await message.answer(f"Минимальная цена для выбранной аудитории: {money(minimum)} {settings.currency_name}.")
        return
    max_amount = int(user.balance // reward) if reward > 0 else 0
    await state.update_data(reward=str(reward))
    await state.set_state(CreateTask.waiting_view_amount)
    await message.answer(view_amount_text(reward, user.balance, max_amount, settings.currency_name), reply_markup=view_amount_keyboard(max_amount))


async def show_view_payment_choice(event: CallbackQuery | Message, session: AsyncSession, state: FSMContext, amount: int) -> None:
    settings = get_settings()
    if amount <= 0:
        text = "Количество просмотров должно быть больше нуля."
        if isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
        else:
            await event.answer(text)
        return
    data = await state.get_data()
    reward = Decimal(data["reward"])
    base_total = reward * amount
    balance_total, stars = ad_payment_totals(base_total, settings.currency_per_star)
    await state.update_data(task_type=TaskType.VIEW.value, base_total=str(base_total), total=str(balance_total), limit=amount, ad_stars=stars)
    text = ad_payment_text(settings.currency_name)
    markup = ad_payment_keyboard(money(balance_total), stars, settings.currency_name)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=markup)
        await event.answer()
    else:
        await event.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("ad:view_amount:"))
async def ad_view_amount_pick(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await show_view_payment_choice(callback, session, state, int(callback.data.split(":")[2]))


@router.message(CreateTask.waiting_view_amount)
async def ad_view_amount(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not (message.text or "").isdigit():
        await message.answer("Введите целое количество просмотров.")
        return
    await show_view_payment_choice(message, session, state, int(message.text))


@router.callback_query(F.data.startswith("ad:reaction_pay:"))
async def ad_reaction_pay(callback: CallbackQuery, session: AsyncSession, state: FSMContext, bot) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    method = callback.data.split(":")[2]
    data = await state.get_data()
    base_total = Decimal(data["base_total"])
    balance_total = Decimal(data["total"])
    stars = int(data["reaction_stars"])
    if method == "balance":
        if user.balance < balance_total:
            await callback.answer(
                f"Недостаточно средств. Нужно {money(balance_total)} {settings.currency_name}.",
                show_alert=True,
            )
            return
        await state.update_data(total=str(balance_total), payment_method="balance")
        await state.set_state(CreateTask.waiting_reaction_url)
        await callback.message.edit_text(reaction_url_text())
        await callback.answer()
        return

    if is_test_mode():
        payment = await create_stars_topup(session, user, base_total, stars)
        await complete_stars_payment(session, user.telegram_id, payment.payload or "", stars, f"test-charge-{payment.id}", "mock", is_test=True)
        await state.update_data(total=str(base_total), payment_method="stars", reaction_stars_payload=payment.payload, stars_paid=True)
        await state.set_state(CreateTask.waiting_reaction_url)
        await callback.message.edit_text(
            test_mode_line()
            + f"✅ Тестовая оплата Stars прошла успешно.\n\n"
            f"Зачислено: {money(base_total)} {settings.currency_name}\n"
            f"Оплачено: {stars} Telegram Stars\n\n"
            + reaction_url_text()
        )
        await callback.answer()
        return

    if not settings.stars_payments_enabled:
        await callback.answer("Оплата Telegram Stars сейчас выключена.", show_alert=True)
        return
    payment = await create_stars_topup(session, user, base_total, stars)
    await state.update_data(
        total=str(base_total),
        payment_method="stars",
        reaction_stars_payload=payment.payload,
        stars_paid=False,
    )
    await state.set_state(CreateTask.waiting_reaction_stars_payment)
    await callback.message.answer(
        f"🧾 <b>Счёт создан</b>\n\n"
        f"Оплата задания на реакции\n"
        f"ID платежа: {payment.id}\n\n"
        f"Оплатите {stars} Telegram Stars по кнопке ниже."
    )
    await send_stars_invoice(bot, callback.from_user.id, payment)
    await callback.message.edit_text("После оплаты я попрошу ссылку на пост.", reply_markup=reaction_payment_keyboard(money(balance_total), stars, settings.currency_name))
    await callback.answer()


@router.message(CreateTask.waiting_reaction_stars_payment)
async def ad_reaction_waiting_stars(message: Message) -> None:
    await message.answer("Сначала оплатите счёт Telegram Stars. После успешной оплаты я попрошу ссылку на пост.")


@router.message(CreateTask.waiting_reaction_url)
async def ad_reaction_url(message: Message, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    user = await current_user(message, session)
    url = (message.text or "").strip()
    if not url or not is_valid_target(url):
        await message.answer("Ссылка на пост выглядит некорректно. Пришлите ссылку формата https://t.me/username/123 или https://t.me/c/123/456.")
        return
    data = await state.get_data()
    task_type = data["task_type"]
    reward = Decimal(data["reward"])
    total = Decimal(data["total"])
    limit = int(data["limit"])
    await state.update_data(target_url=normalize_target_url(url), target_chat_id=None)
    await message.answer(
        t(
            user.language,
            "ad_preview",
            task_type=TASK_LABELS.get(task_type, task_type),
            title=title_for_task(task_type, url, data.get("meta", {})),
            audience=AUDIENCE_LABELS.get(data.get("audience_type", "all"), data.get("audience_type", "all")),
            reward=money(reward),
            currency_name=settings.currency_name,
            limit=limit,
            total=money(total),
        ),
        reply_markup=confirm_task_keyboard(),
    )


@router.callback_query(F.data.startswith("ad:boost_term:"))
async def ad_boost_term(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(callback, session)
    settings = get_settings()
    days = int(callback.data.split(":")[2])
    price = boost_price(days)
    max_amount = int(user.balance // price) if price > 0 else 0
    await state.update_data(
        task_type=TaskType.BOOST.value,
        audience_type="premium",
        meta={"boost_days": days},
        target_url=f"boost://{days}",
        reward=str(price),
    )
    await state.set_state(CreateTask.waiting_boost_amount)
    await callback.message.edit_text(
        t(
            user.language,
            "ad_boost_amount",
            days=days,
            price=money(price),
            balance=money(user.balance),
            max_amount=max_amount,
            currency_name=settings.currency_name,
        )
    )
    await callback.answer()


@router.message(CreateTask.waiting_boost_amount)
async def ad_boost_amount(message: Message, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    user = await current_user(message, session)
    if not (message.text or "").isdigit():
        await message.answer("Введите целое количество boost-зарядов.")
        return
    amount = int(message.text)
    if amount <= 0:
        await message.answer("Количество должно быть больше нуля.")
        return
    data = await state.get_data()
    reward = Decimal(data["reward"])
    base_total = reward * amount
    balance_total, stars = ad_payment_totals(base_total, settings.currency_per_star)
    await state.update_data(base_total=str(base_total), total=str(balance_total), limit=amount, ad_stars=stars)
    await state.set_state(CreateTask.waiting_boost_link)
    await message.answer(
        boost_target_text(),
    )


@router.message(CreateTask.waiting_boost_link, F.text)
async def ad_boost_link(message: Message, session: AsyncSession, state: FSMContext, bot) -> None:
    settings = get_settings()
    await current_user(message, session)
    boost_url = (message.text or "").strip()
    if boost_url == "Скрыть клавиатуру":
        await message.answer("Клавиатура скрыта. Вы можете продолжить оплату задания.", reply_markup=ReplyKeyboardRemove())
        return
    if not is_valid_boost_url(boost_url):
        await message.answer("Ссылка на Boost выглядит некорректно. Отправьте ссылку вида https://t.me/boost/username.")
        return
    data = await state.get_data()
    meta = data.get("meta", {})
    target_url = normalize_target_url(boost_url)
    target_chat_id = None
    username = boost_username_from_url(target_url)
    if username:
        try:
            chat = await bot.get_chat(f"@{username}")
            target_chat_id = str(chat.id)
            meta["boost_target_title"] = chat.title or username
            meta["boost_target_username"] = username
        except (TelegramBadRequest, TelegramForbiddenError):
            meta["boost_target_username"] = username
    meta["boost_url"] = target_url
    await state.update_data(
        target_url=target_url,
        target_chat_id=target_chat_id,
        meta=meta,
    )
    auto_check_line = (
        "Автопроверка подключена: канал найден."
        if target_chat_id
        else "Автопроверка пока недоступна: добавьте бота администратором в канал, затем создайте задание заново или используйте ручную проверку."
    )
    bot_info = await bot.get_me()
    await message.answer(
        "Boost-ссылка сохранена.\n\n"
        "Убедитесь, что наш бот добавлен администратором в канал. Это понадобится для дальнейшей проверки удержания Boost.\n\n"
        f"{auto_check_line}",
        reply_markup=boost_admin_inline_keyboard(bot_info.username),
    )
    await message.answer(
        ad_payment_text(settings.currency_name),
        reply_markup=ad_payment_keyboard(money(Decimal(data["total"])), int(data["ad_stars"]), settings.currency_name),
    )


@router.message(CreateTask.waiting_boost_link, F.chat_shared)
async def ad_boost_admin_chat_selected(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await current_user(message, session)
    chat_shared = message.chat_shared
    if not chat_shared or chat_shared.request_id not in {REQUEST_BOOST_ADMIN_CHANNEL_ID, REQUEST_BOOST_ADMIN_GROUP_ID}:
        await message.answer("Выберите канал или группу через кнопку добавления бота.")
        return
    data = await state.get_data()
    meta = data.get("meta", {})
    meta["boost_target_title"] = chat_shared.title or meta.get("boost_target_title", "")
    meta["boost_target_username"] = chat_shared.username or meta.get("boost_target_username", "")
    meta["boost_target_type"] = "channel" if chat_shared.request_id == REQUEST_BOOST_ADMIN_CHANNEL_ID else "group"
    await state.update_data(target_chat_id=str(chat_shared.chat_id), meta=meta)
    await message.answer(
        f"Готово. Бот подключён к чату: {escape(chat_shared.title or str(chat_shared.chat_id))}\n\n"
        "Теперь автопроверка Boost будет использовать этот канал/группу.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(CreateTask.waiting_boost_target)
async def ad_boost_target_invalid(message: Message, state: FSMContext) -> None:
    if (message.text or "").endswith("Назад") or (message.text or "") == "Назад":
        await state.clear()
        await message.answer("Выбор отменён.", reply_markup=ReplyKeyboardRemove())
        return
    await message.answer("Отправьте ссылку Boost вида https://t.me/boost/username.")


@router.callback_query(F.data == "ad:auto")
async def ad_auto(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    await callback.message.edit_text(t(user.language, "ad_auto"), reply_markup=auto_tasks_keyboard())
    await callback.answer()


@router.callback_query(F.data == "ad:auto_add")
async def ad_auto_add(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    await callback.answer(t(user.language, "ad_auto_add"), show_alert=True)


@router.callback_query((F.data == "ad:mine") | F.data.startswith("ad:mine:"))
async def ad_mine(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    parts = callback.data.split(":")
    source = parts[2] if len(parts) > 2 and parts[2] in {"profile", "ads"} else "ads"
    tab = parts[3] if len(parts) > 3 and parts[3] in {"active", "all", "archive", "paused"} else "active"
    page = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 1
    tasks = await list_created_by_user(session, user)
    pending = await creator_pending_completions(session, user)
    counts = {
        "active": sum(item.status == TaskStatus.ACTIVE.value for item in tasks),
        "moderation": sum(item.status == TaskStatus.MODERATION.value for item in tasks),
        "completed": sum(item.status == TaskStatus.COMPLETED.value for item in tasks),
        "paused": sum(item.status == TaskStatus.PAUSED.value for item in tasks),
        "pending": len(pending),
    }
    tab_filters = {
        "active": {TaskStatus.ACTIVE.value, TaskStatus.MODERATION.value},
        "archive": {TaskStatus.COMPLETED.value},
        "paused": {TaskStatus.PAUSED.value, TaskStatus.REJECTED.value},
    }
    if tab == "all":
        visible_tasks = tasks
    else:
        visible_tasks = [item for item in tasks if item.status in tab_filters[tab]]
    pages = max(1, (len(visible_tasks) + MY_TASKS_PER_PAGE - 1) // MY_TASKS_PER_PAGE)
    page = min(max(1, page), pages)
    page_tasks = visible_tasks[(page - 1) * MY_TASKS_PER_PAGE : page * MY_TASKS_PER_PAGE]
    tab_title = {
        "active": "Активные и на модерации",
        "all": "Все задания",
        "archive": "Архив",
        "paused": "Остановленные и отклонённые",
    }[tab]
    items = tree_list(
        [
            f"#{item.id} {TASK_LABELS.get(item.type, item.type)} · {status_label(item.status)} · {item.completed_count}/{item.total_limit}"
            for item in page_tasks
        ]
    ) or t(user.language, "ad_mine_empty")
    await replace_task_message(
        callback.message,
        t(user.language, "ad_mine", **counts, items=f"<b>{tab_title}</b>\n{items}\n\nСтраница {page}/{pages}"),
        reply_markup=my_tasks_keyboard([item.id for item in page_tasks], source, tab, page, pages),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ad:archive:"))
async def ad_archive(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    parts = callback.data.split(":")
    source = parts[2] if len(parts) > 2 and parts[2] in {"profile", "ads"} else "ads"
    tasks = [item for item in await list_created_by_user(session, user) if item.status == TaskStatus.COMPLETED.value]
    items = tree_list(
        [
            f"#{item.id} {TASK_LABELS.get(item.type, item.type)} · {item.completed_count}/{item.total_limit}"
            for item in tasks[:10]
        ]
    ) or "В архиве пока нет заданий."
    await replace_task_message(
        callback.message,
        f"🗂 <b>Архив заданий</b>\n\n{items}\n\nЗдесь хранятся задания, которые вы архивировали или завершили.",
        reply_markup=archived_tasks_keyboard([item.id for item in tasks[:10]], source),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ad:task:"))
async def ad_task_detail(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    parts = callback.data.split(":")
    task_id = int(parts[2])
    source = parts[3] if len(parts) > 3 and parts[3] in {"profile", "ads"} else "ads"
    task = await session.get(Task, task_id)
    if not task or task.creator_id != user.id:
        await callback.answer("Задание не найдено.", show_alert=True)
        return
    text = (
        f"Задание #{task.id}\n"
        f"{task.title}\n\n"
        + tree_list(
            [
                f"Тип: {TASK_LABELS.get(task.type, task.type)}",
                f"Состояние: {status_label(task.status)}",
                f"Выполнено: {task.completed_count}/{task.total_limit}",
                f"Награда: {money(task.reward)}",
            ]
        )
    )
    await safe_edit_text(callback.message, text, reply_markup=my_task_detail_keyboard(task.id, task.status, source))
    await callback.answer()


@router.callback_query(F.data.startswith("ad:task_pause:"))
async def ad_task_pause(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    parts = callback.data.split(":")
    task_id = int(parts[2])
    source = parts[3] if len(parts) > 3 and parts[3] in {"profile", "ads"} else "ads"
    task = await session.get(Task, task_id)
    if not task or task.creator_id != user.id:
        await callback.answer("Задание не найдено.", show_alert=True)
        return
    paid_count, paid_total, refund = await cancel_task_money(session, task)
    task.status = TaskStatus.PAUSED.value
    text = f"Задание #{task.id} остановлено."
    text += cancellation_summary(paid_count, paid_total, refund)
    await safe_edit_text(callback.message, text, reply_markup=my_tasks_keyboard(source=source))
    await callback.answer()


@router.callback_query(F.data.startswith("ad:task_archive:"))
async def ad_task_archive(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    parts = callback.data.split(":")
    task_id = int(parts[2])
    source = parts[3] if len(parts) > 3 and parts[3] in {"profile", "ads"} else "ads"
    task = await session.get(Task, task_id)
    if not task or task.creator_id != user.id:
        await callback.answer("Задание не найдено.", show_alert=True)
        return
    paid_count, paid_total, refund = await cancel_task_money(session, task)
    task.status = TaskStatus.COMPLETED.value
    text = f"Задание #{task.id} перенесено в архив."
    text += cancellation_summary(paid_count, paid_total, refund)
    await safe_edit_text(callback.message, text, reply_markup=my_tasks_keyboard(source=source))
    await callback.answer()


@router.callback_query(F.data.startswith("ad:task_delete:"))
async def ad_task_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    parts = callback.data.split(":")
    task_id = int(parts[2])
    source = parts[3] if len(parts) > 3 and parts[3] in {"profile", "ads"} else "ads"
    task = await session.get(Task, task_id)
    if not task or task.creator_id != user.id:
        await callback.answer("Задание не найдено.", show_alert=True)
        return
    paid_count, paid_total, refund = await delete_task_permanently(session, task)
    text = f"Задание #{task_id} удалено окончательно."
    text += cancellation_summary(paid_count, paid_total, refund)
    await safe_edit_text(callback.message, text, reply_markup=my_tasks_keyboard(source=source))
    await callback.answer()


@router.callback_query(F.data.startswith("ad:delete_all_confirm:"))
async def ad_delete_all_confirm(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    source = parts[2] if len(parts) > 2 and parts[2] in {"profile", "ads"} else "ads"
    await safe_edit_text(
        callback.message,
        "Удалить все ваши задания окончательно?\n\n"
        "Перед удалением все активные заявки на проверку будут автоматически оплачены исполнителям.\n"
        "За неиспользованный остаток вернётся 85% суммы, комиссия отмены составит 15%.",
        reply_markup=delete_all_tasks_confirm_keyboard(source),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ad:delete_all:"))
async def ad_delete_all(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    parts = callback.data.split(":")
    source = parts[2] if len(parts) > 2 and parts[2] in {"profile", "ads"} else "ads"
    tasks = await list_created_by_user(session, user)
    paid_count = 0
    paid_total = Decimal("0")
    refund_total = Decimal("0")
    deleted_count = len(tasks)
    for task in tasks:
        count, total, refund = await delete_task_permanently(session, task)
        paid_count += count
        paid_total += total
        refund_total += refund
    text = f"Удалено заданий: {deleted_count}."
    text += cancellation_summary(paid_count, paid_total, refund_total)
    await safe_edit_text(callback.message, text, reply_markup=my_tasks_keyboard(source=source))
    await callback.answer()


@router.callback_query(F.data.startswith("ad:mine_review:"))
async def ad_mine_review(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    parts = callback.data.split(":")
    task_type = parts[2]
    source = parts[3] if len(parts) > 3 and parts[3] in {"profile", "ads"} else "ads"
    pending = await creator_pending_completions(session, user)
    related = []
    related_proofs = []
    for completion in pending:
        task = await session.get(Task, completion.task_id)
        if task and task.type == task_type:
            related_proofs.append(completion)
            related.append(f"Заявка #{completion.id} к заданию #{task.id}: {money(completion.reward)} {get_settings().currency_name}")
    if related:
        text = (
            "🧾 <b>Заявки на проверку</b>\n\n"
            + tree_list(
                [
                    f"Тип: {TASK_LABELS.get(task_type, task_type)}",
                    f"Ожидают решения: {len(related_proofs)}",
                ]
            )
            + "\n\n<b>Список заявок:</b>\n"
            + tree_list(related)
            + "\n\nОткройте заявку, проверьте скриншот и примите решение."
        )
    else:
        text = (
            "🧾 <b>Заявки на проверку</b>\n\n"
            f"По типу «{TASK_LABELS.get(task_type, task_type)}» сейчас нет заявок, ожидающих вашего решения."
        )
    proof_ids = [completion.id for completion in related_proofs]
    await replace_task_message(callback.message, text, reply_markup=owner_proofs_keyboard(proof_ids, task_type, source))
    await callback.answer()


@router.callback_query(F.data.startswith("ad:proof:"))
async def ad_owner_proof_card(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    _, _, proof_id_raw, _task_type, source = callback.data.split(":")
    proof = await session.get(TaskCompletion, int(proof_id_raw))
    if not proof:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return
    task = await session.get(Task, proof.task_id)
    if not task or task.creator_id != user.id:
        await callback.answer("Это не ваша заявка.", show_alert=True)
        return
    await show_owner_proof(callback, proof, task, source if source in {"profile", "ads"} else "ads")
    await callback.answer()


@router.callback_query(F.data.startswith("ad:proof_"))
async def ad_owner_proof_moderate(callback: CallbackQuery, session: AsyncSession, bot) -> None:
    user = await current_user(callback, session)
    action, proof_id_raw, source = callback.data.removeprefix("ad:proof_").split(":")
    proof = await session.get(TaskCompletion, int(proof_id_raw))
    if not proof or proof.status != CompletionStatus.PENDING.value:
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return
    task = await session.get(Task, proof.task_id)
    if not task or task.creator_id != user.id:
        await callback.answer("Это не ваша заявка.", show_alert=True)
        return

    settings = get_settings()
    if action == "approve":
        hold_until = parse_datetime(proof.checked_at) if task.type == TaskType.BOOST.value else None
        if hold_until and datetime.utcnow() < hold_until:
            await callback.answer(
                f"Boost ещё должен удерживаться до {hold_until.strftime('%d.%m.%Y %H:%M')}.",
                show_alert=True,
            )
            return
        if task.type == TaskType.BOOST.value and task.target_chat_id:
            performer = await session.get(User, proof.user_id)
            has_boost = await user_has_active_boost(bot, task, performer) if performer else None
            if has_boost is False:
                await callback.answer("Активный Boost от исполнителя не найден.", show_alert=True)
                return
            if has_boost is None:
                await callback.answer("Не удалось проверить Boost. Проверьте, что бот является администратором канала.", show_alert=True)
                return
        proof.status = CompletionStatus.PAID.value
        await add_balance(session, proof.user_id, proof.reward)
        task.completed_count += 1
        if task.completed_count >= task.total_limit:
            task.status = TaskStatus.COMPLETED.value
        text = f"Заявка #{proof.id} принята. Исполнителю начислено {money(proof.reward)} {settings.currency_name}."
    else:
        proof.status = CompletionStatus.REJECTED.value
        text = f"Заявка #{proof.id} отклонена. Награда исполнителю не начислена."

    if callback.message.photo:
        await callback.message.edit_caption(caption=text)
    else:
        await safe_edit_text(callback.message, text)
    await callback.answer()


@router.callback_query(F.data == "ad:create_channel")
async def create_channel_task(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(task_type=TaskType.CHANNEL.value)
    await callback.message.edit_text("Продвижение канала", reply_markup=audience_keyboard(TaskType.CHANNEL.value))
    await callback.answer()


@router.callback_query(F.data == "ad:create_manual")
async def create_manual_task(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(task_type=TaskType.BOT.value)
    await callback.message.edit_text("Продвижение бота", reply_markup=bot_format_keyboard())
    await callback.answer()


@router.message(CreateTask.waiting_url)
async def task_url(message: Message, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    user = await current_user(message, session)
    parts = (message.text or "").split()
    if not parts or not is_valid_target(parts[0]):
        await message.answer("Ссылка выглядит некорректно. Пришлите URL или username, который начинается с @.")
        return
    await state.update_data(target_url=normalize_target_url(parts[0]), target_chat_id=parts[1] if len(parts) > 1 else None)
    data = await state.get_data()
    minimum = min_task_reward(data.get("task_type", ""), data.get("audience_type"), data.get("meta", {}))
    min_line = f"\nМинимальная цена: {money(minimum)} {settings.currency_name}" if minimum > 0 else ""
    await state.set_state(CreateTask.waiting_reward)
    await message.answer(t(user.language, "ad_send_reward", currency_name=settings.currency_name, min_line=min_line))


@router.message(CreateTask.waiting_reward)
async def task_reward(message: Message, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    user = await current_user(message, session)
    value = (message.text or "").replace(",", ".").strip()
    try:
        reward = Decimal(value)
    except InvalidOperation:
        await message.answer(t(user.language, "ad_bad_reward"))
        return
    if not reward.is_finite() or reward <= 0:
        await message.answer(t(user.language, "ad_bad_reward"))
        return
    try:
        reward = reward.quantize(Decimal("0.01"))
    except InvalidOperation:
        await message.answer(t(user.language, "ad_bad_reward"))
        return
    data = await state.get_data()
    minimum = min_task_reward(data.get("task_type", ""), data.get("audience_type"), data.get("meta", {}))
    if minimum > 0 and reward < minimum:
        await message.answer(
            t(
                user.language,
                "ad_reward_too_low",
                min_reward=money(minimum),
                currency_name=settings.currency_name,
            )
        )
        return
    await state.update_data(reward=str(reward))
    await state.set_state(CreateTask.waiting_limit)
    await message.answer(t(user.language, "ad_send_limit", reward=money(reward), currency_name=settings.currency_name))


@router.message(CreateTask.waiting_limit)
async def task_limit(message: Message, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    await current_user(message, session)
    if not (message.text or "").isdigit():
        await message.answer("Введите целое число.")
        return
    limit = int(message.text)
    data = await state.get_data()
    task_type = data["task_type"]
    reward = Decimal(data["reward"])
    base_total = reward * limit
    balance_total, stars = ad_payment_totals(base_total, settings.currency_per_star)
    await state.update_data(reward=str(reward), base_total=str(base_total), total=str(balance_total), limit=limit, ad_stars=stars)
    await message.answer(
        ad_payment_text(settings.currency_name),
        reply_markup=ad_payment_keyboard(money(balance_total), stars, settings.currency_name),
    )


async def send_ad_preview(message: Message, user: User, data: dict, settings, reply_markup=None) -> None:
    task_type = data["task_type"]
    await message.answer(
        t(
            user.language,
            "ad_preview",
            task_type=TASK_LABELS.get(task_type, task_type),
            title=title_for_task(task_type, data["target_url"], data.get("meta", {})),
            audience=AUDIENCE_LABELS.get(data.get("audience_type", "all"), data.get("audience_type", "all")),
            reward=money(Decimal(data["reward"])),
            currency_name=settings.currency_name,
            limit=int(data["limit"]),
            total=money(Decimal(data["total"])),
        ),
        reply_markup=reply_markup or confirm_task_keyboard(),
    )


@router.callback_query(F.data.startswith("ad:pay:"))
async def ad_pay(callback: CallbackQuery, session: AsyncSession, state: FSMContext, bot) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    method = callback.data.split(":")[2]
    data = await state.get_data()
    if not data.get("base_total") or not data.get("limit") or not data.get("reward"):
        await callback.answer("Расчёт задания не найден. Начните заново.", show_alert=True)
        await state.clear()
        return
    base_total = Decimal(data["base_total"])
    balance_total = Decimal(data["total"])
    stars = int(data["ad_stars"])
    if method == "balance":
        if user.balance < balance_total:
            await callback.answer(
                f"Недостаточно средств. Нужно {money(balance_total)} {settings.currency_name}.",
                show_alert=True,
            )
            return
        await state.update_data(total=str(balance_total), payment_method="balance", stars_paid=False)
        if data.get("task_type") == TaskType.VIEW.value and not data.get("target_url"):
            await state.set_state(CreateTask.waiting_view_url)
            await callback.message.edit_text("Отправьте ссылку на пост, для которого нужно запустить просмотры.")
            await callback.answer()
            return
        await callback.message.edit_text("Расчёт готов. Проверьте данные перед запуском.")
        data = await state.get_data()
        await send_ad_preview(callback.message, user, data, settings)
        await callback.answer()
        return

    if is_test_mode():
        payment = await create_stars_topup(session, user, base_total, stars)
        await complete_stars_payment(session, user.telegram_id, payment.payload or "", stars, f"test-charge-{payment.id}", "mock", is_test=True)
        await state.update_data(total=str(base_total), payment_method="stars", ad_stars_payload=payment.payload, stars_paid=True)
        if data.get("task_type") == TaskType.VIEW.value and not data.get("target_url"):
            await state.set_state(CreateTask.waiting_view_url)
            await callback.message.edit_text(
                test_mode_line()
                + f"✅ Тестовая оплата Stars прошла успешно.\n\n"
                f"Зачислено: {money(base_total)} {settings.currency_name}\n"
                f"Оплачено: {stars} Telegram Stars\n\n"
                "Отправьте ссылку на пост, для которого нужно запустить просмотры."
            )
            await callback.answer()
            return
        await callback.message.edit_text(
            test_mode_line()
            + f"✅ Тестовая оплата Stars прошла успешно.\n\n"
            f"Зачислено: {money(base_total)} {settings.currency_name}\n"
            f"Оплачено: {stars} Telegram Stars"
        )
        data = await state.get_data()
        await send_ad_preview(callback.message, user, data, settings)
        await callback.answer()
        return

    if not settings.stars_payments_enabled:
        await callback.answer("Оплата Telegram Stars сейчас выключена.", show_alert=True)
        return
    payment = await create_stars_topup(session, user, base_total, stars)
    await state.update_data(
        total=str(base_total),
        payment_method="stars",
        ad_stars_payload=payment.payload,
        stars_paid=False,
    )
    await state.set_state(CreateTask.waiting_ad_stars_payment)
    await callback.message.answer(
        f"🧾 <b>Счёт создан</b>\n\n"
        f"Оплата за создание задания\n"
        f"ID платежа: {payment.id}\n\n"
        f"Оплатите {stars} Telegram Stars по кнопке ниже."
    )
    await send_stars_invoice(bot, callback.from_user.id, payment)
    await callback.message.edit_text("После оплаты я покажу финальный предпросмотр задания.")
    await callback.answer()


@router.message(CreateTask.waiting_ad_stars_payment)
async def ad_waiting_stars_payment(message: Message) -> None:
    await message.answer("Сначала оплатите счёт Telegram Stars. После успешной оплаты я покажу предпросмотр задания.")


@router.message(CreateTask.waiting_view_url)
async def ad_view_url(message: Message, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    user = await current_user(message, session)
    url = (message.text or "").strip()
    if not url or not is_valid_target(url):
        await message.answer("Ссылка на пост выглядит некорректно. Пришлите ссылку формата https://t.me/username/123 или https://t.me/c/123/456.")
        return
    await state.update_data(target_url=normalize_target_url(url), target_chat_id=None)
    data = await state.get_data()
    await send_ad_preview(message, user, data, settings)


@router.callback_query(F.data == "ad:confirm")
async def task_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    data = await state.get_data()
    if not data.get("target_url") or not data.get("limit") or not data.get("reward"):
        await callback.answer("Черновик задания не найден. Начните заново.", show_alert=True)
        await state.clear()
        return
    reward = Decimal(data["reward"])
    total = Decimal(data["total"])
    if data.get("payment_method") == "stars" and not data.get("stars_paid"):
        await callback.answer("Сначала оплатите счёт Telegram Stars.", show_alert=True)
        return
    if not await charge_balance(session, user, total):
        await callback.answer(f"Недостаточно средств. Нужно {money(total)} {settings.currency_name}.", show_alert=True)
        await state.clear()
        return
    task_type = TaskType(data["task_type"])
    meta = data.get("meta", {})
    task = await create_task(
        session,
        user,
        task_type,
        data["target_url"],
        data.get("target_chat_id"),
        title_for_task(task_type.value, data["target_url"], meta),
        reward,
        int(data["limit"]),
        audience_type=data.get("audience_type", "all"),
        filters_json=json.dumps({"filters": data.get("filters", {}), "meta": meta}, ensure_ascii=False),
        description=description_for_task(task_type.value, meta),
        status=TaskStatus.ACTIVE,
    )
    await callback.message.edit_text(
        t(user.language, "ad_created", task_id=task.id, total=money(total), currency_name=settings.currency_name),
        reply_markup=advertise_keyboard(),
    )
    await callback.answer()
    await state.clear()
