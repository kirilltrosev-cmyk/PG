from datetime import datetime
from decimal import Decimal
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Check, CheckActivation, Payment
from app.models.user import User


async def create_sandbox_payment(
    session: AsyncSession,
    user: User,
    amount: Decimal,
    *,
    provider: str = "sandbox",
    status: str = "paid",
    is_test: bool = False,
) -> Payment:
    payment = Payment(
        user_id=user.id,
        provider=provider,
        type="sandbox_topup",
        amount_internal=amount,
        currency_name=None,
        status=status,
        provider_payment_id=f"{provider}-{token_urlsafe(8)}",
        paid_at=datetime.utcnow().isoformat(timespec="seconds") if status == "paid" else None,
        is_test=is_test,
    )
    if status == "paid":
        user.balance += amount
        user.xp += max(1, int(amount // Decimal("10000")))
    session.add(payment)
    await session.flush()
    return payment


async def create_stars_payment(session: AsyncSession, user: User, currency_amount: Decimal, stars_amount: int, currency_name: str, is_test: bool = False) -> Payment:
    payment = Payment(
        user_id=user.id,
        type="stars_topup",
        provider="mock" if is_test else "telegram_stars",
        amount_money=Decimal(stars_amount),
        amount_currency="XTR",
        amount_internal=currency_amount,
        currency_name=currency_name,
        stars_amount=stars_amount,
        payment_currency="XTR",
        status="created",
        is_test=is_test,
    )
    session.add(payment)
    await session.flush()
    payment.payload = f"stars_{payment.id}_{token_urlsafe(8)}"
    payment.provider_payment_id = payment.payload
    await session.flush()
    return payment


async def get_payment_by_payload(session: AsyncSession, payload: str) -> Payment | None:
    return await session.scalar(select(Payment).where(Payment.payload == payload))


async def get_payment_by_telegram_charge(session: AsyncSession, charge_id: str) -> Payment | None:
    return await session.scalar(select(Payment).where(Payment.telegram_payment_charge_id == charge_id))


async def create_check(session: AsyncSession, user: User, amount_per_user: Decimal, limit: int) -> Check | None:
    total = amount_per_user * limit
    if user.balance < total:
        return None
    user.balance -= total
    check = Check(
        creator_id=user.id,
        token=token_urlsafe(10),
        amount_total=total,
        amount_per_user=amount_per_user,
        activations_limit=limit,
    )
    session.add(check)
    await session.flush()
    return check


async def activate_check(session: AsyncSession, token: str, user: User) -> str:
    result = await session.execute(select(Check).where(Check.token == token))
    check = result.scalar_one_or_none()
    if not check or check.status != "active":
        return "not_found"
    exists = await session.execute(
        select(CheckActivation).where(CheckActivation.check_id == check.id, CheckActivation.user_id == user.id)
    )
    if exists.scalar_one_or_none():
        return "already"
    if check.activations_count >= check.activations_limit:
        check.status = "closed"
        return "closed"
    check.activations_count += 1
    user.balance += check.amount_per_user
    session.add(CheckActivation(check_id=check.id, user_id=user.id, amount=check.amount_per_user))
    if check.activations_count >= check.activations_limit:
        check.status = "closed"
    await session.flush()
    return "ok"
