# Telegram Agent — Отчёт о готовности к деплою

**Дата:** 8 апреля 2026
**Версия:** Phase 1 MVP + Phase 2б (семейный чат)
**Статус:** Готов к деплою на VPS

---

## Что реализовано

### Phase 1 — MVP (Claude в Telegram)

| Компонент | Файл | Описание |
|-----------|------|----------|
| Точка входа | `bot.py` | Dispatcher factory, polling, DI |
| Конфигурация | `config.py` | Pydantic Settings v2, все переменные из `.env` |
| Auth middleware | `middleware/auth.py` | Whitelist по `TELEGRAM_ALLOWED_USER_IDS`, группы пропускает |
| Claude сервис | `services/claude.py` | Anthropic AsyncClient, in-memory история (~20 сообщений), trimming парами |
| Команды | `handlers/commands.py` | `/start`, `/help`, `/clear` |
| Личный чат | `handlers/personal.py` | Только приватные чаты, typing indicator, error handling, split длинных ответов |

### Phase 2б — Семейный групповой чат

| Компонент | Файл | Описание |
|-----------|------|----------|
| Групповой хэндлер | `handlers/group.py` | Отвечает на @mention и reply, общая история на группу |
| Семейный промпт | `config.py` | Отдельный `family_system_prompt` — простой тон, без технических деталей |

---

## Структура проекта

```
telegram-agent/
├── bot.py                    # точка входа
├── config.py                 # pydantic-settings
├── requirements.txt          # pinned зависимости
├── .env.example              # шаблон переменных
├── handlers/
│   ├── __init__.py           # root router (commands → group → personal)
│   ├── commands.py           # /start /clear /help
│   ├── group.py              # семейный групповой чат
│   └── personal.py           # личный чат с Claude
├── middleware/
│   ├── __init__.py
│   └── auth.py               # фильтрация по user_id
└── services/
    ├── __init__.py
    └── claude.py             # Anthropic SDK + история в памяти
```

---

## Архитектурные решения

**Два режима — одна кодовая база:** определение по `chat.type`. Личный чат (`PRIVATE`) → `personal_router`, группа (`GROUP`/`SUPERGROUP`) → `group_router`. Middleware пропускает группы без проверки user_id.

**Раздельные промпты:** личный ассистент — кратко и по делу; семейный — дружелюбный, без техники.

**История:** для личного чата ключ = `user_id`, для группы = `chat_id` (отрицательное число). Вся семья видит общий контекст.

**Группа реагирует только на обращение:** `@bot_username` или reply на сообщение бота. Не флудит в групповом чате.

**DI через aiogram:** `claude_service` и `config` инжектятся через `Dispatcher(...)` → доступны как аргументы хэндлеров. Никаких глобальных переменных.

---

## Инструкция по деплою на VPS

```bash
# 1. Скопировать на VPS
scp -r telegram-agent/ user@vps:~/

# 2. Установить зависимости
cd ~/telegram-agent
pip install -r requirements.txt

# 3. Создать .env
cp .env.example .env
nano .env
# Заполнить: TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_IDS, CLAUDE_API_KEY

# 4. Запустить
python bot.py

# 5. (Опционально) Systemd сервис для автозапуска
sudo nano /etc/systemd/system/telegram-agent.service
```

Пример systemd unit:

```ini
[Unit]
Description=Telegram Agent Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/telegram-agent
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=5
EnvironmentFile=/home/ubuntu/telegram-agent/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-agent
sudo systemctl start telegram-agent
sudo journalctl -u telegram-agent -f  # логи
```

---

## Переменные окружения (.env)

| Переменная | Обязательная | Описание |
|------------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | да | Токен от @BotFather |
| `TELEGRAM_ALLOWED_USER_IDS` | да | ID пользователей (через запятую) |
| `CLAUDE_API_KEY` | да | Ключ Anthropic API |
| `CLAUDE_MODEL` | нет | Модель (default: `claude-opus-4-6`) |
| `CLAUDE_MAX_TOKENS` | нет | Лимит токенов (default: 2048) |
| `CLAUDE_HISTORY_LIMIT` | нет | Сколько сообщений хранить (default: 20) |
| `CLAUDE_SYSTEM_PROMPT` | нет | Промпт для личного чата |
| `CLAUDE_FAMILY_SYSTEM_PROMPT` | нет | Промпт для семейного чата |

---

## Что дальше — Phase 2a (Личные инструменты)

Следующий этап — переделка `ClaudeService.chat()` в agentic tool_use loop:

1. **KB tool** — `kb_search`, `kb_get_facts` через HTTP к VPS (обязательный)
2. **Notion tool** — поиск страниц, создание задач
3. **Web Search tool** — DuckDuckGo API
4. **Memory tool** — SQLite, долгосрочные факты
5. **Vision** — обработка фото через Claude Vision

---

## Зависимости

```
aiogram==3.27.0
anthropic==0.91.0
pydantic==2.12.5
pydantic-settings==2.13.1
```
