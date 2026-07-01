import json
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.enums import CompletionStatus, TaskStatus, TaskType
from app.models.task import Task, TaskCompletion
from app.models.user import User


async def active_counts(session: AsyncSession) -> dict[str, int]:
    result = await session.execute(
        select(Task.type, func.count(Task.id)).where(Task.status == TaskStatus.ACTIVE.value).group_by(Task.type)
    )
    counts = {task_type.value: 0 for task_type in TaskType}
    counts.update(dict(result.all()))
    return counts


async def active_count_by_type(session: AsyncSession, task_type: str) -> int:
    total = await session.scalar(
        select(func.count(Task.id)).where(
            Task.type == task_type,
            Task.status == TaskStatus.ACTIVE.value,
            Task.completed_count < Task.total_limit,
        )
    )
    return int(total or 0)


def task_matches_user_filters(task: Task, user: User) -> bool:
    if task.audience_type == "premium" and not user.is_premium:
        return False
    if task.audience_type != "custom" or not task.filters_json:
        return True
    try:
        payload = json.loads(task.filters_json)
    except (TypeError, ValueError):
        return True
    languages = (payload.get("filters") or {}).get("languages") or []
    if languages and user.language not in languages:
        return False
    return True


def task_meta(task: Task) -> dict:
    if not task.filters_json:
        return {}
    try:
        payload = json.loads(task.filters_json)
    except (TypeError, ValueError):
        return {}
    return payload.get("meta") or {}


def task_matches_reaction_mode(task: Task, reaction_mode: str | None) -> bool:
    if task.type != TaskType.REACTION.value or not reaction_mode:
        return True
    mode = task_meta(task).get("reaction_mode", "any")
    return mode == reaction_mode


async def list_active(
    session: AsyncSession,
    task_type: str,
    user: User,
    page: int,
    per_page: int = 10,
    reaction_mode: str | None = None,
) -> tuple[list[Task], int]:
    completed_subq = select(TaskCompletion.task_id).where(TaskCompletion.user_id == user.id)
    base = (
        select(Task)
        .where(Task.type == task_type, Task.status == TaskStatus.ACTIVE.value)
        .where(Task.completed_count < Task.total_limit)
        .where(Task.creator_id != user.id)
        .where(Task.id.not_in(completed_subq))
        .order_by(Task.created_at)
    )
    result = await session.execute(base)
    tasks = [
        task
        for task in result.scalars()
        if task_matches_user_filters(task, user) and task_matches_reaction_mode(task, reaction_mode)
    ]
    total = len(tasks)
    start = max(page - 1, 0) * per_page
    return tasks[start : start + per_page], total


async def available_counts(session: AsyncSession, user: User) -> dict[str, int]:
    counts = {task_type.value: 0 for task_type in TaskType}
    for task_type in TaskType:
        _tasks, total = await list_active(session, task_type.value, user, page=1, per_page=1)
        counts[task_type.value] = total
    return counts


async def create_task(
    session: AsyncSession,
    creator: User,
    task_type: TaskType,
    target_url: str,
    target_chat_id: str | None,
    title: str,
    reward: Decimal,
    total_limit: int,
    audience_type: str = "all",
    filters_json: str | None = None,
    description: str | None = None,
    status: TaskStatus = TaskStatus.ACTIVE,
) -> Task:
    task = Task(
        creator_id=creator.id,
        type=task_type.value,
        target_url=target_url,
        target_chat_id=target_chat_id,
        title=title,
        description=description or "Задание создано пользователем и ожидает выполнения.",
        reward=reward,
        total_limit=total_limit,
        audience_type=audience_type,
        filters_json=filters_json,
        status=status.value,
        is_test=get_settings().test_mode,
    )
    session.add(task)
    await session.flush()
    return task


async def get_completion(session: AsyncSession, task_id: int, user_id: int) -> TaskCompletion | None:
    result = await session.execute(
        select(TaskCompletion).where(TaskCompletion.task_id == task_id, TaskCompletion.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def mark_paid(session: AsyncSession, task: Task, user: User) -> bool:
    if await get_completion(session, task.id, user.id):
        return False
    completion = TaskCompletion(
        task_id=task.id,
        user_id=user.id,
        status=CompletionStatus.PAID.value,
        reward=task.reward,
        is_test=get_settings().test_mode or bool(getattr(task, "is_test", False)),
    )
    user.balance += task.reward
    user.xp += int(task.reward)
    user.level = max(1, user.xp // 100 + 1)
    task.completed_count += 1
    if task.completed_count >= task.total_limit:
        task.status = TaskStatus.COMPLETED.value
    session.add(completion)
    await session.flush()
    return True


async def create_pending_proof(session: AsyncSession, task: Task, user: User, proof_file_id: str | None) -> TaskCompletion | None:
    if await get_completion(session, task.id, user.id):
        return None
    completion = TaskCompletion(
        task_id=task.id,
        user_id=user.id,
        status=CompletionStatus.PENDING.value,
        proof_file_id=proof_file_id,
        reward=task.reward,
        is_test=get_settings().test_mode or bool(getattr(task, "is_test", False)),
    )
    session.add(completion)
    await session.flush()
    return completion


async def pending_completions(session: AsyncSession) -> list[TaskCompletion]:
    result = await session.execute(
        select(TaskCompletion).where(TaskCompletion.status == CompletionStatus.DISPUTED.value).order_by(TaskCompletion.created_at)
    )
    return list(result.scalars())


async def list_created_by_user(session: AsyncSession, user: User) -> list[Task]:
    result = await session.execute(select(Task).where(Task.creator_id == user.id).order_by(Task.created_at.desc()))
    return list(result.scalars())


async def creator_pending_completions(session: AsyncSession, user: User) -> list[TaskCompletion]:
    task_ids = select(Task.id).where(Task.creator_id == user.id)
    result = await session.execute(
        select(TaskCompletion)
        .where(TaskCompletion.task_id.in_(task_ids), TaskCompletion.status == CompletionStatus.PENDING.value)
        .order_by(TaskCompletion.created_at)
    )
    return list(result.scalars())


async def pending_completions_for_task(session: AsyncSession, task_id: int) -> list[TaskCompletion]:
    result = await session.execute(
        select(TaskCompletion)
        .where(TaskCompletion.task_id == task_id, TaskCompletion.status == CompletionStatus.PENDING.value)
        .order_by(TaskCompletion.created_at)
    )
    return list(result.scalars())
