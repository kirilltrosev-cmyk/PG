from decimal import Decimal


STATUS_LABELS = {
    "active": "активно",
    "moderation": "на модерации",
    "completed": "завершено",
    "paused": "остановлено",
    "rejected": "отклонено",
    "pending": "ожидает проверки",
    "disputed": "спор открыт",
    "paid": "оплачено",
    "approved": "принято",
    "accepted": "принято",
    "reviewed": "рассмотрено",
    "processing": "в обработке",
    "failed": "ошибка",
    "refunded": "возврат",
    "created": "создано",
    "new": "новое",
    "draft": "черновик",
    "already_paid": "уже оплачено",
}


def money(value: Decimal) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def status_label(status: str | None) -> str:
    if not status:
        return "неизвестно"
    value = str(status)
    return STATUS_LABELS.get(value, value.replace("_", " "))


def tree_list(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) <= 3:
        return "\n".join(f"• {item}" for item in items)
    lines = []
    for index, item in enumerate(items):
        prefix = "└" if index == len(items) - 1 else "├"
        lines.append(f"{prefix} {item}")
    return "\n".join(lines)
