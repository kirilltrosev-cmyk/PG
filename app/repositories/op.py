import json
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import OpConnectedBot, OpEvent, OpGroup, OpRequiredChannel, OpWhitelist
from app.models.user import User

DEFAULT_WARNING = (
    "{user_name}, чтобы писать в группе {group_title}, подпишитесь на обязательные ресурсы и нажмите кнопку проверки."
)

DEFAULT_SETTINGS = {
    "warning_text": DEFAULT_WARNING,
    "violation_action": "warn",
    "ignore_admins": True,
    "commands": {"check": True, "status": True, "op": True, "help": True},
    "stats": {
        "checks_total": 0,
        "checks_ok": 0,
        "checks_failed": 0,
        "messages_deleted": 0,
        "restricted": 0,
        "joined_today": 0,
        "joined_week": 0,
    },
}


def load_settings(group: OpGroup) -> dict:
    data = json.loads(group.settings_json or "{}")
    merged = DEFAULT_SETTINGS | data
    merged["commands"] = DEFAULT_SETTINGS["commands"] | data.get("commands", {})
    merged["stats"] = DEFAULT_SETTINGS["stats"] | data.get("stats", {})
    return merged


def save_settings(group: OpGroup, settings: dict) -> None:
    group.settings_json = json.dumps(settings, ensure_ascii=False)


async def upsert_group(session: AsyncSession, owner: User, chat_id: str, title: str) -> OpGroup:
    result = await session.execute(select(OpGroup).where(OpGroup.chat_id == chat_id))
    group = result.scalar_one_or_none()
    if group:
        group.owner_id = owner.id
        group.title = title
        if not group.settings_json:
            save_settings(group, DEFAULT_SETTINGS)
    else:
        group = OpGroup(owner_id=owner.id, chat_id=chat_id, title=title, is_enabled=False)
        save_settings(group, DEFAULT_SETTINGS)
        session.add(group)
    await session.flush()
    return group


async def owner_groups(session: AsyncSession, owner: User) -> list[OpGroup]:
    result = await session.execute(select(OpGroup).where(OpGroup.owner_id == owner.id).order_by(OpGroup.title))
    return list(result.scalars())


async def required_channels(session: AsyncSession, group_id: int) -> list[OpRequiredChannel]:
    result = await session.execute(select(OpRequiredChannel).where(OpRequiredChannel.group_id == group_id).order_by(OpRequiredChannel.id))
    return list(result.scalars())


async def add_required_channel(session: AsyncSession, group: OpGroup, channel_id: str, title: str, url: str) -> OpRequiredChannel:
    channel = OpRequiredChannel(group_id=group.id, channel_id=channel_id, channel_url=url, title=title)
    session.add(channel)
    await session.flush()
    return channel


async def upsert_connected_bot(
    session: AsyncSession,
    owner: User,
    bot_id: str,
    username: str,
    title: str,
    token_secret: str,
    token_hint: str,
) -> OpConnectedBot:
    result = await session.execute(select(OpConnectedBot).where(OpConnectedBot.owner_id == owner.id, OpConnectedBot.bot_id == bot_id))
    item = result.scalar_one_or_none()
    if item:
        item.username = username
        item.title = title
        item.token_secret = token_secret
        item.token_hint = token_hint
        item.is_enabled = True
    else:
        item = OpConnectedBot(
            owner_id=owner.id,
            bot_id=bot_id,
            username=username,
            title=title,
            token_secret=token_secret,
            token_hint=token_hint,
            is_enabled=True,
            created_at=datetime.utcnow().isoformat(),
        )
        session.add(item)
    await session.flush()
    return item


async def connected_bots(session: AsyncSession, owner: User) -> list[OpConnectedBot]:
    result = await session.execute(select(OpConnectedBot).where(OpConnectedBot.owner_id == owner.id).order_by(OpConnectedBot.username))
    return list(result.scalars())


async def connected_bots_by_owner_id(session: AsyncSession, owner_id: int) -> list[OpConnectedBot]:
    result = await session.execute(
        select(OpConnectedBot).where(OpConnectedBot.owner_id == owner_id, OpConnectedBot.is_enabled == True).order_by(OpConnectedBot.username)
    )
    return list(result.scalars())


async def delete_required_channel(session: AsyncSession, channel_id: int, group_id: int) -> None:
    await session.execute(delete(OpRequiredChannel).where(OpRequiredChannel.id == channel_id, OpRequiredChannel.group_id == group_id))


async def whitelist_users(session: AsyncSession, group_id: int) -> list[OpWhitelist]:
    result = await session.execute(select(OpWhitelist).where(OpWhitelist.group_id == group_id).order_by(OpWhitelist.id))
    return list(result.scalars())


async def add_whitelist_user(session: AsyncSession, group_id: int, user_id: str, username: str | None = None) -> None:
    session.add(OpWhitelist(group_id=group_id, user_id=user_id, username=username))
    await session.flush()


async def delete_whitelist_user(session: AsyncSession, item_id: int, group_id: int) -> None:
    await session.execute(delete(OpWhitelist).where(OpWhitelist.id == item_id, OpWhitelist.group_id == group_id))


async def is_whitelisted(session: AsyncSession, group_id: int, user_id: int, username: str | None) -> bool:
    result = await session.execute(
        select(OpWhitelist).where(
            OpWhitelist.group_id == group_id,
            (OpWhitelist.user_id == str(user_id)) | (OpWhitelist.username == (username or "")),
        )
    )
    return result.scalar_one_or_none() is not None


async def log_event(session: AsyncSession, group_id: int, user_id: int, event_type: str, details: dict | None = None) -> None:
    session.add(
        OpEvent(
            group_id=group_id,
            user_id=str(user_id),
            event_type=event_type,
            details_json=json.dumps(details or {}, ensure_ascii=False),
            created_at=datetime.utcnow().isoformat(),
        )
    )


async def group_stats(session: AsyncSession, group_id: int) -> dict[str, int]:
    total = int(await session.scalar(select(func.count(OpEvent.id)).where(OpEvent.group_id == group_id)) or 0)
    ok = int(await session.scalar(select(func.count(OpEvent.id)).where(OpEvent.group_id == group_id, OpEvent.event_type == "check_ok")) or 0)
    failed = int(await session.scalar(select(func.count(OpEvent.id)).where(OpEvent.group_id == group_id, OpEvent.event_type == "check_failed")) or 0)
    deleted = int(await session.scalar(select(func.count(OpEvent.id)).where(OpEvent.group_id == group_id, OpEvent.event_type == "message_deleted")) or 0)
    restricted = int(await session.scalar(select(func.count(OpEvent.id)).where(OpEvent.group_id == group_id, OpEvent.event_type == "restricted")) or 0)
    return {"checks_total": total, "checks_ok": ok, "checks_failed": failed, "messages_deleted": deleted, "restricted": restricted}
