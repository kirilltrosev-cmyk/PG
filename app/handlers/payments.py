from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.common import confirm_task_keyboard
from app.models.enums import TaskType
from app.services.payments import complete_stars_payment, validate_pre_checkout
from app.states import CreateTask
from app.utils.formatting import money

router = Router()


@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, session: AsyncSession) -> None:
    ok, error = await validate_pre_checkout(
        session,
        pre_checkout_query.from_user.id,
        pre_checkout_query.invoice_payload,
        pre_checkout_query.currency,
        pre_checkout_query.total_amount,
    )
    await pre_checkout_query.answer(ok=ok, error_message=error or None)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not message.from_user or not message.successful_payment:
        return
    successful_payment = message.successful_payment
    if successful_payment.currency != "XTR":
        return

    result = await complete_stars_payment(
        session=session,
        telegram_id=message.from_user.id,
        payload=successful_payment.invoice_payload,
        paid_stars=successful_payment.total_amount,
        telegram_payment_charge_id=successful_payment.telegram_payment_charge_id,
        provider_payment_charge_id=successful_payment.provider_payment_charge_id,
    )
    settings = get_settings()
    if result.status in {"paid", "already_paid"} and result.payment:
        await message.answer(
            f"✅ <b>Оплата получена!</b>\n\n"
            f"Баланс пополнен на {money(result.currency_amount)} {settings.currency_name}.\n"
            f"Оплачено: {result.stars_amount} ⭐"
        )
        data = await state.get_data()
        if data.get("reaction_stars_payload") == successful_payment.invoice_payload:
            await state.update_data(stars_paid=True)
            await state.set_state(CreateTask.waiting_reaction_url)
            await message.answer(
                "Теперь отправьте ссылку на пост, где нужно поставить реакцию.\n\n"
                "Подойдут форматы:\n"
                "https://t.me/username/123\n"
                "https://t.me/c/123/456\n"
                "https://t.me/c/1234567890/123/123"
            )
        elif data.get("ad_stars_payload") == successful_payment.invoice_payload:
            await state.update_data(stars_paid=True)
            if data.get("task_type") == TaskType.VIEW.value and not data.get("target_url"):
                await state.set_state(CreateTask.waiting_view_url)
                await message.answer("Оплата за просмотры получена. Теперь отправьте ссылку на пост.")
                return
            await message.answer(
                "Оплата задания получена. Проверьте черновик и запустите размещение.",
                reply_markup=confirm_task_keyboard(),
            )
    else:
        await message.answer(f"❌ Оплата получена, но не была начислена: {result.message}")
