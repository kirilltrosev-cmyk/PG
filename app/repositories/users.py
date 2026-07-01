from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import Referral
from app.models.user import User


async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def ensure_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    admin_ids: set[int],
    is_premium: bool = False,
    referrer_telegram_id: int | None = None,
    referral_bonus: int = 0,
) -> User:
    user = await get_by_telegram_id(session, telegram_id)
    if user:
        user.username = username
        user.first_name = first_name
        user.is_admin = telegram_id in admin_ids
        user.is_premium = is_premium
        await session.flush()
        return user

    referrer = None
    if referrer_telegram_id and referrer_telegram_id != telegram_id:
        referrer = await get_by_telegram_id(session, referrer_telegram_id)

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        referrer_id=referrer.id if referrer else None,
        is_admin=telegram_id in admin_ids,
        is_premium=is_premium,
    )
    session.add(user)
    await session.flush()

    if referrer and referral_bonus > 0:
        referrer.balance += Decimal(referral_bonus)
        session.add(Referral(referrer_id=referrer.id, referred_id=user.id, source="start", bonus_amount=referral_bonus))
    await session.flush()
    return user


async def add_balance(session: AsyncSession, user_id: int, amount: Decimal | int | float) -> None:
    user = await session.get(User, user_id)
    if user:
        user.balance += Decimal(str(amount))
        user.xp += int(Decimal(str(amount)))
        user.level = max(1, user.xp // 100 + 1)


async def charge_balance(session: AsyncSession, user: User, amount: Decimal) -> bool:
    if user.balance < amount:
        return False
    user.balance -= amount
    await session.flush()
    return True
