# Telegram Agent — Личный AI-ассистент

Личный Telegram-бот на базе Claude с инструментами (Knowledge Base, Notion, Web Search, Memory, Vision) и семейным режимом для группового чата.

## Два режима

| Режим | Где | Возможности |
|-------|-----|-------------|
| **Личный** | Приватный чат (whitelist по user_id) | Claude + KB + Notion + Web Search + Memory + Vision |
| **Семейный** | Групповой чат (по @mention / reply) | Claude без инструментов, дружелюбный тон |

## Быстрый старт

```bash
# 1. Клонировать
git clone git@github.com:UshurbakiyevDavlat/Telegram-Assistant-Agent.git
cd Telegram-Assistant-Agent

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Настроить переменные окружения
cp .env.example .env
nano .env  # заполнить TELEGRAM_BOT_TOKEN, CLAUDE_API_KEY, TELEGRAM_ALLOWED_USER_IDS

# 4. Запустить
python bot.py
```

## Структура проекта

```
telegram-agent/
├── bot.py                    # Точка входа, dispatcher factory, polling
├── config.py                 # Pydantic Settings v2, все переменные из .env
├── handlers/
│   ├── __init__.py           # Root router (commands → group → personal)
│   ├── commands.py           # /start /help /clear /model
│   ├── group.py              # Семейный чат (Claude без инструментов)
│   └── personal.py           # Личный чат (agentic loop + Vision)
├── middleware/
│   ├── __init__.py
│   └── auth.py               # Whitelist по TELEGRAM_ALLOWED_USER_IDS
├── services/
│   ├── __init__.py
│   └── claude.py             # Anthropic SDK, agentic tool_use loop, история
├── tools/
│   ├── __init__.py
│   ├── definitions.py        # JSON Schema определения инструментов
│   ├── executor.py           # Диспетчер: name → execute
│   ├── kb.py                 # Knowledge Base (MCP SSE → VPS)
│   ├── notion_tool.py        # Notion API (search + create task)
│   ├── web_search.py         # DuckDuckGo
│   └── memory.py             # SQLite долгосрочная память
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/help` | Справка по возможностям |
| `/clear` | Очистить историю диалога |
| `/model` | Выбрать модель Claude (Opus / Sonnet / Haiku) |

## Инструменты (личный чат)

**KB (Knowledge Base)** — поиск по личной базе знаний (523+ чанков из Notion, сессий, проектов). Подключается к MCP серверу на VPS через SSE. Главный инструмент — используется для вопросов о проектах, архитектуре, прошлых решениях.

**Notion** — поиск страниц и создание задач через Notion API. Требует `NOTION_API_KEY` (internal integration).

**Web Search** — поиск в интернете через DuckDuckGo. Бесплатно, без API ключа. Для актуальной информации, документации, новостей.

**Memory** — SQLite-хранилище для долгосрочных фактов. Запоминает предпочтения, факты о семье, контекст проектов. Переживает перезагрузки бота.

**Vision** — анализ фотографий через Claude Vision. Отправь фото — бот распознает и ответит.

## Архитектура

```
Telegram (телефон)
 │
 ▼
aiogram 3 (Python)
 │ AuthMiddleware → whitelist по user_id
 ▼
┌─────────────────────────────────────┐
│ ClaudeService                       │
│                                     │
│ Личный чат:                         │
│   chat() → agentic tool_use loop    │
│   Claude ↔ tools ↔ Claude ↔ ...    │
│                                     │
│ Семейный чат:                       │
│   chat_simple() → одиночный вызов   │
└─────────────────────────────────────┘
 │
 ├── KB tool → MCP SSE → VPS (pgvector)
 ├── Notion tool → Notion API (httpx)
 ├── Web Search → DuckDuckGo
 └── Memory → SQLite (aiosqlite)
```

## Переменные окружения

| Переменная | Обязательная | Описание |
|------------|:-----------:|----------|
| `TELEGRAM_BOT_TOKEN` | да | Токен от @BotFather |
| `TELEGRAM_ALLOWED_USER_IDS` | да | ID пользователей через запятую |
| `CLAUDE_API_KEY` | да | Ключ Anthropic API |
| `CLAUDE_PERSONAL_MODEL` | нет | Модель для личного чата (default: claude-opus-4-6) |
| `CLAUDE_FAMILY_MODEL` | нет | Модель для семейного чата (default: claude-sonnet-4-5) |
| `KB_URL` | нет | URL MCP SSE сервера KB (default: http://127.0.0.1:8000/sse) |
| `NOTION_API_KEY` | нет | Токен Notion integration |
| `NOTION_TASKS_DATABASE_ID` | нет | ID базы данных для задач |
| `MEMORY_DB_PATH` | нет | Путь к SQLite (default: data/memory.db) |

## Деплой на VPS (systemd)

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
sudo cp telegram-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-agent
sudo systemctl start telegram-agent
sudo journalctl -u telegram-agent -f  # логи
```

## Стек

- Python 3.12
- aiogram 3 — Telegram Bot API
- anthropic SDK — Claude API с tool_use
- MCP SDK — подключение к Knowledge Base
- aiosqlite — SQLite для памяти
- duckduckgo-search — веб-поиск
- httpx — HTTP-клиент (Notion API)
- pydantic-settings — конфигурация

## Дорожная карта

- [x] Phase 1 — MVP: Claude в Telegram, /start /clear /help, auth middleware
- [x] Phase 2a — Инструменты: KB, Notion, Web Search, Memory, Vision
- [x] Phase 2б — Семейный чат: @mention, shared history, отдельный промпт
- [ ] Phase 3 — Morning Digest: утренний/вечерний дайджест (APScheduler)
- [ ] Phase 4 — Голос: Whisper для голосовых, webhook, режимы /work /study
