from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database.base import Base

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if settings.database_url.startswith("sqlite"):
            await _ensure_sqlite_test_columns(conn)
            await _ensure_sqlite_user_columns(conn)
            await _ensure_sqlite_payment_columns(conn)


async def _ensure_sqlite_test_columns(conn) -> None:
    test_columns = {
        "users": "is_test BOOLEAN DEFAULT 0 NOT NULL",
        "tasks": "is_test BOOLEAN DEFAULT 0 NOT NULL",
        "task_completions": "is_test BOOLEAN DEFAULT 0 NOT NULL",
        "payments": "is_test BOOLEAN DEFAULT 0 NOT NULL",
        "admin_logs": "is_test BOOLEAN DEFAULT 0 NOT NULL",
    }
    for table, ddl in test_columns.items():
        result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
        existing = {row[1] for row in result.fetchall()}
        if "is_test" not in existing:
            await conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {ddl}")


async def _ensure_sqlite_user_columns(conn) -> None:
    user_columns = {
        "is_premium": "is_premium BOOLEAN DEFAULT 0 NOT NULL",
    }
    result = await conn.exec_driver_sql("PRAGMA table_info(users)")
    existing = {row[1] for row in result.fetchall()}
    for column, ddl in user_columns.items():
        if column not in existing:
            await conn.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {ddl}")


async def _ensure_sqlite_payment_columns(conn) -> None:
    payment_columns = {
        "type": "type VARCHAR(32) DEFAULT 'stars_topup' NOT NULL",
        "payload": "payload VARCHAR(128)",
        "currency_name": "currency_name VARCHAR(32)",
        "stars_amount": "stars_amount INTEGER DEFAULT 0 NOT NULL",
        "payment_currency": "payment_currency VARCHAR(8) DEFAULT 'XTR' NOT NULL",
        "telegram_payment_charge_id": "telegram_payment_charge_id VARCHAR(128)",
        "provider_payment_charge_id": "provider_payment_charge_id VARCHAR(128)",
    }
    result = await conn.exec_driver_sql("PRAGMA table_info(payments)")
    existing = {row[1] for row in result.fetchall()}
    for column, ddl in payment_columns.items():
        if column not in existing:
            await conn.exec_driver_sql(f"ALTER TABLE payments ADD COLUMN {ddl}")


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
