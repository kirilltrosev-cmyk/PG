from html import escape
from pprint import pformat

from app.config import get_settings


# id is a Telegram custom_emoji_id.
# If id is empty, the bot uses fallback.
# You can start with regular emoji now and later replace them with premium/custom emoji
# by filling the needed id fields without rewriting message texts.
CUSTOM_EMOJIS = {
    "profile": {"id": "5305436280270658180", "fallback": "👤"},
    "balance": {"id": "5283232570660634549", "fallback": "💰"},
    "ads": {"id": "5305778267041602238", "fallback": "📢"},
    "earn": {"id": "5305455036392841533", "fallback": "💼"},
    "checks": {"id": "5305264391384504472", "fallback": "🧾"},
    "subscription_check": {"id": "5305625774227760054", "fallback": "🔐"},
    "statistics": {"id": "", "fallback": "📊"},
    "links": {"id": "", "fallback": "🔗"},
    "instruction": {"id": "", "fallback": "📘"},
    "support": {"id": "", "fallback": "💬"},
    "privacy": {"id": "", "fallback": "🛡"},
    "channel": {"id": "", "fallback": "📣"},
    "group": {"id": "", "fallback": "👥"},
    "post": {"id": "", "fallback": "📝"},
    "bot": {"id": "", "fallback": "🤖"},
    "reactions": {"id": "", "fallback": "❤️"},
    "boost": {"id": "", "fallback": "⭐"},
    "auto_tasks": {"id": "", "fallback": "⚙️"},
    "my_tasks": {"id": "", "fallback": "📂"},
    "success": {"id": "5305324834459263842", "fallback": "✅"},
    "error": {"id": "5305775217614821987", "fallback": "❌"},
    "warning": {"id": "5305426565054633447", "fallback": "⚠️"},
    "info": {"id": "5305584722930343990", "fallback": "ℹ️"},
    "next": {"id": "", "fallback": "➡️"},
    "confirm": {"id": "", "fallback": "✅"},
    "cancel": {"id": "", "fallback": "✖️"},
    "delete": {"id": "", "fallback": "🗑"},
    "edit": {"id": "", "fallback": "✏️"},
    "search": {"id": "", "fallback": "🔎"},
    "payment": {"id": "", "fallback": "💳"},
    "stars": {"id": "5453900977432188793", "fallback": "⭐"},
    "gift": {"id": "", "fallback": "🎁"},
    "wallet": {"id": "", "fallback": "👛"},
    "premium": {"id": "", "fallback": "💎"},
    "settings": {"id": "5305544238568611374", "fallback": "⚙️"},
    "language": {"id": "5305594158973500958", "fallback": "🌐"},
    "referrals": {"id": "5303103589042923982", "fallback": "👥"},
    "levels": {"id": "5305463312794820933", "fallback": "🏆"},
    "xp": {"id": "", "fallback": "✨"},
    "id": {"id": "", "fallback": "🆔"},
    "notifications_on": {"id": "", "fallback": "🔔"},
    "notifications_off": {"id": "", "fallback": "🔕"},
    "lock": {"id": "", "fallback": "🔒"},
    "unlock": {"id": "", "fallback": "🔓"},
    "shield": {"id": "", "fallback": "🛡"},
    "commands": {"id": "", "fallback": "⌨️"},
    "admin": {"id": "", "fallback": "🛠"},
    "users": {"id": "", "fallback": "👥"},
    "tasks": {"id": "", "fallback": "📢"},
    "logs": {"id": "", "fallback": "🗂"},
    "close": {"id": "", "fallback": "❌"},
    "add": {"id": "", "fallback": "➕"},
    "minus": {"id": "", "fallback": "➖"},
    "pause": {"id": "", "fallback": "⏸"},
    "play": {"id": "", "fallback": "▶️"},
    "finish": {"id": "", "fallback": "🏁"},
    "new": {"id": "", "fallback": "🆕"},
    "comment": {"id": "", "fallback": "💬"},
    "calendar": {"id": "", "fallback": "📅"},
    "complaint": {"id": "", "fallback": "🚩"},
    "proof": {"id": "", "fallback": "🖼"},
    "moderation": {"id": "", "fallback": "🕒"},
    "broadcast": {"id": "", "fallback": "📣"},
    "test": {"id": "", "fallback": "🧪"},
    "back": {"id": "5305275781637774136", "fallback": "⬅️"},
    "refresh": {"id": "5289930378885214069", "fallback": "🔄"},
    "copy": {"id": "5303453817856109827", "fallback": "📋"},
}


def emoji(name: str) -> str:
    item = CUSTOM_EMOJIS.get(name)
    if not item:
        return "▫️"

    fallback = escape(item.get("fallback") or "▫️")
    emoji_id = escape(str(item.get("id") or ""))
    if not get_settings().use_custom_emoji or not emoji_id:
        return fallback
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def ce(name: str) -> str:
    return emoji(name)


def button_emoji_id(name: str) -> str | None:
    item = CUSTOM_EMOJIS.get(name)
    if not item or not get_settings().use_custom_emoji:
        return None
    emoji_id = str(item.get("id") or "")
    return emoji_id or None


def button_fallback(name: str) -> str:
    item = CUSTOM_EMOJIS.get(name)
    if not item:
        return ""
    return item.get("fallback", "")


def button_emoji(name: str) -> str:
    return button_fallback(name)


def emoji_template() -> str:
    return pformat(CUSTOM_EMOJIS, width=120, sort_dicts=False)
