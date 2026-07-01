from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field("", alias="BOT_TOKEN")
    admin_ids: str = Field("", alias="ADMIN_IDS")
    project_name: str = Field("PromoGram", alias="PROJECT_NAME")
    currency_name: str = Field("GRAM", alias="CURRENCY_NAME")
    support_username: str = Field("", alias="SUPPORT_USERNAME")
    news_channel_url: str = Field("", alias="NEWS_CHANNEL_URL")
    project_chat_url: str = Field("", alias="PROJECT_CHAT_URL")
    partnership_url: str = Field("", alias="PARTNERSHIP_URL")
    rules_url: str = Field("", alias="RULES_URL")
    policy_url: str = Field("", alias="POLICY_URL")
    database_url: str = Field("sqlite+aiosqlite:///bot.db", alias="DATABASE_URL")
    use_custom_emoji: bool = Field(True, alias="USE_CUSTOM_EMOJI")
    test_mode: bool = Field(False, alias="TEST_MODE")
    payments_provider: str = Field("sandbox", alias="PAYMENTS_PROVIDER")
    stars_test_mode: bool = Field(False, alias="STARS_TEST_MODE")
    stars_payments_enabled: bool = Field(True, alias="STARS_PAYMENTS_ENABLED")
    currency_per_star: int = Field(1800, alias="CURRENCY_PER_STAR")
    min_stars_topup: int = Field(1, alias="MIN_STARS_TOPUP")
    max_stars_topup: int = Field(10000, alias="MAX_STARS_TOPUP")
    referral_bonus: int = Field(10, alias="REFERRAL_BONUS")
    ref_bonus_regular: int = Field(10, alias="REF_BONUS_REGULAR")
    ref_bonus_premium: int = Field(25, alias="REF_BONUS_PREMIUM")
    ref_bonus_op: int = Field(15, alias="REF_BONUS_OP")
    ref_percent_deposits: int = Field(10, alias="REF_PERCENT_DEPOSITS")
    ref_percent_tasks: int = Field(3, alias="REF_PERCENT_TASKS")
    default_task_reward: int = Field(5, alias="DEFAULT_TASK_REWARD")
    proof_dispute_delay_hours: int = Field(24, alias="PROOF_DISPUTE_DELAY_HOURS")
    complaint_cooldown_seconds: int = Field(300, alias="COMPLAINT_COOLDOWN_SECONDS")
    op_token_secret: str = Field("", alias="OP_TOKEN_SECRET")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admins(self) -> set[int]:
        return {int(item.strip()) for item in self.admin_ids.split(",") if item.strip().isdigit()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
