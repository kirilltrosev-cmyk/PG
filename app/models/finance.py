from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(32), default="stars_topup", index=True)
    provider: Mapped[str] = mapped_column(String(64), default="sandbox")
    payload: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)
    amount_money: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    amount_currency: Mapped[str] = mapped_column(String(16), default="TEST")
    amount_internal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stars_amount: Mapped[int] = mapped_column(Integer, default=0)
    payment_currency: Mapped[str] = mapped_column(String(8), default="XTR")
    status: Mapped[str] = mapped_column(String(32), default="paid")
    provider_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    telegram_payment_charge_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)
    provider_payment_charge_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    paid_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class Check(Base):
    __tablename__ = "checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    check_type: Mapped[str] = mapped_column(String(32), default="multi")
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    amount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    amount_per_user: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    activations_limit: Mapped[int] = mapped_column(default=1)
    activations_count: Mapped[int] = mapped_column(default=0)
    required_subscription_chat_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CheckActivation(Base):
    __tablename__ = "check_activations"

    id: Mapped[int] = mapped_column(primary_key=True)
    check_id: Mapped[int] = mapped_column(ForeignKey("checks.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
