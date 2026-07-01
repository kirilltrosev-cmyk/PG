from app.config import get_settings
from app.custom_emojis import ce


def is_test_mode() -> bool:
    return get_settings().test_mode


def test_mode_line() -> str:
    if not is_test_mode():
        return ""
    return f"{ce('test')} <b>Тестовый режим</b>\n\n"


def test_mode_suffix() -> str:
    if not is_test_mode():
        return ""
    return f"\n\n{ce('test')} <b>Тестовый режим</b>"
