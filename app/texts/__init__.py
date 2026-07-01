from app.texts.en import TEXTS as EN
from app.texts.ru import TEXTS as RU

LANGUAGE_OVERRIDES = {
    "uk": {
        "language": "Оберіть мову інтерфейсу.",
        "language_set": "Мову змінено на українську.",
    },
    "de": {
        "language": "Wählen Sie die Sprache der Oberfläche.",
        "language_set": "Die Sprache wurde auf Deutsch geändert.",
    },
    "zh": {
        "language": "请选择界面语言。",
        "language_set": "语言已切换为中文。",
    },
    "ar": {
        "language": "اختر لغة الواجهة.",
        "language_set": "تم تغيير اللغة إلى العربية.",
    },
    "fa": {
        "language": "زبان رابط کاربری را انتخاب کنید.",
        "language_set": "زبان به فارسی تغییر کرد.",
    },
    "es": {
        "language": "Seleccione el idioma de la interfaz.",
        "language_set": "El idioma se cambió a español.",
    },
    "id": {
        "language": "Pilih bahasa antarmuka.",
        "language_set": "Bahasa diubah ke Bahasa Indonesia.",
    },
    "pt": {
        "language": "Escolha o idioma da interface.",
        "language_set": "O idioma foi alterado para português.",
    },
    "hi": {
        "language": "इंटरफ़ेस भाषा चुनें।",
        "language_set": "भाषा हिन्दी में बदल दी गई है।",
    },
    "bn": {
        "language": "ইন্টারফেসের ভাষা নির্বাচন করুন।",
        "language_set": "ভাষা বাংলায় পরিবর্তন করা হয়েছে।",
    },
    "uz": {
        "language": "Interfeys tilini tanlang.",
        "language_set": "Til o‘zbekchaga o‘zgartirildi.",
    },
    "tr": {
        "language": "Arayüz dilini seçin.",
        "language_set": "Dil Türkçe olarak değiştirildi.",
    },
    "kk": {
        "language": "Интерфейс тілін таңдаңыз.",
        "language_set": "Тіл қазақшаға ауыстырылды.",
    },
    "fr": {
        "language": "Choisissez la langue de l’interface.",
        "language_set": "La langue est passée au français.",
    },
}

CATALOG = {
    "ru": RU,
    "en": EN,
    **{language: {**RU, **texts} for language, texts in LANGUAGE_OVERRIDES.items()},
}


def t(language: str, key: str, **kwargs) -> str:
    catalog = CATALOG.get(language, RU)
    template = catalog.get(key, RU.get(key, EN[key]))
    return template.format(**kwargs)
