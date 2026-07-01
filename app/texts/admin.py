from html import escape

from app.custom_emojis import ce
from app.models.finance import Payment
from app.models.social import Complaint
from app.models.task import Task, TaskCompletion
from app.models.user import User
from app.services.levels import get_level_info
from app.utils.formatting import money, status_label, tree_list
from app.utils.test_mode import test_mode_line


def admin_menu_text(admin_name: str, data: dict[str, int]) -> str:
    return (
        test_mode_line()
        + f"{ce('admin')} <b>Админ-панель</b>\n\n"
        f"Добро пожаловать, {escape(admin_name)}.\n\n"
        "<b>Сводка:</b>\n"
        + tree_list(
            [
                f"Пользователи: {data['users_count']}",
                f"Активные задания: {data['active_tasks_count']}",
                f"Открытые споры: {data['pending_proofs_count']}",
                f"Жалобы: {data['complaints_count']}",
            ]
        )
        + "\n\nВыберите раздел управления."
    )


def users_text(data: dict[str, int]) -> str:
    return (
        f"{ce('users')} <b>Пользователи</b>\n\n"
        "<b>Сводка:</b>\n"
        + tree_list(
            [
                f"Всего: {data['users_count']}",
                f"За сегодня: {data['today_users_count']}",
                f"За неделю: {data['week_users_count']}",
                f"Заблокированы: {data['blocked_users_count']}",
                f"С балансом > 0: {data['users_with_balance_count']}",
            ]
        )
        + "\n\nВыберите действие."
    )


def user_card_text(user: User, referrals_count: int, currency_name: str) -> str:
    username = f"@{escape(user.username)}" if user.username else "не указан"
    status = "заблокирован" if user.is_blocked else "активен"
    level = get_level_info(user.xp)
    return (
        f"{ce('profile')} <b>Пользователь</b>\n\n"
        + tree_list(
            [
                f"ID: {user.telegram_id}",
                f"Username: {username}",
                f"Имя: {escape(user.first_name or 'не указано')}",
                f"Баланс: {money(user.balance)} {escape(currency_name)}",
                f"XP: {user.xp}",
                f"Уровень: {escape(level.name)}",
                f"Рефералов: {referrals_count}",
                f"Статус: {status}",
                f"Дата регистрации: {user.created_at:%Y-%m-%d %H:%M}",
            ]
        )
    )


def users_list_text(title: str, users: list[User], page: int, pages: int) -> str:
    if not users:
        items = "Список пуст."
    else:
        items = tree_list([f"#{user.id}: {escape(user.first_name or 'без имени')} · {user.telegram_id} · {money(user.balance)}" for user in users])
    return f"{ce('users')} <b>{escape(title)}</b>\n\n{items}\n\nСтраница {page}/{pages}"


def tasks_text(data: dict[str, int]) -> str:
    return (
        f"{ce('tasks')} <b>Задания</b>\n\n"
        "<b>Статусы:</b>\n"
        + tree_list(
            [
                f"Активные: {data.get('active', 0)}",
                f"На модерации: {data.get('moderation', 0)}",
                f"Завершённые: {data.get('completed', 0)}",
                f"Остановленные: {data.get('paused', 0)}",
                f"Отклонённые: {data.get('rejected', 0)}",
            ]
        )
        + "\n\nВыберите раздел."
    )


def task_card_text(task: Task, currency_name: str) -> str:
    return (
        f"{ce('tasks')} <b>Задание #{task.id}</b>\n\n"
        + tree_list(
            [
                f"Тип: {escape(task.type)}",
                f"Создатель: {task.creator_id}",
                f"Награда: {money(task.reward)} {escape(currency_name)}",
                f"Лимит: {task.completed_count}/{task.total_limit}",
                f"Состояние: {escape(status_label(task.status))}",
                f"Создано: {task.created_at:%Y-%m-%d %H:%M}",
            ]
        )
    )


def proofs_text(total: int) -> str:
    return f"{ce('proof')} <b>Споры по заданиям</b>\n\nОткрытых споров: {total}\n\nАдмин проверяет только спорные proof-заявки."


def proof_card_text(proof: TaskCompletion, task: Task | None, currency_name: str) -> str:
    return (
        f"{ce('proof')} <b>Спор #{proof.id}</b>\n\n"
        + tree_list(
            [
                f"Пользователь: {proof.user_id}",
                f"Задание: #{proof.task_id}",
                f"Тип: {escape(task.type if task else 'не найдено')}",
                f"Награда: {money(proof.reward)} {escape(currency_name)}",
                f"Состояние: {escape(status_label(proof.status))}",
                f"Скрин: {'приложен' if proof.proof_file_id else 'не приложен'}",
                f"Дата: {proof.created_at:%Y-%m-%d %H:%M}",
            ]
        )
    )


def complaints_text(data: dict[str, int]) -> str:
    return (
        f"{ce('complaint')} <b>Жалобы</b>\n\n"
        "<b>Статусы:</b>\n"
        + tree_list(
            [
                f"Новые: {data.get('new', 0)}",
                f"В работе: {data.get('processing', 0)}",
                f"Принятые: {data.get('accepted', 0) + data.get('reviewed', 0)}",
                f"Отклонённые: {data.get('rejected', 0)}",
            ]
        )
    )


def complaint_card_text(complaint: Complaint) -> str:
    return (
        f"{ce('complaint')} <b>Жалоба #{complaint.id}</b>\n\n"
        + tree_list(
            [
                f"Пользователь: {complaint.user_id}",
                f"Задание: #{complaint.task_id}",
                f"Причина: {escape(complaint.reason)}",
                f"Состояние: {escape(status_label(complaint.status))}",
                f"Дата: {complaint.created_at:%Y-%m-%d %H:%M}",
            ]
        )
    )


def payments_text(data: dict, currency_name: str) -> str:
    return (
        f"{ce('payment')} <b>Платежи</b>\n\n"
        "<b>Сводка:</b>\n"
        + tree_list(
            [
                f"Сегодня: {money(data['today_payments_sum'])} {escape(currency_name)}",
                f"Неделя: {money(data['week_payments_sum'])} {escape(currency_name)}",
                f"Месяц: {money(data['month_payments_sum'])} {escape(currency_name)}",
                f"Созданы: {data['created_payments_count']}",
                f"Ожидают: {data['pending_payments_count']}",
                f"Успешные: {data['successful_payments_count']}",
                f"Ошибки: {data['failed_payments_count']}",
                f"Возвраты: {data['refunded_payments_count']}",
                f"Получено Stars: {data['stars_received']}",
                f"Начислено: {money(data['currency_credited'])} {escape(currency_name)}",
            ]
        )
    )


def payment_list_text(payments: list[Payment], page: int, pages: int, currency_name: str) -> str:
    items = tree_list([f"#{p.id}: user {p.user_id}, {money(p.amount_internal)} {escape(currency_name)}, {p.stars_amount} Stars, {escape(status_label(p.status))}" for p in payments]) if payments else "Список пуст."
    return f"{ce('payment')} <b>Платежи</b>\n\n{items}\n\nСтраница {page}/{pages}"


def payment_card_text(payment: Payment, currency_name: str) -> str:
    paid_at = payment.paid_at or "не оплачен"
    return (
        f"{ce('payment')} <b>Платеж #{payment.id}</b>\n\n"
        + tree_list(
            [
                f"Пользователь: {payment.user_id}",
                f"Тип: {escape(payment.type)}",
                f"Состояние: {escape(status_label(payment.status))}",
                f"Сумма: {money(payment.amount_internal)} {escape(payment.currency_name or currency_name)}",
                f"Stars: {payment.stars_amount}",
                f"Payload: {escape(payment.payload or '-')}",
                f"Telegram charge ID: {escape(payment.telegram_payment_charge_id or '-')}",
                f"Создан: {payment.created_at:%Y-%m-%d %H:%M}",
                f"Оплачен: {escape(paid_at)}",
            ]
        )
    )


def statistics_text(data: dict, currency_name: str) -> str:
    return (
        f"{ce('statistics')} <b>Статистика бота</b>\n\n"
        "<b>Пользователи:</b>\n"
        + tree_list([f"Всего: {data['users_count']}", f"Сегодня: {data['today_users']}", f"Неделя: {data['week_users']}", f"Месяц: {data['month_users']}"])
        + "\n\n<b>Задания:</b>\n"
        + tree_list([f"Активные: {data['active_tasks']}", f"Выполнено: {data['completed_tasks']}", f"Споры: {data['pending_proofs']}", f"Жалобы: {data['complaints']}"])
        + "\n\n<b>Финансы:</b>\n"
        + tree_list(
            [
                f"Баланс пользователей: {money(data['total_user_balance'])} {escape(currency_name)}",
                f"Пополнения сегодня: {money(data['today_deposits'])} {escape(currency_name)}",
                f"Пополнения за месяц: {money(data['month_deposits'])} {escape(currency_name)}",
            ]
        )
    )
