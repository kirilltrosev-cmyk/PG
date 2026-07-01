from app.custom_emojis import button_fallback


MENU_EMOJI_NAMES = {
    "Заработать": "earn",
    "Рекламировать": "ads",
    "Чеки": "checks",
    "Профиль": "profile",
    "Проверка подписки": "subscription_check",
    "Статистика": "statistics",
    "Полезные ссылки": "links",
    "Инструкция": "instruction",
    "Язык": "language",
    "Админка": "admin",
}


def menu_variants(label: str) -> set[str]:
    emoji = button_fallback(MENU_EMOJI_NAMES.get(label, ""))
    return {label, f"{emoji} {label}"} if emoji else {label}
