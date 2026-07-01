from aiogram.fsm.state import State, StatesGroup


class CreateTask(StatesGroup):
    waiting_manual_filters = State()
    waiting_url = State()
    waiting_chat_target = State()
    waiting_reward = State()
    waiting_limit = State()
    waiting_boost_amount = State()
    waiting_boost_target = State()
    waiting_boost_link = State()
    waiting_reaction_price = State()
    waiting_reaction_amount = State()
    waiting_reaction_stars_payment = State()
    waiting_reaction_url = State()
    waiting_reaction_emoji = State()
    waiting_view_price = State()
    waiting_view_amount = State()
    waiting_view_url = State()
    waiting_ad_stars_payment = State()
    waiting_bot_conditions = State()


class CreateCheck(StatesGroup):
    waiting_amount = State()
    waiting_limit = State()


class ActivateCheck(StatesGroup):
    waiting_token = State()


class TopUp(StatesGroup):
    waiting_custom_amount = State()


class SubscriptionCheck(StatesGroup):
    waiting_group_title = State()
    waiting_channel = State()
    waiting_bot_token = State()
    waiting_warning_text = State()
    waiting_whitelist_user = State()


class EmojiIds(StatesGroup):
    waiting_custom_emoji = State()


class ManualProof(StatesGroup):
    waiting_screenshot = State()


class AdminUserSearch(StatesGroup):
    waiting_query = State()


class AdminBalanceAction(StatesGroup):
    waiting_amount = State()


class AdminBroadcast(StatesGroup):
    waiting_text = State()
