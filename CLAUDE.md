# CLAUDE.md — SciProof

## Проект

SciProof — мульти-агентный дискуссионный сервис. 4 LLM-агента (2×Claude + 2×GPT) с разными persona и температурой обсуждают вопрос в нескольких раундах. LLM-судья оценивает раунды и делает финальный синтез. Результат — карта аргументации: консенсус, разногласия, эволюция позиций.

## Архитектура

```
Frontend (React+Vite) → Backend (FastAPI) → LLM Gateway (LiteLLM) → Anthropic API / OpenAI API
                                          → Judge Module (Sonnet)
                                          → Web Search (Brave API)
                                          → PostgreSQL
```

### Компоненты бэкенда

| Компонент | Файл | Вход | Выход |
|-----------|------|------|-------|
| Orchestrator | `backend/core/orchestrator.py` | DebateConfig | DebateResult |
| LLM Gateway | `backend/core/llm_gateway.py` | AgentConfig + messages | str (streamed) |
| Prompt Builder | `backend/core/prompt_builder.py` | Agent + Config + History | list[dict] (messages) |
| Response Parser | `backend/core/response_parser.py` | raw str | ParsedResponse |
| Judge | `backend/core/judge.py` | Debate (full history) | JudgeVerdict / Synthesis |
| Web Search | `backend/core/web_search.py` | query str | SearchContext |
| Storage | `backend/storage/` | Pydantic models | PostgreSQL rows |

### Провайдеры

Только два провайдера, прямые API-ключи через LiteLLM:
- **Anthropic:** `anthropic/claude-sonnet-4-20250514` (участники + судья)
- **OpenAI:** `openai/gpt-5.4` (участники)

### 4 агента по умолчанию

| ID | Провайдер | Persona | Temperature |
|----|-----------|---------|-------------|
| `claude-analyst` | anthropic | Строгий аналитик. Факты, evidence, скептицизм | 0.3 |
| `claude-creative` | anthropic | Креативный синтезатор. Неожиданные связи, гипотезы | 0.8 |
| `gpt-critic` | openai | Методологический критик. Логика, допущения, ошибки | 0.4 |
| `gpt-generalist` | openai | Широкий эрудит. Аналогии, смежные области, контекст | 0.6 |

Судья: отдельный вызов Sonnet (t=0.2), НЕ участник дебата. Использует ту же модель что claude-analyst/creative, но другой промт и температуру — это корректно.

## Контракт данных

### Ответ агента (гибридный JSON)

Ключи СТРОГО фиксированы — НЕ менять, НЕ переименовывать:

```
position          : str       — краткая позиция (1-2 предложения)
confidence        : str       — "high" | "medium" | "low"
position_changed  : bool
change_reason     : str
agreements        : list[obj] — [{with: str, point: str, why: str}]
disagreements     : list[obj] — [{with: str, point: str, counterargument: str}]
sources           : list[str] — URL
full_argument     : str       — свободный текст (Markdown)
```

**Раунд 1:** тот же формат. Поля `agreements`, `disagreements` = пустые, `position_changed` = false.
**Раунд 2+:** все поля заполняются.

### Вердикт судьи

```
round_number             : int
argument_novelty         : float (0.0–1.0)
position_changes         : list[str]
stagnation               : bool
convergence_points       : list[str]
remaining_disagreements  : list[str]
should_stop              : bool
stop_reason              : str | null — "consensus" | "stagnation" | "max_rounds"
```

### Анонимизация

Ответы оппонентов подаются моделям как Response A / Response B / Response C / Response D.
Маппинг `{"Response A": "claude-analyst", ...}` хранится в бэкенде.
Модели НИКОГДА не видят brand/id оппонента.

## Конфигурация (config/settings.yaml)

```yaml
database:
  dsn: "postgresql+asyncpg://user:pass@localhost:5432/sciproof"

brave_search:
  api_key: "${BRAVE_API_KEY}"
  max_results_per_query: 5

server:
  host: "0.0.0.0"
  port: 8001

limits:
  max_rounds: 5
  max_agents_per_debate: 6
  budget_default_usd: 5.0
```

## Стек

- Python 3.12, FastAPI, LiteLLM, SQLAlchemy 2.0 + asyncpg, Alembic, sse-starlette
- React 19, Vite 6
- PostgreSQL 16+
- Brave Search API
- Jinja2 для шаблонов промтов
- pytest + httpx для тестов

## Структура проекта

```
sciproof/
├── backend/
│   ├── main.py
│   ├── config.py              # Pydantic Settings, загрузка YAML
│   ├── auth.py
│   ├── api/
│   │   ├── debates.py
│   │   ├── agents.py
│   │   └── metrics.py
│   ├── core/
│   │   ├── orchestrator.py
│   │   ├── llm_gateway.py
│   │   ├── judge.py
│   │   ├── web_search.py
│   │   ├── prompt_builder.py
│   │   └── response_parser.py
│   ├── models/                # Pydantic
│   │   ├── agent.py
│   │   ├── debate.py
│   │   ├── response.py
│   │   └── events.py
│   ├── storage/
│   │   ├── database.py
│   │   ├── models_db.py       # SQLAlchemy ORM
│   │   └── queries.py
│   ├── prompts/               # Jinja2
│   │   ├── system_debate.jinja2
│   │   ├── system_consensus.jinja2
│   │   ├── system_devil.jinja2
│   │   ├── system_expert.jinja2
│   │   ├── system_review.jinja2
│   │   ├── format_json.jinja2
│   │   ├── round_n.jinja2
│   │   ├── skeptic_addon.jinja2
│   │   ├── judge_round.jinja2
│   │   └── judge_synthesis.jinja2
│   ├── alembic/
│   └── tests/
│       ├── test_orchestrator.py
│       ├── test_response_parser.py
│       ├── test_prompt_builder.py
│       └── integration/
│           ├── test_full_debate.py
│           └── test_data.py
├── frontend/
│   └── src/
│       ├── App.jsx
│       └── components/
├── config/
│   ├── agents.yaml            # GITIGNORED — API-ключи + агенты
│   ├── agents.example.yaml    # Пример без ключей (в git)
│   └── settings.yaml          # PostgreSQL DSN, Brave API key, порты, лимиты
├── alembic.ini                # Alembic config (PostgreSQL migrations)
├── requirements.txt
├── docker-compose.yml
└── Dockerfile
```

## Важно: __init__.py

Каждая директория-пакет (`backend/`, `backend/core/`, `backend/models/`, `backend/storage/`, `backend/api/`) ДОЛЖНА содержать `__init__.py` (может быть пустым). Без них Python не найдёт импорты.

## Правила разработки

1. **Контракт данных — из этого файла.** НЕ изобретать новые имена полей. Если нужно новое поле — сначала обновить CLAUDE.md.
2. **Интеграционный тест ОБЯЗАТЕЛЕН** при создании/изменении любого компонента. Не юнит-тест в изоляции, а прогон через pipeline.
3. **Промты — на русском.** Ключи JSON — на английском (для парсинга).
4. **Шаблоны промтов — Jinja2** в `backend/prompts/`. Не хардкодить текст промтов в Python-коде.
5. **Async everywhere.** Все LLM-вызовы, все БД-запросы — async. Никаких синхронных блокировок.
6. **Response Parser — 3 fallback:** чистый JSON → JSON из markdown code block → свободный текст. Никогда не падать на невалидном JSON.
7. **Validate on Exit.** Финальная валидация данных перед отдачей клиенту, не на каждом шаге.
8. **Каждый коммит — рабочее состояние.** Не коммитить сломанное.
9. **requirements.txt актуален.** Каждая новая зависимость — сразу в файл.
10. **Никаких правок на сервере.** Все изменения через Claude Code → git → deploy.

## Ограничения

- НЕ использовать LangChain, CrewAI или другие фреймворки поверх LiteLLM
- НЕ использовать SQLite — только PostgreSQL
- НЕ использовать WebSocket — только SSE для стриминга
- НЕ хардкодить API-ключи, модели, URL — всё из config/
- НЕ создавать локальных моделей / Ollama интеграций
- НЕ менять структуру гибридного JSON ответа без обновления CLAUDE.md
