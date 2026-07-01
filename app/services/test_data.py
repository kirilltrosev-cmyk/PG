from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.admin_log import AdminLog
from app.models.enums import TaskStatus, TaskType
from app.models.finance import Payment
from app.models.task import Task, TaskCompletion
from app.models.user import User


TEST_TELEGRAM_IDS = [900000001, 900000002, 900000003]


async def seed_test_data(session: AsyncSession) -> dict[str, int]:
    users = []
    for index, telegram_id in enumerate(TEST_TELEGRAM_IDS, start=1):
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=f"test_user_{index}",
                first_name=f"Test User {index}",
                balance=Decimal("500000.00") * index,
                xp=100 * index,
                is_test=True,
            )
            session.add(user)
        else:
            user.is_test = True
            user.balance = max(user.balance, Decimal("500000.00") * index)
        users.append(user)
    await session.flush()

    task_count = 0
    for task_type in [TaskType.CHANNEL, TaskType.GROUP, TaskType.BOT, TaskType.REACTION, TaskType.BOOST]:
        exists = await session.scalar(select(Task).where(Task.is_test.is_(True), Task.type == task_type.value))
        if exists:
            continue
        session.add(
            Task(
                creator_id=users[0].id,
                type=task_type.value,
                target_url=f"https://t.me/test_{task_type.value}",
                title=f"Test {task_type.value}",
                description="Test mode task",
                reward=Decimal("10.00"),
                total_limit=25,
                status=TaskStatus.ACTIVE.value,
                is_test=True,
            )
        )
        task_count += 1

    await session.flush()
    return {"users": len(users), "tasks": task_count}


async def clear_test_data(session: AsyncSession) -> dict[str, int]:
    result: dict[str, int] = {}
    for label, model in [
        ("completions", TaskCompletion),
        ("tasks", Task),
        ("payments", Payment),
        ("admin_logs", AdminLog),
    ]:
        outcome = await session.execute(delete(model).where(model.is_test.is_(True)))
        result[label] = outcome.rowcount or 0

    outcome = await session.execute(delete(User).where(User.is_test.is_(True)))
    result["users"] = outcome.rowcount or 0
    await session.flush()
    return result


def test_mode_settings_text() -> str:
    settings = get_settings()
    return (
        "🧪 <b>Тестовый режим</b>\n\n"
        f"TEST_MODE: {settings.test_mode}\n"
        f"PAYMENTS_PROVIDER: {settings.payments_provider}\n"
        f"STARS_TEST_MODE: {settings.stars_test_mode}"
    )
