from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.common import (
    advertise_keyboard,
    back_menu,
    checks_keyboard,
    earn_keyboard,
    languages_keyboard,
    levels_keyboard,
    main_menu,
    profile_back_keyboard,
    profile_keyboard,
    referrals_keyboard,
    topup_confirm_keyboard,
    topup_keyboard,
    useful_links_back_keyboard,
    useful_links_keyboard,
)
from app.repositories.stats import project_stats, referral_stats
from app.repositories.tasks import active_counts
from app.services.levels import get_level_info, levels_table, xp_to_next_level
from app.services.payments import complete_stars_payment, create_stars_topup, currency_for_stars, fail_stars_payment, send_stars_invoice
from app.states import TopUp
from app.texts import t
from app.utils.formatting import money
from app.utils.menu_match import menu_variants
from app.utils.test_mode import is_test_mode, test_mode_line
from app.utils.users import current_user

router = Router()


def telegram_profile_url(value: str) -> str:
    link = (value or "").strip()
    if not link:
        return ""
    if link.startswith(("https://", "http://")):
        return link
    if link.startswith("t.me/"):
        return f"https://{link}"
    return f"https://t.me/{link.lstrip('@')}"


def links_markup():
    settings = get_settings()
    support = telegram_profile_url(settings.support_username or "Human_Car_Home")
    chat = telegram_profile_url(settings.project_chat_url or "https://t.me/Viphakpremium_Pr_Gram")
    news = telegram_profile_url(settings.news_channel_url)
    return useful_links_keyboard(support_url=support, chat_url=chat, news_url=news)


def home_text(user) -> str:
    settings = get_settings()
    return test_mode_line() + t(
        user.language,
        "welcome",
        name=user.first_name or "друг",
        project_name=settings.project_name,
        currency_name=settings.currency_name,
    )


async def show_home(message: Message, session: AsyncSession) -> None:
    user = await current_user(message, session)
    await message.answer(home_text(user), reply_markup=main_menu(user.is_admin))


@router.callback_query(F.data == "menu:home")
async def home_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.message.delete()
    user = await current_user(callback, session)
    await callback.message.answer(home_text(user), reply_markup=main_menu(user.is_admin))
    await callback.answer()


@router.message(StateFilter("*"), F.text.in_(menu_variants("Заработать")))
async def earn(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await current_user(message, session)
    counts = await active_counts(session)
    await message.answer(t(user.language, "earn", **counts), reply_markup=earn_keyboard(user.is_premium))


@router.callback_query(F.data == "earn")
async def earn_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    counts = await active_counts(session)
    await callback.message.edit_text(t(user.language, "earn", **counts), reply_markup=earn_keyboard(user.is_premium))
    await callback.answer()


@router.callback_query(F.data == "premium_locked")
async def premium_locked(callback: CallbackQuery) -> None:
    await callback.answer("Это задание доступно только владельцам Telegram Premium.", show_alert=True)


async def profile_text(user, session: AsyncSession) -> str:
    settings = get_settings()
    refs = await referral_stats(session, user.id)
    level = get_level_info(user.xp)
    return t(
        user.language,
        "profile",
        project_name=settings.project_name,
        display_name=user.first_name or (f"@{user.username}" if user.username else "Пользователь"),
        telegram_id=user.telegram_id,
        balance=money(user.balance),
        currency_name=settings.currency_name,
        level_name=level.name,
        xp=user.xp,
        xp_left=xp_to_next_level(user.xp),
        referrals_count=refs["referrals_count"],
        notifications="включены" if user.notifications_enabled else "выключены",
    )


@router.message(StateFilter("*"), F.text.in_(menu_variants("Профиль")))
async def profile(message: Message, session: AsyncSession, bot, state: FSMContext) -> None:
    await state.clear()
    user = await current_user(message, session)
    await message.answer(await profile_text(user, session), reply_markup=profile_keyboard(user.notifications_enabled))


@router.callback_query(F.data == "profile:main")
async def profile_main(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await current_user(callback, session)
    await callback.message.edit_text(await profile_text(user, session), reply_markup=profile_keyboard(user.notifications_enabled))
    await callback.answer()


@router.callback_query(F.data == "profile:topup")
async def profile_topup(callback: CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    await callback.message.edit_text(
        test_mode_line() + t(user.language, "topup", balance=money(user.balance), currency_name=settings.currency_name),
        reply_markup=topup_keyboard(settings.currency_name),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:topup_pick:"))
async def profile_topup_pick(callback: CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    _, _, amount_raw, stars_raw = callback.data.split(":")
    amount = int(amount_raw)
    stars = int(stars_raw)
    await callback.message.edit_text(
        test_mode_line() + t(user.language, "topup_confirm", amount=f"{amount:,}".replace(",", " "), stars=stars, currency_name=settings.currency_name),
        reply_markup=topup_confirm_keyboard(amount, stars, is_test_mode()),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:topup_confirm:"))
async def profile_topup_confirm(callback: CallbackQuery, session: AsyncSession, bot) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    _, _, amount_raw, _stars_raw = callback.data.split(":")
    amount = Decimal(amount_raw)
    stars = int(_stars_raw)
    if is_test_mode():
        payment = await create_stars_topup(session, user, amount, stars)
        await complete_stars_payment(session, user.telegram_id, payment.payload or "", stars, f"test-charge-{payment.id}", "mock", is_test=True)
        await callback.message.edit_text(
            test_mode_line() + t(user.language, "topup_done", amount=money(amount), currency_name=settings.currency_name),
            reply_markup=profile_back_keyboard(),
        )
        await callback.answer()
        return
    if not settings.stars_payments_enabled:
        await callback.answer("Оплата Telegram Stars сейчас выключена.", show_alert=True)
        return
    payment = await create_stars_topup(session, user, amount, stars)
    await callback.message.answer(
        f"🧾 <b>Счет создан</b>\n\n"
        f"Пополнение на: {money(amount)} {settings.currency_name}\n"
        f"К оплате: {stars} Telegram Stars\n\n"
        "Нажмите кнопку оплаты ниже."
    )
    await send_stars_invoice(bot, callback.from_user.id, payment)
    await callback.message.edit_text(
        t(user.language, "topup_confirm", amount=money(amount), stars=stars, currency_name=settings.currency_name),
        reply_markup=profile_back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:topup_mock:"))
async def profile_topup_mock(callback: CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    _, _, amount_raw, _stars_raw, status = callback.data.split(":")
    if not is_test_mode():
        await callback.answer("Тестовый режим выключен.", show_alert=True)
        return
    amount = Decimal(amount_raw)
    stars = int(_stars_raw)
    payment = await create_stars_topup(session, user, amount, stars)
    if status == "paid":
        await complete_stars_payment(session, user.telegram_id, payment.payload or "", stars, f"test-charge-{payment.id}", "mock", is_test=True)
        text = test_mode_line() + t(user.language, "topup_done", amount=money(amount), currency_name=settings.currency_name)
    elif status == "pending":
        payment.status = "pending"
        text = test_mode_line() + "⏳ <b>Платёж ожидает подтверждения.</b>\n\nБаланс пока не изменён."
    else:
        await fail_stars_payment(session, payment)
        text = test_mode_line() + "❌ <b>Платёж завершился ошибкой.</b>\n\nБаланс не изменён."
    await callback.message.edit_text(text, reply_markup=profile_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "profile:topup_custom")
async def profile_topup_custom(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    await state.set_state(TopUp.waiting_custom_amount)
    await callback.message.edit_text("Введите количество Telegram Stars для пополнения.", reply_markup=profile_back_keyboard())
    await callback.answer()


@router.message(TopUp.waiting_custom_amount)
async def profile_topup_custom_amount(message: Message, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    user = await current_user(message, session)
    try:
        stars = int((message.text or "").replace(" ", ""))
    except ValueError:
        await message.answer("Введите целое количество Telegram Stars.")
        return
    if stars < settings.min_stars_topup or stars > settings.max_stars_topup:
        await message.answer(f"Введите от {settings.min_stars_topup} до {settings.max_stars_topup} Stars.")
        return
    amount = currency_for_stars(stars)
    await state.clear()
    await message.answer(
        test_mode_line() + t(user.language, "topup_confirm", amount=money(amount), stars=stars, currency_name=settings.currency_name),
        reply_markup=topup_confirm_keyboard(int(amount), stars, is_test_mode()),
    )


@router.callback_query(F.data == "profile:refs")
async def profile_refs(callback: CallbackQuery, session: AsyncSession, bot) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    refs = await referral_stats(session, user.id)
    me = await bot.get_me()
    referral_link = f"https://t.me/{me.username}?start=ref_{user.telegram_id}"
    await callback.message.edit_text(
        t(
            user.language,
            "refs",
            referral_link=referral_link,
            referrals_count=refs["referrals_count"],
            referral_earned=refs["referral_earned"],
            currency_name=settings.currency_name,
        ),
        reply_markup=referrals_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "profile:ref_copy")
async def profile_ref_copy(callback: CallbackQuery, bot) -> None:
    me = await bot.get_me()
    await callback.answer(f"Ваша ссылка: https://t.me/{me.username}?start=ref_{callback.from_user.id}", show_alert=True)


@router.callback_query(F.data == "profile:refs_stats")
async def profile_refs_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    await callback.message.edit_text(
        t(
            user.language,
            "refs_stats",
            regular=settings.ref_bonus_regular,
            premium=settings.ref_bonus_premium,
            op=settings.ref_bonus_op,
            deposit_percent=settings.ref_percent_deposits,
            task_percent=settings.ref_percent_tasks,
            currency_name=settings.currency_name,
        ),
        reply_markup=profile_back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "profile:levels")
async def profile_levels(callback: CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    level = get_level_info(user.xp)
    await callback.message.edit_text(
        t(
            user.language,
            "levels",
            level_name=level.name,
            xp=user.xp,
            xp_left=xp_to_next_level(user.xp),
            check_limit=level.check_limit.format(currency_name=settings.currency_name),
            deposit_percent=level.deposit_percent,
            task_percent=level.task_percent,
            levels_table=levels_table(settings.currency_name),
        ),
        reply_markup=levels_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "profile:xp_help")
async def profile_xp_help(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    await callback.message.edit_text(t(user.language, "xp_help"), reply_markup=profile_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "profile:language")
async def profile_language(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    await callback.message.edit_text(t(user.language, "language"), reply_markup=languages_keyboard())
    await callback.answer()


@router.callback_query(F.data == "profile:toggle_notifications")
async def profile_toggle_notifications(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    user.notifications_enabled = not user.notifications_enabled
    await callback.message.edit_text(
        t(user.language, "notifications_on" if user.notifications_enabled else "notifications_off"),
        reply_markup=profile_keyboard(user.notifications_enabled),
    )
    await callback.answer()


@router.message(StateFilter("*"), F.text.in_(menu_variants("Рекламировать")))
async def advertise(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    settings = get_settings()
    user = await current_user(message, session)
    await message.answer(
        t(
            user.language,
            "advertise",
            project_name=settings.project_name,
            balance=money(user.balance),
            currency_name=settings.currency_name,
        ),
        reply_markup=advertise_keyboard(),
    )


@router.message(StateFilter("*"), F.text.in_(menu_variants("Чеки")))
async def checks(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await current_user(message, session)
    await message.answer(t(user.language, "checks"), reply_markup=checks_keyboard())


@router.message(StateFilter("*"), F.text.in_(menu_variants("Полезные ссылки")))
async def links(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await current_user(message, session)
    await message.answer(t(user.language, "links"), reply_markup=links_markup())


@router.callback_query(F.data == "links:main")
async def links_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    await callback.message.edit_text(t(user.language, "links"), reply_markup=links_markup())
    await callback.answer()


@router.callback_query(F.data == "links:guide")
async def links_guide(callback: CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    user = await current_user(callback, session)
    await callback.message.edit_text(
        t(user.language, "guide", currency_name=settings.currency_name),
        reply_markup=useful_links_back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "links:rules")
async def links_rules(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    await callback.message.edit_text(t(user.language, "rules"), reply_markup=useful_links_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "links:policy")
async def links_policy(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    await callback.message.edit_text(t(user.language, "privacy_policy"), reply_markup=useful_links_back_keyboard())
    await callback.answer()


@router.message(StateFilter("*"), F.text.in_(menu_variants("Инструкция")))
async def guide(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    settings = get_settings()
    user = await current_user(message, session)
    await message.answer(t(user.language, "guide", currency_name=settings.currency_name), reply_markup=back_menu())


@router.message(StateFilter("*"), F.text.in_(menu_variants("Статистика")))
async def stats(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    settings = get_settings()
    user = await current_user(message, session)
    data = await project_stats(session)
    await message.answer(t(user.language, "stats", project_name=settings.project_name, **data), reply_markup=back_menu())


@router.message(StateFilter("*"), F.text.in_(menu_variants("Язык")))
async def language(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await current_user(message, session)
    await message.answer(t(user.language, "language"), reply_markup=languages_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await current_user(callback, session)
    user.language = callback.data.split(":")[1]
    await callback.message.edit_text(t(user.language, "language_set"), reply_markup=profile_back_keyboard())
    await callback.answer()
