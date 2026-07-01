from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.common import add_button
from app.models.enums import TaskStatus


def admin_main_keyboard():
    builder = InlineKeyboardBuilder()
    add_button(builder, "Пользователи", callback_data="admin:users", emoji_name="users")
    add_button(builder, "Задания", callback_data="admin:tasks", emoji_name="tasks")
    add_button(builder, "Споры", callback_data="admin:proofs", emoji_name="proof")
    add_button(builder, "Жалобы", callback_data="admin:complaints", emoji_name="complaint")
    add_button(builder, "Платежи", callback_data="admin:payments", emoji_name="payment")
    add_button(builder, "Рассылка", callback_data="admin:broadcast", emoji_name="broadcast")
    add_button(builder, "Настройки", callback_data="admin:settings", emoji_name="settings")
    add_button(builder, "Статистика", callback_data="admin:statistics", emoji_name="statistics")
    add_button(builder, "Логи", callback_data="admin:logs:1", emoji_name="logs")
    add_button(builder, "Обновить", callback_data="admin:menu", emoji_name="refresh")
    add_button(builder, "Закрыть", callback_data="admin:close", emoji_name="close")
    builder.adjust(2, 2, 2, 2, 2, 2)
    return builder.as_markup()


def admin_back_keyboard(target: str = "admin:menu"):
    builder = InlineKeyboardBuilder()
    add_button(builder, "Назад", callback_data=target, emoji_name="back")
    return builder.as_markup()


def admin_users_keyboard():
    builder = InlineKeyboardBuilder()
    add_button(builder, "Найти пользователя", callback_data="admin:user_search", emoji_name="search")
    add_button(builder, "Список пользователей", callback_data="admin:users_list:1", emoji_name="copy")
    add_button(builder, "Заблокированные", callback_data="admin:users_blocked:1", emoji_name="shield")
    add_button(builder, "Топ по балансу", callback_data="admin:users_top_balance:1", emoji_name="levels")
    add_button(builder, "Назад", callback_data="admin:menu", emoji_name="back")
    builder.adjust(1, 2, 1, 1)
    return builder.as_markup()


def admin_list_keyboard(prefix: str, page: int, pages: int, back: str = "admin:menu"):
    builder = InlineKeyboardBuilder()
    if page > 1:
        add_button(builder, "Назад", callback_data=f"{prefix}:{page - 1}", emoji_name="back")
    if page < pages:
        add_button(builder, "Далее", callback_data=f"{prefix}:{page + 1}", emoji_name="next")
    add_button(builder, "Обновить", callback_data=f"{prefix}:{page}", emoji_name="refresh")
    add_button(builder, "В меню", callback_data=back, emoji_name="back")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def admin_entity_list_keyboard(items: list[tuple[str, str]], prefix: str, page: int, pages: int, back: str):
    builder = InlineKeyboardBuilder()
    for text, callback_data in items:
        add_button(builder, text, callback_data=callback_data, emoji_name="search")
    if page > 1:
        add_button(builder, "Назад", callback_data=f"{prefix}:{page - 1}", emoji_name="back")
    if page < pages:
        add_button(builder, "Далее", callback_data=f"{prefix}:{page + 1}", emoji_name="next")
    add_button(builder, "Обновить", callback_data=f"{prefix}:{page}", emoji_name="refresh")
    add_button(builder, "В меню", callback_data=back, emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def admin_user_card_keyboard(user_id: int, blocked: bool):
    builder = InlineKeyboardBuilder()
    add_button(builder, "Выдать монеты", callback_data=f"admin:user_balance:add:{user_id}", emoji_name="add")
    add_button(builder, "Списать монеты", callback_data=f"admin:user_balance:subtract:{user_id}", emoji_name="minus")
    add_button(builder, "Установить баланс", callback_data=f"admin:user_balance:set:{user_id}", emoji_name="edit")
    add_button(builder, "Разблокировать" if blocked else "Заблокировать", callback_data=f"admin:user_block:{user_id}:{0 if blocked else 1}", emoji_name="confirm" if blocked else "shield")
    add_button(builder, "Назад", callback_data="admin:users", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def admin_balance_confirm_keyboard(action: str, user_id: int, amount: str):
    builder = InlineKeyboardBuilder()
    add_button(builder, "Подтвердить", callback_data=f"admin:user_balance_confirm:{action}:{user_id}:{amount}", emoji_name="confirm", style="success")
    add_button(builder, "Отмена", callback_data=f"admin:user:{user_id}", emoji_name="cancel", style="danger")
    builder.adjust(2)
    return builder.as_markup()


def admin_payment_card_keyboard(payment_id: int, can_refund: bool):
    builder = InlineKeyboardBuilder()
    if can_refund:
        add_button(builder, "Возврат Stars", callback_data=f"admin:payment_refund:{payment_id}", emoji_name="refresh", style="danger")
    add_button(builder, "Назад", callback_data="admin:payments_list:any:1", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def admin_tasks_keyboard():
    builder = InlineKeyboardBuilder()
    labels = [
        (TaskStatus.MODERATION.value, "На модерации", "moderation"),
        (TaskStatus.ACTIVE.value, "Активные", "confirm"),
        (TaskStatus.PAUSED.value, "Остановленные", "pause"),
        (TaskStatus.COMPLETED.value, "Завершённые", "finish"),
        (TaskStatus.REJECTED.value, "Отклонённые", "complaint"),
    ]
    for status, text, emoji in labels:
        add_button(builder, text, callback_data=f"admin:tasks_list:{status}:1", emoji_name=emoji)
    add_button(builder, "Назад", callback_data="admin:menu", emoji_name="back")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def admin_task_card_keyboard(task_id: int):
    builder = InlineKeyboardBuilder()
    add_button(builder, "Одобрить", callback_data=f"admin:task_status:{task_id}:active", emoji_name="confirm")
    add_button(builder, "Отклонить", callback_data=f"admin:task_status:{task_id}:rejected", emoji_name="error")
    add_button(builder, "Остановить", callback_data=f"admin:task_status:{task_id}:paused", emoji_name="pause")
    add_button(builder, "Завершить", callback_data=f"admin:task_status:{task_id}:completed", emoji_name="finish")
    add_button(builder, "Назад", callback_data="admin:tasks", emoji_name="back")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def admin_proofs_keyboard():
    builder = InlineKeyboardBuilder()
    add_button(builder, "Все споры", callback_data="admin:proofs_list:1", emoji_name="copy")
    add_button(builder, "Назад", callback_data="admin:menu", emoji_name="back")
    builder.adjust(1)
    return builder.as_markup()


def admin_proof_card_keyboard(proof_id: int):
    builder = InlineKeyboardBuilder()
    add_button(builder, "Принять спор", callback_data=f"admin:proof_approve:{proof_id}", emoji_name="confirm", style="success")
    add_button(builder, "Отклонить спор", callback_data=f"admin:proof_reject:{proof_id}", emoji_name="error", style="danger")
    add_button(builder, "Назад", callback_data="admin:proofs_list:1", emoji_name="back")
    builder.adjust(2, 1)
    return builder.as_markup()


def admin_complaints_keyboard():
    builder = InlineKeyboardBuilder()
    for status, text, emoji in [
        ("new", "Новые", "new"),
        ("processing", "В работе", "moderation"),
        ("accepted", "Принятые", "confirm"),
        ("rejected", "Отклонённые", "error"),
    ]:
        add_button(builder, text, callback_data=f"admin:complaints_list:{status}:1", emoji_name=emoji)
    add_button(builder, "Назад", callback_data="admin:menu", emoji_name="back")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def admin_complaint_card_keyboard(complaint_id: int):
    builder = InlineKeyboardBuilder()
    add_button(builder, "Принять", callback_data=f"admin:complaint_status:{complaint_id}:accepted", emoji_name="confirm")
    add_button(builder, "Отклонить", callback_data=f"admin:complaint_status:{complaint_id}:rejected", emoji_name="error")
    add_button(builder, "В работу", callback_data=f"admin:complaint_status:{complaint_id}:processing", emoji_name="moderation")
    add_button(builder, "Назад", callback_data="admin:complaints", emoji_name="back")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def admin_broadcast_keyboard():
    builder = InlineKeyboardBuilder()
    add_button(builder, "Всем", callback_data="admin:broadcast_audience:all", emoji_name="users")
    add_button(builder, "Активным", callback_data="admin:broadcast_audience:active", emoji_name="confirm")
    add_button(builder, "С уведомлениями", callback_data="admin:broadcast_audience:notifications", emoji_name="notifications_on")
    add_button(builder, "С балансом", callback_data="admin:broadcast_audience:balance", emoji_name="balance")
    add_button(builder, "Назад", callback_data="admin:menu", emoji_name="back")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def admin_broadcast_confirm_keyboard(audience: str):
    builder = InlineKeyboardBuilder()
    add_button(builder, "Отправить", callback_data=f"admin:broadcast_confirm:{audience}", emoji_name="confirm", style="success")
    add_button(builder, "Отмена", callback_data="admin:broadcast", emoji_name="cancel", style="danger")
    builder.adjust(2)
    return builder.as_markup()
