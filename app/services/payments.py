from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from aiogram import Bot
from aiogram.types import LabeledPrice
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.finance import Payment
from app.models.user import User
from app.repositories.finance import create_sandbox_payment, create_stars_payment, get_payment_by_payload, get_payment_by_telegram_charge


@dataclass
class PaymentCompleteResult:
    payment: Payment | None
    status: str
    message: str
    credited: bool = False

    @property
    def currency_amount(self) -> Decimal:
        return self.payment.amount_internal if self.payment else Decimal("0")

    @property
    def stars_amount(self) -> int:
        return self.payment.stars_amount if self.payment else 0


class MockPaymentProvider:
    provider_name = "mock"

    async def create_payment(self, session: AsyncSession, user: User, amount: Decimal, status: str = "paid"):
        return await create_sandbox_payment(
            session,
            user,
            amount,
            provider=self.provider_name,
            status=status,
            is_test=True,
        )


def should_use_mock_payments() -> bool:
    settings = get_settings()
    return settings.test_mode and settings.payments_provider.lower() == "mock"


def currency_for_stars(stars_amount: int) -> Decimal:
    return Decimal(stars_amount * get_settings().currency_per_star)


async def top_up_sandbox(session: AsyncSession, user: User, amount: Decimal, status: str = "paid"):
    settings = get_settings()
    if should_use_mock_payments():
        return await MockPaymentProvider().create_payment(session, user, amount, status=status)
    return await create_sandbox_payment(
        session,
        user,
        amount,
        provider=settings.payments_provider or "sandbox",
        status=status,
        is_test=False,
    )


async def create_stars_topup(session: AsyncSession, user: User, currency_amount: Decimal, stars_amount: int) -> Payment:
    settings = get_settings()
    return await create_stars_payment(session, user, currency_amount, stars_amount, settings.currency_name, is_test=settings.test_mode)


async def send_stars_invoice(bot: Bot, chat_id: int, payment: Payment) -> None:
    settings = get_settings()
    amount_text = f"{int(payment.amount_internal):,}".replace(",", " ")
    await bot.send_invoice(
        chat_id=chat_id,
        title=f"Пополнение на {amount_text} {settings.currency_name}",
        description=f"Пополнение баланса в {settings.project_name} на {amount_text} {settings.currency_name}",
        payload=payment.payload or str(payment.id),
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{amount_text} {settings.currency_name}", amount=payment.stars_amount)],
    )


async def validate_pre_checkout(session: AsyncSession, telegram_id: int, payload: str, currency: str, total_amount: int) -> tuple[bool, str]:
    payment = await get_payment_by_payload(session, payload)
    if not payment:
        return False, "Платеж не найден. Создайте счет заново."
    if payment.status not in {"created", "pending"}:
        return False, "Этот счет уже обработан."
    if currency != "XTR" or payment.payment_currency != "XTR":
        return False, "Некорректная валюта платежа."
    if payment.stars_amount != total_amount:
        return False, "Сумма Stars не совпадает со счетом."
    user = await session.get(User, payment.user_id)
    if not user or user.telegram_id != telegram_id:
        return False, "Этот счет создан для другого пользователя."
    payment.status = "pending"
    await session.flush()
    return True, ""


async def complete_stars_payment(
    session: AsyncSession,
    telegram_id: int,
    payload: str,
    paid_stars: int,
    telegram_payment_charge_id: str | None,
    provider_payment_charge_id: str | None = None,
    is_test: bool = False,
) -> PaymentCompleteResult:
    payment = await get_payment_by_payload(session, payload)
    if not payment:
        return PaymentCompleteResult(None, "not_found", "Платеж не найден.")

    user = await session.get(User, payment.user_id)
    if not user or user.telegram_id != telegram_id:
        return PaymentCompleteResult(payment, "wrong_user", "Платеж создан для другого пользователя.")

    if payment.status == "paid":
        return PaymentCompleteResult(payment, "already_paid", "Платеж уже был обработан.")

    if telegram_payment_charge_id:
        charged_payment = await get_payment_by_telegram_charge(session, telegram_payment_charge_id)
        if charged_payment and charged_payment.id != payment.id:
            return PaymentCompleteResult(charged_payment, "duplicate_charge", "Этот платеж уже был обработан.")

    if payment.payment_currency != "XTR":
        return PaymentCompleteResult(payment, "wrong_currency", "Некорректная валюта платежа.")
    if payment.stars_amount != paid_stars:
        return PaymentCompleteResult(payment, "wrong_amount", "Сумма Stars не совпадает со счетом.")

    payment.status = "paid"
    payment.telegram_payment_charge_id = telegram_payment_charge_id
    payment.provider_payment_charge_id = provider_payment_charge_id
    payment.paid_at = datetime.utcnow().isoformat(timespec="seconds")
    payment.is_test = payment.is_test or is_test
    user.balance += payment.amount_internal
    user.xp += max(1, int(payment.amount_internal // Decimal("10000")))
    await session.flush()
    return PaymentCompleteResult(payment, "paid", "Платеж успешно обработан.", credited=True)


async def fail_stars_payment(session: AsyncSession, payment: Payment) -> Payment:
    payment.status = "failed"
    await session.flush()
    return payment


async def refund_stars_payment(bot: Bot, session: AsyncSession, payment: Payment) -> tuple[bool, str]:
    if payment.status != "paid":
        return False, "Возврат доступен только для успешного платежа."
    if payment.payment_currency != "XTR" or not payment.telegram_payment_charge_id:
        return False, "У платежа нет Telegram Stars charge ID."
    user = await session.get(User, payment.user_id)
    if not user:
        return False, "Пользователь не найден."
    await bot.refund_star_payment(user_id=user.telegram_id, telegram_payment_charge_id=payment.telegram_payment_charge_id)
    user.balance -= payment.amount_internal
    payment.status = "refunded"
    await session.flush()
    return True, "Stars возвращены пользователю, внутренняя валюта списана."
