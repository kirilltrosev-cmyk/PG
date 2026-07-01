from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.finance import activate_check, create_check
from app.states import ActivateCheck, CreateCheck
from app.texts import t
from app.utils.users import current_user

router = Router()


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
