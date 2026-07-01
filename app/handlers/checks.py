from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.common import check_detail_keyboard, check_list_keyboard, checks_keyboard
from app.models.finance import Check
from app.repositories.finance import activate_check, create_check, get_user_check, list_user_checks
from app.states import ActivateCheck, CreateCheck
from app.texts import t
from app.utils.formatting import money
from app.utils.users import current_user

router = Router()


def check_status_label(check: Check) -> str:
    if check.status == "active":
        return "активен"
    if check.status == "closed":
        return "закрыт"
    return check.status


def check_stats_text(check: Check, bot_username: str) -> str:
    left = max(check.activations_limit - check.activations_count, 0)
    link = f"https://t.me/{bot_username}?start=check_{check.token}"
    created = check.created_at or "не указано"
    settings = get_settings()
    return (
        f"🧾 <b>Чек #{check.id}</b>\n\n"
        f"├ Статус: {check_status_label(check)}\n"
        f"├ Сумма за активацию: {money(check.amount_per_user)} {settings.currency_name}\n"
        f"├ Всего активаций: {check.activations_limit}\n"
        f"├ Активировали: {check.activations_count}\n"
        f"├ Осталось: {left}\n"
        f"├ Зарезервировано всего: {money(check.amount_total)} {settings.currency_name}\n"
        f"└ Создан: {created}\n\n"
        f"Ссылка:\n{link}"
    )


@router.callback_query(F.data == "menu:checks")
async def checks_main(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    await callback.message.edit_text(t(user.language, "checks"), reply_markup=checks_keyboard())
    await callback.answer()


@router.callback_query(F.data == "check:list")
async def check_list(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    checks = await list_user_checks(session, user)
    if not checks:
        await callback.message.edit_text(
            "У вас пока нет созданных чеков.",
            reply_markup=checks_keyboard(),
        )
        await callback.answer()
        return
    lines = []
    for check in checks:
        left = max(check.activations_limit - check.activations_count, 0)
        lines.append(
            f"#{check.id} · {check_status_label(check)} · "
            f"{check.activations_count}/{check.activations_limit} активировано · осталось {left}"
        )
    await callback.message.edit_text(
        "🧾 <b>Мои чеки</b>\n\n" + "\n".join(lines),
        reply_markup=check_list_keyboard(checks),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("check:view:"))
async def check_detail(callback: CallbackQuery, session: AsyncSession, bot) -> None:
    user = await current_user(callback, session)
    check_id = int(callback.data.rsplit(":", 1)[-1])
    check = await get_user_check(session, user, check_id)
    if not check:
        await callback.answer("Чек не найден.", show_alert=True)
        return
    me = await bot.get_me()
    await callback.message.edit_text(
        check_stats_text(check, me.username),
        reply_markup=check_detail_keyboard(check.id),
    )
    await callback.answer()


@router.callback_query(F.data == "check:create")
async def start_create_check(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreateCheck.waiting_amount)
    await callback.message.answer("Сколько начислять за одну активацию?")
    await callback.answer()


@router.message(CreateCheck.waiting_amount)
async def check_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = Decimal((message.text or "").replace(",", "."))
    except InvalidOperation:
        await message.answer("Введите число.")
        return
    await state.update_data(amount=str(amount))
    await state.set_state(CreateCheck.waiting_limit)
    await message.answer("Сколько активаций разрешить?")


@router.message(CreateCheck.waiting_limit)
async def check_limit(message: Message, session: AsyncSession, state: FSMContext, bot) -> None:
    if not (message.text or "").isdigit():
        await message.answer("Введите целое число.")
        return
    user = await current_user(message, session)
    data = await state.get_data()
    check = await create_check(session, user, Decimal(data["amount"]), int(message.text))
    if not check:
        await message.answer("Недостаточно баланса для такого чека.")
    else:
        me = await bot.get_me()
        await message.answer(t(user.language, "check_created", bot_username=me.username, token=check.token))
        await message.answer(check_stats_text(check, me.username), reply_markup=check_detail_keyboard(check.id))
    await state.clear()


@router.callback_query(F.data == "check:activate")
async def ask_check_token(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ActivateCheck.waiting_token)
    await callback.message.answer("Пришлите токен или полную ссылку чека.")
    await callback.answer()


@router.message(ActivateCheck.waiting_token)
async def activate_token(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await current_user(message, session)
    token = (message.text or "").split("check_")[-1].strip()
    status = await activate_check(session, token, user)
    await message.answer(t(user.language, "check_activated" if status == "ok" else "check_bad"))
    await state.clear()
