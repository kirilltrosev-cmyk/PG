from app.texts.en import TEXTS as EN
from app.texts.locales import LANGUAGE_OVERRIDES
from app.texts.ru import TEXTS as RU


CATALOG = {
    "ru": RU,
    "en": EN,
    **LANGUAGE_OVERRIDES,
}


def t(language: str, key: str, **kwargs) -> str:
    catalog = CATALOG.get(language, RU)
    template = catalog.get(key, EN.get(key, RU[key]))
    return template.format(**kwargs)
