# PromoGram MVP

Рабочий MVP Telegram-бота на Python 3.11+ и aiogram 3.x для продвижения Telegram-проектов и заработка внутренней валюты.

## Что готово

- `/start`, главное меню, профиль, баланс, уровень, реферальная ссылка.
- Переменные `PROJECT_NAME` и `CURRENCY_NAME` используются в текстах через конфиг.
- Async SQLAlchemy, SQLite по умолчанию, схема подходит для перехода на PostgreSQL.
- Создание задания на канал с резервированием баланса.
- Автоматическая проверка подписки через Telegram API для channel/group задач, если указан `target_chat_id`.
- Bot/reaction/boost/post/view задачи работают через отправку скриншота и ручное подтверждение админом.
- Чеки: создание, ссылка активации, лимит активаций, защита от повторной активации.
- Реальное пополнение баланса через Telegram Stars с idempotency-защитой от повторного начисления.
- Админка для пользователей из `ADMIN_IDS`: статистика и подтверждение proof-заявок.
- Смена языка ru/en, остальные языки заложены в клавиатуру как расширяемая структура.
- Разделы проверки подписки, полезные ссылки, инструкция, статистика проекта.
- Антиспам на частые сообщения/нажатия и общий error logging.

## Установка

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка `.env`

Скопируйте `.env.example` в `.env` и заполните:

```env
BOT_TOKEN=123456:telegram-token
ADMIN_IDS=111111111,222222222
PROJECT_NAME=PromoGram
CURRENCY_NAME=GRAM
SUPPORT_USERNAME=@support
NEWS_CHANNEL_URL=https://t.me/news
RULES_URL=https://example.com/rules
DATABASE_URL=sqlite+aiosqlite:///bot.db
```

`ADMIN_IDS` указываются через запятую. Название проекта меняется только через `PROJECT_NAME`.

## Создание базы

Для MVP база создается автоматически при старте:

```powershell
python -m app.main
```

Также можно вызвать инициализацию отдельно:

```powershell
python -c "import asyncio; from app.database.session import init_db; asyncio.run(init_db())"
```

## Миграции

Alembic-скелет добавлен. Для production-сценария:

```powershell
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

При использовании SQLite в MVP автосоздание таблиц уже достаточно. Для PostgreSQL замените `DATABASE_URL`, например:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/promogram
```

и добавьте `asyncpg` в зависимости.

## Запуск

```powershell
.\.venv\Scripts\activate
python -m app.main
```

## Как подключить custom emoji

1. Создайте Telegram emoji-pack и добавьте его себе в Telegram.
2. Запустите бота и отправьте команду `/emoji_ids` от администратора из `ADMIN_IDS`.
3. Отправьте боту нужные custom emoji из своего набора.
4. Бот покажет `custom_emoji_id`, `offset` и `length`.
5. Вставьте ID в `app/custom_emojis.py` в нужные ключи.
6. Перезапустите бота.

Custom emoji используются только в текстах сообщений через HTML-тег `tg-emoji`. В inline-кнопках остаются обычные Unicode emoji, потому что кнопки не поддерживают HTML entities как сообщения. Если `id` пустой или `USE_CUSTOM_EMOJI=false`, бот покажет обычный fallback emoji.

Получить текущую заготовку словаря можно командой `/emoji_template` от администратора.

Для кнопок проект использует официальный параметр Bot API `icon_custom_emoji_id` через helper в `app/keyboards/common.py`. Требуется актуальная версия `aiogram`; текущий минимум в `requirements.txt` — `aiogram>=3.29,<4.0`. Если поле недоступно в старой версии, helper автоматически вернёт обычный fallback emoji в текст кнопки.

## Как подключить Telegram Stars

1. Включите платежи Stars у бота в BotFather, если они ещё не включены.
2. В `.env` оставьте `TEST_MODE=false` для реальных платежей.
3. Укажите настройки:

```env
STARS_PAYMENTS_ENABLED=true
CURRENCY_PER_STAR=1800
MIN_STARS_TOPUP=1
MAX_STARS_TOPUP=10000
```

Пользователь выбирает пакет пополнения, бот создаёт счёт Telegram Stars через `sendInvoice` с `currency="XTR"` и пустым `provider_token`. Внутренний баланс пополняется только после события `successful_payment`. Если Telegram повторно пришлёт тот же платёж, баланс не начислится второй раз.

Stars поступают на баланс Telegram-бота. Пользователь получает внутреннюю валюту проекта (`CURRENCY_NAME`), а владелец потом выводит Stars через доступные инструменты Telegram/Fragment.

Для проверки без реальных списаний включите:

```env
TEST_MODE=true
PAYMENTS_PROVIDER=mock
STARS_TEST_MODE=true
```

В тестовом режиме реальные счета Stars не создаются: бот показывает кнопки симуляции успешной оплаты, ошибки и ожидания. Все тестовые платежи записываются в БД с `is_test=true`.

## Как создать админа

Добавьте Telegram ID в `ADMIN_IDS`, перезапустите бота и выполните `/start`. Пользователь получит кнопку `Админка`.

## Заглушки и точки расширения

- Тестовые платежи начисляют баланс без реального платежного шлюза только при `TEST_MODE=true`.
- Раздел проверки подписки содержит структуру БД, управление группами и базовые group handlers.
- Для bot/reaction/boost/post/view проверка ручная, потому что Telegram API не всегда позволяет надежно проверить такие действия автоматически.
- Alembic настроен, но первая ревизия не сгенерирована, так как MVP умеет создавать таблицы сам.
- Остальные языки кроме ru/en заведены в интерфейсе как будущие переводы.
