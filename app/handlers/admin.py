from decimal import Decimal
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.custom_emojis import emoji_template
from app.keyboards.admin import (
    admin_back_keyboard,
    admin_balance_confirm_keyboard,
    admin_broadcast_confirm_keyboard,
    admin_broadcast_keyboard,
    admin_complaint_card_keyboard,
    admin_complaints_keyboard,
    admin_entity_list_keyboard,
    admin_list_keyboard,
    admin_main_keyboard,
    admin_payment_card_keyboard,
    admin_proof_card_keyboard,
    admin_proofs_keyboard,
    admin_task_card_keyboard,
    admin_tasks_keyboard,
    admin_user_card_keyboard,
    admin_users_keyboard,
)
from app.models.enums import CompletionStatus, TaskStatus
from app.models.finance import Payment
from app.models.social import Complaint
from app.models.task import Task, TaskCompletion
from app.models.user import User
from app.repositories.admin_repository import (
    admin_summary,
    bot_statistics,
    broadcast_targets,
    complaints_summary,
    list_complaints,
    list_logs,
    list_payments,
    list_pending_proofs,
    list_tasks_by_status,
    list_users,
    log_admin_action,
    payments_summary,
    search_users,
    tasks_summary,
    user_referrals_count,
    users_summary,
)
from app.repositories.users import add_balance
from app.services.admin_service import apply_balance_action, parse_amount, run_broadcast, set_complaint_status, set_task_status, set_user_block
from app.services.payments import refund_stars_payment
from app.services.test_data import clear_test_data, seed_test_data, test_mode_settings_text
from app.states import AdminBalanceAction, AdminBroadcast, AdminUserSearch, EmojiIds
from app.texts.admin import (
    admin_menu_text,
    complaint_card_text,
    complaints_text,
    payment_list_text,
    payment_card_text,
    payments_text,
    proof_card_text,
    proofs_text,
    statistics_text,
    task_card_text,
    tasks_text,
    user_card_text,
    users_list_text,
    users_text,
)
from app.utils.formatting import money, status_label, tree_list
from app.utils.menu_match import menu_variants
from app.utils.users import current_user

router = Router()


async def require_admin_message(message: Message, session: AsyncSession):
    user = await current_user(message, session)
    if not user.is_admin:
        await message.answer("Недостаточно прав.")
        return None
    return user


async def require_admin_callback(callback: CallbackQuery, session: AsyncSession):
    user = await current_user(callback, session)
    if not user.is_admin:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return None
    return user


def entity_text(text: str, offset: int, length: int) -> str:
    encoded = text.encode("utf-16-le")
    start = offset * 2
    end = (offset + length) * 2
    return encoded[start:end].decode("utf-16-le")


async def send_admin_menu(target: Message | CallbackQuery, session: AsyncSession, state: FSMContext | None = None) -> None:
    if state:
        await state.clear()
    admin = await current_user(target, session)
    text = admin_menu_text(admin.first_name or "админ", await admin_summary(session))
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=admin_main_keyboard())
        await target.answer()
    else:
        await target.answer(text, reply_markup=admin_main_keyboard())


async def replace_admin_message(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    if callback.message.photo:
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await callback.message.answer(text, reply_markup=reply_markup)
        return
    await callback.message.edit_text(text, reply_markup=reply_markup)


async def show_admin_proof_card(callback: CallbackQuery, proof: TaskCompletion, task: Task | None) -> None:
    text = proof_card_text(proof, task, get_settings().currency_name)
    reply_markup = admin_proof_card_keyboard(proof.id)
    if proof.proof_file_id:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=reply_markup)
            return
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await callback.message.answer_photo(proof.proof_file_id, caption=text, reply_markup=reply_markup)
        return
    await replace_admin_message(callback, text, reply_markup=reply_markup)


@router.message(Command("admin"))
async def admin_command(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_message(message, session):
        return
    await send_admin_menu(message, session, state)


@router.message(Command("seed_test_data"))
async def seed_test_data_command(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message, session):
        return
    result = await seed_test_data(session)
    await message.answer(
        test_mode_settings_text()
        + "\n\nТестовые данные созданы:\n"
        + tree_list(
            [
                f"Пользователи: {result['users']}",
                f"Задания: {result['tasks']}",
            ]
        )
    )


@router.message(Command("clear_test_data"))
async def clear_test_data_command(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message, session):
        return
    result = await clear_test_data(session)
    await message.answer(
        "🧪 <b>Тестовые данные удалены:</b>\n\n"
        + tree_list(
            [
                f"События сделок: {result['events']}",
                f"Выполнения заданий: {result['completions']}",
                f"Задания: {result['tasks']}",
                f"Платежи: {result['payments']}",
                f"Логи админки: {result['admin_logs']}",
                f"Пользователи: {result['users']}",
            ]
        )
    )


@router.message(StateFilter("*"), F.text.in_(menu_variants("Админка")))
async def admin_panel_button(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_message(message, session):
        return
    await send_admin_menu(message, session, state)


@router.callback_query(F.data == "admin:menu")
async def admin_menu_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_callback(callback, session):
        return
    await send_admin_menu(callback, session, state)


@router.callback_query(F.data == "admin:close")
async def admin_close(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_callback(callback, session):
        return
    await state.clear()
    await callback.message.edit_text("Админ-панель закрыта.")
    await callback.answer()


@router.message(Command("emoji_ids"))
async def emoji_ids_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_message(message, session):
        return
    await state.set_state(EmojiIds.waiting_custom_emoji)
    await message.answer("Отправь мне custom emoji из своего emoji-pack, а я покажу их custom_emoji_id.")


@router.message(Command("emoji_template"))
async def emoji_template_command(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message, session):
        return
    await message.answer("<pre>" + escape(emoji_template()) + "</pre>")


@router.message(EmojiIds.waiting_custom_emoji)
async def emoji_ids_read(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_message(message, session):
        await state.clear()
        return
    text = message.text or message.caption or ""
    entities = list(message.entities or []) + list(message.caption_entities or [])
    custom_entities = [
        entity
        for entity in entities
        if (entity.type == "custom_emoji" or getattr(entity.type, "value", None) == "custom_emoji") and entity.custom_emoji_id
    ]
    if not custom_entities:
        await message.answer("Custom emoji не найден. Отправь именно кастомный эмодзи из добавленного emoji-pack.")
        return
    lines = ["Найдено custom emoji:"]
    for index, entity in enumerate(custom_entities, start=1):
        base = entity_text(text, entity.offset, entity.length) if text else "?"
        lines.append(f"\n{index}. {escape(base)}\ncustom_emoji_id: <code>{escape(entity.custom_emoji_id)}</code>\noffset: {entity.offset}\nlength: {entity.length}")
    await message.answer("\n".join(lines))
    await state.clear()


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    await callback.message.edit_text(users_text(await users_summary(session)), reply_markup=admin_users_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:user_search")
async def admin_user_search(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_callback(callback, session):
        return
    await state.set_state(AdminUserSearch.waiting_query)
    await callback.message.edit_text("Введите Telegram ID, username, имя или внутренний ID пользователя.", reply_markup=admin_back_keyboard("admin:users"))
    await callback.answer()


@router.message(AdminUserSearch.waiting_query)
async def admin_user_search_query(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_message(message, session):
        return
    users = await search_users(session, message.text or "")
    await state.clear()
    if not users:
        await message.answer("Пользователь не найден.", reply_markup=admin_users_keyboard())
        return
    lines = [f"#{user.id}: {escape(user.first_name or 'без имени')} · {user.telegram_id} · @{escape(user.username or '-')}" for user in users]
    await message.answer(
        "Найдено:\n\n" + tree_list(lines),
        reply_markup=admin_entity_list_keyboard(
            [(f"Открыть #{user.id}", f"admin:user:{user.id}") for user in users],
            "admin:users_list",
            1,
            1,
            "admin:users",
        ),
    )


@router.callback_query(F.data.startswith("admin:users_list:"))
async def admin_users_list(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    page = int(callback.data.split(":")[2])
    users, total = await list_users(session, page)
    pages = max(1, (total + 4) // 5)
    await callback.message.edit_text(
        users_list_text("Список пользователей", users, page, pages),
        reply_markup=admin_entity_list_keyboard(
            [(f"Открыть #{user.id}", f"admin:user:{user.id}") for user in users],
            "admin:users_list",
            page,
            pages,
            "admin:users",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:users_blocked:"))
async def admin_users_blocked(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    page = int(callback.data.split(":")[2])
    users, total = await list_users(session, page, blocked=True)
    pages = max(1, (total + 4) // 5)
    await callback.message.edit_text(
        users_list_text("Заблокированные", users, page, pages),
        reply_markup=admin_entity_list_keyboard(
            [(f"Открыть #{user.id}", f"admin:user:{user.id}") for user in users],
            "admin:users_blocked",
            page,
            pages,
            "admin:users",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:users_top_balance:"))
async def admin_users_top_balance(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    page = int(callback.data.split(":")[2])
    users, total = await list_users(session, page, order_by_balance=True)
    pages = max(1, (total + 4) // 5)
    await callback.message.edit_text(
        users_list_text("Топ по балансу", users, page, pages),
        reply_markup=admin_entity_list_keyboard(
            [(f"Открыть #{user.id}", f"admin:user:{user.id}") for user in users],
            "admin:users_top_balance",
            page,
            pages,
            "admin:users",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user:"))
async def admin_user_card(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    user = await session.get(User, int(callback.data.split(":")[2]))
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    settings = get_settings()
    await callback.message.edit_text(
        user_card_text(user, await user_referrals_count(session, user.id), settings.currency_name),
        reply_markup=admin_user_card_keyboard(user.id, user.is_blocked),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user_balance:"))
async def admin_user_balance_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_callback(callback, session):
        return
    _, _, action, user_id = callback.data.split(":")
    await state.set_state(AdminBalanceAction.waiting_amount)
    await state.update_data(action=action, user_id=int(user_id))
    await callback.message.edit_text("Введите сумму.", reply_markup=admin_back_keyboard(f"admin:user:{user_id}"))
    await callback.answer()


@router.message(AdminBalanceAction.waiting_amount)
async def admin_user_balance_amount(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_message(message, session):
        return
    data = await state.get_data()
    amount = parse_amount(message.text or "")
    if amount is None:
        await message.answer("Введите корректную сумму.")
        return
    await state.clear()
    await message.answer(
        f"Подтвердить действие с балансом?\n\nСумма: {money(amount)} {get_settings().currency_name}",
        reply_markup=admin_balance_confirm_keyboard(data["action"], data["user_id"], str(amount)),
    )


@router.callback_query(F.data.startswith("admin:user_balance_confirm:"))
async def admin_user_balance_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    admin = await require_admin_callback(callback, session)
    if not admin:
        return
    _, _, action, user_id, amount_raw = callback.data.split(":")
    target = await session.get(User, int(user_id))
    if not target:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    text = await apply_balance_action(session, admin, target, action, Decimal(amount_raw))
    await callback.answer(text, show_alert=True)
    await callback.message.edit_text(user_card_text(target, await user_referrals_count(session, target.id), get_settings().currency_name), reply_markup=admin_user_card_keyboard(target.id, target.is_blocked))


@router.callback_query(F.data.startswith("admin:user_block:"))
async def admin_user_block(callback: CallbackQuery, session: AsyncSession) -> None:
    admin = await require_admin_callback(callback, session)
    if not admin:
        return
    _, _, user_id, blocked_raw = callback.data.split(":")
    target = await session.get(User, int(user_id))
    if not target:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    await callback.answer(await set_user_block(session, admin, target, blocked_raw == "1"), show_alert=True)
    await callback.message.edit_text(user_card_text(target, await user_referrals_count(session, target.id), get_settings().currency_name), reply_markup=admin_user_card_keyboard(target.id, target.is_blocked))


@router.callback_query(F.data == "admin:tasks")
async def admin_tasks(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    await callback.message.edit_text(tasks_text(await tasks_summary(session)), reply_markup=admin_tasks_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tasks_list:"))
async def admin_tasks_list(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    _, _, status, page_raw = callback.data.split(":")
    page = int(page_raw)
    tasks, total = await list_tasks_by_status(session, status, page)
    pages = max(1, (total + 4) // 5)
    items = tree_list([f"#{task.id}: {escape(task.title)} · {task.completed_count}/{task.total_limit}" for task in tasks]) if tasks else "Список пуст."
    await callback.message.edit_text(
        f"Задания: {escape(status_label(status))}\n\n{items}\n\nСтраница {page}/{pages}",
        reply_markup=admin_entity_list_keyboard(
            [(f"Открыть #{task.id}", f"admin:task:{task.id}") for task in tasks],
            f"admin:tasks_list:{status}",
            page,
            pages,
            "admin:tasks",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:task:"))
async def admin_task_card(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    task = await session.get(Task, int(callback.data.split(":")[2]))
    if not task:
        await callback.answer("Задание не найдено.", show_alert=True)
        return
    await callback.message.edit_text(task_card_text(task, get_settings().currency_name), reply_markup=admin_task_card_keyboard(task.id))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:task_status:"))
async def admin_task_status(callback: CallbackQuery, session: AsyncSession) -> None:
    admin = await require_admin_callback(callback, session)
    if not admin:
        return
    _, _, task_id, status = callback.data.split(":")
    task = await session.get(Task, int(task_id))
    if not task:
        await callback.answer("Задание не найдено.", show_alert=True)
        return
    await callback.answer(await set_task_status(session, admin, task, status), show_alert=True)
    await callback.message.edit_text(task_card_text(task, get_settings().currency_name), reply_markup=admin_task_card_keyboard(task.id))


@router.callback_query(F.data == "admin:proofs")
async def admin_proofs(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    proofs, total = await list_pending_proofs(session, 1)
    await callback.message.edit_text(proofs_text(total), reply_markup=admin_proofs_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("admin:proofs_list:"))
async def admin_proofs_list(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    page = int(callback.data.split(":")[2])
    proofs, total = await list_pending_proofs(session, page)
    pages = max(1, (total + 4) // 5)
    items = tree_list([f"#{proof.id}: task #{proof.task_id}, user {proof.user_id}, {money(proof.reward)}" for proof in proofs]) if proofs else "Список пуст."
    await replace_admin_message(
        callback,
        f"Споры по заданиям\n\n{items}\n\nСтраница {page}/{pages}",
        reply_markup=admin_entity_list_keyboard(
            [(f"Открыть #{proof.id}", f"admin:proof:{proof.id}") for proof in proofs],
            "admin:proofs_list",
            page,
            pages,
            "admin:proofs",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:proof:"))
async def admin_proof_card(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    proof = await session.get(TaskCompletion, int(callback.data.split(":")[2]))
    if not proof:
        await callback.answer("Спор не найден.", show_alert=True)
        return
    task = await session.get(Task, proof.task_id)
    await show_admin_proof_card(callback, proof, task)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:proof_"))
async def admin_proof_moderate(callback: CallbackQuery, session: AsyncSession) -> None:
    admin = await require_admin_callback(callback, session)
    if not admin:
        return
    action, proof_id = callback.data.removeprefix("admin:proof_").split(":")
    proof = await session.get(TaskCompletion, int(proof_id))
    if not proof or proof.status != CompletionStatus.DISPUTED.value:
        await callback.answer("Спор уже обработан.", show_alert=True)
        return
    task = await session.get(Task, proof.task_id)
    settings = get_settings()
    if action == "approve":
        proof.status = CompletionStatus.PAID.value
        await add_balance(session, proof.user_id, proof.reward)
        if task:
            task.completed_count += 1
            if task.completed_count >= task.total_limit:
                task.status = TaskStatus.COMPLETED.value
        await log_admin_action(session, admin.id, "dispute_approve", proof.user_id, f"proof_id={proof.id}")
        if callback.message.photo:
            await callback.message.edit_caption(caption=f"Спор #{proof.id} принят. Начислено {proof.reward} {settings.currency_name}.")
        else:
            await callback.message.edit_text(f"Спор #{proof.id} принят. Начислено {proof.reward} {settings.currency_name}.")
    else:
        proof.status = CompletionStatus.REJECTED.value
        await log_admin_action(session, admin.id, "dispute_reject", proof.user_id, f"proof_id={proof.id}")
        if callback.message.photo:
            await callback.message.edit_caption(caption=f"Спор #{proof.id} отклонён.")
        else:
            await callback.message.edit_text(f"Спор #{proof.id} отклонён.")
    await callback.answer()


@router.callback_query(F.data == "admin:complaints")
async def admin_complaints(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    await callback.message.edit_text(complaints_text(await complaints_summary(session)), reply_markup=admin_complaints_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("admin:complaints_list:"))
async def admin_complaints_list(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    _, _, status, page_raw = callback.data.split(":")
    page = int(page_raw)
    complaints, total = await list_complaints(session, status, page)
    pages = max(1, (total + 4) // 5)
    items = tree_list([f"#{item.id}: task #{item.task_id}, user {item.user_id}" for item in complaints]) if complaints else "Список пуст."
    await callback.message.edit_text(
        f"Жалобы: {escape(status_label(status))}\n\n{items}\n\nСтраница {page}/{pages}",
        reply_markup=admin_entity_list_keyboard(
            [(f"Открыть #{item.id}", f"admin:complaint:{item.id}") for item in complaints],
            f"admin:complaints_list:{status}",
            page,
            pages,
            "admin:complaints",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:complaint:"))
async def admin_complaint_card(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    complaint = await session.get(Complaint, int(callback.data.split(":")[2]))
    if not complaint:
        await callback.answer("Жалоба не найдена.", show_alert=True)
        return
    await callback.message.edit_text(complaint_card_text(complaint), reply_markup=admin_complaint_card_keyboard(complaint.id))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:complaint_status:"))
async def admin_complaint_status(callback: CallbackQuery, session: AsyncSession) -> None:
    admin = await require_admin_callback(callback, session)
    if not admin:
        return
    _, _, complaint_id, status = callback.data.split(":")
    complaint = await session.get(Complaint, int(complaint_id))
    if not complaint:
        await callback.answer("Жалоба не найдена.", show_alert=True)
        return
    await callback.answer(await set_complaint_status(session, admin, complaint, status), show_alert=True)
    await callback.message.edit_text(complaint_card_text(complaint), reply_markup=admin_complaint_card_keyboard(complaint.id))


@router.callback_query(F.data == "admin:payments")
async def admin_payments(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    await callback.message.edit_text(payments_text(await payments_summary(session), get_settings().currency_name), reply_markup=admin_list_keyboard("admin:payments_list:any", 1, 1, "admin:menu"))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:payments_list:"))
async def admin_payments_list(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    _, _, status, page_raw = callback.data.split(":")
    page = int(page_raw)
    payments, total = await list_payments(session, None if status == "any" else status, page)
    pages = max(1, (total + 4) // 5)
    await callback.message.edit_text(
        payment_list_text(payments, page, pages, get_settings().currency_name),
        reply_markup=admin_entity_list_keyboard(
            [(f"Открыть #{payment.id}", f"admin:payment:{payment.id}") for payment in payments],
            f"admin:payments_list:{status}",
            page,
            pages,
            "admin:payments",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:payment:"))
async def admin_payment_card(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    payment = await session.get(Payment, int(callback.data.split(":")[2]))
    if not payment:
        await callback.answer("Платеж не найден.", show_alert=True)
        return
    can_refund = payment.status == "paid" and payment.payment_currency == "XTR" and bool(payment.telegram_payment_charge_id)
    await callback.message.edit_text(
        payment_card_text(payment, get_settings().currency_name),
        reply_markup=admin_payment_card_keyboard(payment.id, can_refund),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:payment_refund:"))
async def admin_payment_refund(callback: CallbackQuery, session: AsyncSession, bot) -> None:
    admin = await require_admin_callback(callback, session)
    if not admin:
        return
    payment = await session.get(Payment, int(callback.data.split(":")[2]))
    if not payment:
        await callback.answer("Платеж не найден.", show_alert=True)
        return
    ok, text = await refund_stars_payment(bot, session, payment)
    if ok:
        await log_admin_action(session, admin.id, "stars_refund", payment.user_id, f"payment_id={payment.id}")
    await callback.answer(text, show_alert=True)
    await callback.message.edit_text(
        payment_card_text(payment, get_settings().currency_name),
        reply_markup=admin_payment_card_keyboard(payment.id, False),
    )


@router.callback_query(F.data == "admin:statistics")
async def admin_statistics(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    await callback.message.edit_text(statistics_text(await bot_statistics(session), get_settings().currency_name), reply_markup=admin_back_keyboard("admin:menu"))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:logs:"))
async def admin_logs(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    page = int(callback.data.split(":")[2])
    logs, total = await list_logs(session, page)
    pages = max(1, (total + 4) // 5)
    items = tree_list([f"#{log.id}: {escape(log.action)} · admin {log.admin_id} · {log.created_at:%Y-%m-%d %H:%M}" for log in logs]) if logs else "Логов пока нет."
    await callback.message.edit_text(f"🗂 <b>Логи</b>\n\n{items}\n\nСтраница {page}/{pages}", reply_markup=admin_list_keyboard("admin:logs", page, pages, "admin:menu"))
    await callback.answer()


@router.callback_query(F.data == "admin:settings")
async def admin_settings(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    settings = get_settings()
    text = "⚙️ <b>Настройки</b>\n\n" + tree_list(
        [
            f"Создание заданий: включено",
            f"Чеки: включены",
            f"Техработы: выключены",
        ]
    )
    await callback.message.edit_text(text, reply_markup=admin_back_keyboard("admin:menu"))
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback, session):
        return
    await callback.message.edit_text("Выберите аудиторию рассылки.", reply_markup=admin_broadcast_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("admin:broadcast_audience:"))
async def admin_broadcast_audience(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_callback(callback, session):
        return
    audience = callback.data.split(":")[2]
    await state.set_state(AdminBroadcast.waiting_text)
    await state.update_data(audience=audience)
    await callback.message.edit_text("Отправьте текст рассылки. Перед отправкой будет предпросмотр.", reply_markup=admin_back_keyboard("admin:broadcast"))
    await callback.answer()


@router.message(AdminBroadcast.waiting_text)
async def admin_broadcast_text(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_message(message, session):
        return
    data = await state.get_data()
    safe_text = escape(message.text or "")
    await state.update_data(text=safe_text)
    await message.answer("<b>Предпросмотр рассылки:</b>\n\n" + safe_text, reply_markup=admin_broadcast_confirm_keyboard(data["audience"]))


@router.callback_query(F.data.startswith("admin:broadcast_confirm:"))
async def admin_broadcast_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext, bot) -> None:
    admin = await require_admin_callback(callback, session)
    if not admin:
        return
    audience = callback.data.split(":")[2]
    data = await state.get_data()
    text = data.get("text", "")
    users = await broadcast_targets(session, audience)
    result = await run_broadcast(bot, users, text)
    await log_admin_action(session, admin.id, "broadcast", details=f"audience={audience}; result={result}")
    await state.clear()
    await callback.message.edit_text(f"Рассылка завершена.\n\n" + tree_list([f"Всего: {result['total']}", f"Отправлено: {result['sent']}", f"Ошибок: {result['errors']}"]), reply_markup=admin_back_keyboard("admin:menu"))
    await callback.answer()
