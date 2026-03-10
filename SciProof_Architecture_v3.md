# SciProof: Архитектура и стек
## Software Design Document v2

**Версия:** 3.0  
**Дата:** 2026-03-10  
**Статус:** Проектирование  
**Основание:** LLM_Debate_Requirements_v2.md (v2.3)  
**Изменения v3.0:** финальная ревизия — согласование порядка шагов с PROMPTS.md, settings.yaml, __init__.py, sse-starlette, DDL дополнения

---

## 1. Стек технологий

### 1.1. Принятые решения

| Слой | Технология | Версия | Обоснование |
|------|-----------|--------|-------------|
| **Backend** | FastAPI | 0.115+ | Async из коробки, SSE, OpenAPI docs |
| **Frontend** | React + Vite | React 19, Vite 6 | Компонентный UI для side-by-side раундов |
| **LLM-маршрутизация** | LiteLLM | 1.60+ | Единый интерфейс. Async. Трекинг стоимости |
| **Web search** | Brave Search API | — | Интегрирован в OpenClaw, ключ есть |
| **БД** | PostgreSQL | 16+ | Уже в инфраструктуре SciMap. Единая БД |
| **ORM** | SQLAlchemy 2.0 + asyncpg | — | Async, миграции через Alembic |
| **Язык** | Python 3.12 | — | Единый для бэкенда, тестов, LLM-вызовов |
| **Стриминг** | SSE (sse-starlette) | 2.0+ | Однонаправленный стриминг ответов |
| **Конфигурация** | YAML + Pydantic | — | Агенты, ключи, дефолты. Валидация |
| **Тестирование** | pytest + httpx | — | Интеграционные тесты через полный pipeline |

### 1.2. Отброшенные варианты

| Компонент | Отброшен | Причина |
|-----------|----------|---------|
| OpenRouter | → LiteLLM + прямые ключи | Лишняя прослойка, свои ключи есть |
| SQLite | → PostgreSQL | Уже в инфраструктуре SciMap, единая БД |
| Ollama / локальные модели | Убраны | Только frontier API-модели. Упрощение |
| DeepSeek, Google | Убраны | 2 провайдера × 2 агента = 4 участника. Достаточно |
| Django | → FastAPI | Overkill, нет нативного async |
| WebSocket | → SSE | Двусторонний канал не нужен |
| LangChain | → Чистый LiteLLM | Абстракции без пользы |
| Next.js | → React + Vite | SPA достаточно |

---

## 2. Ключевое решение: агенты, не модели

### 2.1. Концепция

**Агент = модель + температура + системный промт + роль.**

Две frontier-модели (Claude, GPT) порождают 4 агента с разными «характерами». Разнообразие достигается не разными вендорами, а разными настройками одной модели. Это дешевле, проще в поддержке и даёт контролируемое разнообразие.

### 2.2. Конфигурация агентов по умолчанию

```yaml
providers:
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    model: "claude-sonnet-4-6"   # Фаза 0: Sonnet. Upgrade → Opus если нужно
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-5.4"

agents:
  claude-analyst:
    provider: anthropic
    display_name: "Аналитик (Claude)"
    temperature: 0.3
    persona: >
      Ты — строгий аналитик. Опираешься на факты и источники.
      Скептически относишься к утверждениям без evidence.
      Предпочитаешь точность широте охвата.
    default_role: analyst

  claude-creative:
    provider: anthropic
    display_name: "Синтезатор (Claude)"
    temperature: 0.8
    persona: >
      Ты — креативный синтезатор. Ищешь неожиданные связи между идеями.
      Предлагаешь нестандартные интерпретации.
      Не боишься спекулятивных гипотез, но маркируешь их как гипотезы.
    default_role: synthesizer

  gpt-critic:
    provider: openai
    display_name: "Критик (GPT)"
    temperature: 0.4
    persona: >
      Ты — методологический критик. Проверяешь логику аргументации.
      Ищешь скрытые допущения, ошибки вывода, недостаточную обоснованность.
      Если аргумент строгий — признаёшь это.
    default_role: critic

  gpt-generalist:
    provider: openai
    display_name: "Эрудит (GPT)"
    temperature: 0.6
    persona: >
      Ты — широкий эрудит. Привлекаешь данные из смежных областей.
      Проводишь аналогии. Контекстуализируешь проблему в более
      широкой картине. Приводишь примеры из других дисциплин.
    default_role: generalist

judge:
  provider: anthropic
  model: "claude-sonnet-4-6"     # Фаза 0: Sonnet. Upgrade → Opus если нужно
  temperature: 0.2                       # Низкая: судья должен быть стабилен
  display_name: "Судья"
```

### 2.3. Почему это работает

- **Разнообразие температуры:** 0.3 (детерминированный аналитик) vs 0.8 (креативный синтезатор) — гарантирует разные ракурсы даже на одном вопросе
- **Разнообразие persona:** critic ищет дыры, generalist расширяет контекст, analyst сужает до фактов, synthesizer строит мосты
- **Два провайдера:** разные training data → разные «слепые пятна» → взаимная коррекция
- **Анонимизация работает:** модели не знают, что 2 из 4 оппонентов — тот же вендор с другой температурой

### 2.4. Пользователь может менять

- Какие агенты участвуют (чекбоксы, минимум 2)
- Persona каждого агента (редактирование текста)
- Температуру
- Модель провайдера (например, переключить Anthropic на Opus)
- Создавать кастомных агентов

---

## 3. Структурная схема

```
┌──────────────────────────────────────────────────────────────┐
│                        ПОЛЬЗОВАТЕЛЬ                          │
│                      (браузер, 3–4 чел.)                     │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP / SSE
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + Vite)                   │
│                                                               │
│  ┌─────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Список   │  │ Создание     │  │ Дебат    │  │ Настройки│ │
│  │ дебатов  │  │ дебата       │  │ (live)   │  │          │ │
│  └─────────┘  └──────────────┘  └──────────┘  └──────────┘ │
│                                                               │
│  SSE-клиент │ Markdown renderer │ JSON metadata parser       │
└──────────────────────────┬───────────────────────────────────┘
                           │ REST API + SSE
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                          │
│                                                               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │ API Router     │  │ Debate         │  │ Auth           │ │
│  │ (endpoints)    │  │ Orchestrator   │  │ (simple token) │ │
│  └───────┬────────┘  └───────┬────────┘  └────────────────┘ │
│          │                   │                                │
│          │    ┌──────────────┼──────────────┐                │
│          │    │              │              │                 │
│          ▼    ▼              ▼              ▼                 │
│  ┌────────────────┐  ┌────────────┐  ┌────────────────┐     │
│  │ LLM Gateway    │  │ Judge      │  │ Web Search     │     │
│  │ (LiteLLM)      │  │ Module     │  │ (Brave API)    │     │
│  └───────┬────────┘  └────────────┘  └────────────────┘     │
│          │                                                    │
│  ┌────────────────┐  ┌────────────────┐                      │
│  │ Prompt Builder │  │ Response       │                      │
│  │ (templates)    │  │ Parser (JSON)  │                      │
│  └────────────────┘  └────────────────┘                      │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                   Storage Layer                         │  │
│  │  PostgreSQL: debates, rounds, responses, metrics, users │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                           │
                     ┌─────┴─────┐
                     │           │
                     ▼           ▼
               ┌──────────┐ ┌──────────┐
               │ Anthropic│ │ OpenAI   │
               │ API      │ │ API      │
               └──────────┘ └──────────┘
```

### 3.1. Описание компонентов

| Компонент | Что делает | С чем связан |
|-----------|-----------|-------------|
| **Frontend** | SPA: создание дебатов, отображение раундов side-by-side, стриминг, экспорт | → Backend (REST + SSE) |
| **API Router** | Маршрутизация HTTP, валидация, SSE-эндпоинты | → Orchestrator, → Storage, → Auth |
| **Debate Orchestrator** | Ядро: управляет раундами, параллельными вызовами агентов, стоп-критериями | → LLM Gateway, → Judge, → Web Search, → Prompt Builder, → Response Parser |
| **LLM Gateway** | Единый интерфейс к Anthropic и OpenAI через LiteLLM. Async, стриминг, retry, трекинг | → Anthropic API, → OpenAI API |
| **Judge Module** | LLM-судья: оценка раундов, автодетект сходимости, финальный синтез | → LLM Gateway |
| **Web Search** | Поиск через Brave API. Раунд 0 + tool use | → Brave Search API |
| **Prompt Builder** | Сборка промтов: persona агента + системный + контекст + история + анонимизация | ← Orchestrator |
| **Response Parser** | Парсинг гибридного JSON. 3 уровня fallback | ← Orchestrator |
| **Storage** | PostgreSQL: дебаты, раунды, ответы, метрики, пользователи | ← API Router, ← Orchestrator |
| **Auth** | Простая аутентификация: токен в header | ← API Router |

### 3.2. Внешние зависимости

| Зависимость | Зачем | Что будет без неё |
|-------------|-------|-------------------|
| Anthropic API | 2 агента (analyst + synthesizer) + судья | Дебат только на GPT-агентах (2 из 4) |
| OpenAI API | 2 агента (critic + generalist) | Дебат только на Claude-агентах (2 из 4) |
| Brave Search API | Web search в раундах | Дебат без web search (работает, но хуже) |
| PostgreSQL | Хранение всех данных | Сервис не работает |

**Минимум для дебата:** 2 любых агента (даже оба от одного провайдера).

---

## 4. Компоненты: детальное описание

### 4.1. Debate Orchestrator (ядро)

**Роль:** управляет жизненным циклом дебата.

**Ключевое отличие от модели «1 модель = 1 участник»:** оркестратор работает с агентами. Каждый агент несёт свой persona + temperature. Prompt Builder собирает финальный промт = persona агента + системная инструкция режима + контекст + история.

```python
async def run_debate(config: DebateConfig) -> DebateResult:
    debate = create_debate(config)
    
    # Раунд 0: web search (если включён)
    if config.web_search_enabled:
        debate.shared_context = await web_search.search(config.question)
    
    # Раунд 1: независимые ответы (параллельно)
    round_1 = await asyncio.gather(*[
        llm_gateway.call(
            agent=agent,
            messages=prompt_builder.round_1(agent, config, debate.shared_context)
        )
        for agent in config.agents
    ])
    debate.add_round(1, round_1)
    
    # Раунды 2+
    for round_num in range(2, config.max_rounds + 1):
        prev = debate.get_round(round_num - 1)
        anonymized = prompt_builder.anonymize(prev)  # Response A/B/C/D
        skeptic = debate.get_skeptic(round_num)       # Ротация
        
        round_n = await asyncio.gather(*[
            llm_gateway.call(
                agent=agent,
                messages=prompt_builder.round_n(
                    agent, config, debate.history, anonymized,
                    is_skeptic=(agent.id == skeptic.id)
                )
            )
            for agent in config.agents
        ])
        debate.add_round(round_num, round_n)
        
        # Судья
        verdict = await judge.evaluate_round(debate)
        debate.add_verdict(round_num, verdict)
        
        if verdict.should_stop:
            break
        
        if config.pause_between_rounds:
            await debate.wait_for_user_action()
    
    # Синтез
    debate.synthesis = await judge.synthesize(debate)
    return debate.to_result()
```

### 4.2. LLM Gateway

**На основе LiteLLM. Работает с агентами, не моделями:**

```python
async def call(
    agent: AgentConfig,
    messages: list[dict],
    stream: bool = True,
) -> AsyncGenerator[str, None] | str:
    """Вызов агента: модель из провайдера + температура агента."""
    provider = providers[agent.provider]
    
    response = await litellm.acompletion(
        model=provider.litellm_model_id,
        messages=messages,
        stream=stream,
        max_tokens=4096,
        temperature=agent.temperature,
        api_key=provider.api_key,
    )
    # ... стриминг или полный ответ
```

**Маппинг провайдеров:**

```yaml
providers:
  anthropic:
    litellm_model_id: "anthropic/claude-sonnet-4-6"
    cost_input_per_1m: 3.0
    cost_output_per_1m: 15.0
    max_context: 200000
    
  openai:
    litellm_model_id: "openai/gpt-5.4"
    cost_input_per_1m: 2.5
    cost_output_per_1m: 10.0
    max_context: 128000
```

### 4.3. Prompt Builder

**Ключевое:** промт = persona агента + инструкция режима + контекст. Persona — «характер» агента, не зависит от режима. Инструкция режима — структура дебата (debate/consensus/devil's advocate/...).

**Сборка промта для раунда 2+:**

```python
def round_n(self, agent, config, history, anonymized, is_skeptic) -> list[dict]:
    system = self._build_system(agent, config, is_skeptic)
    user = self._build_round_n_user(history, anonymized)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user}
    ]

def _build_system(self, agent, config, is_skeptic) -> str:
    """persona + режим + формат + (опц.) скептик."""
    parts = [
        agent.persona,                              # «Ты строгий аналитик...»
        self._load_template(f"system_{config.mode}"),  # Инструкция режима
        self._load_template("format_json"),          # Формат JSON-ответа
    ]
    if is_skeptic:
        parts.append(self._load_template("skeptic_addon"))
    return "\n\n".join(parts)
```

**Анонимизация:** Response A/B/C/D. Маппинг хранится на бэкенде. Модели не знают ни brand оппонента, ни что 2 из 4 — тот же вендор.

### 4.4. Response Parser

Без изменений: 3 уровня fallback (чистый JSON → JSON из markdown → свободный текст). Метрика `parse_quality` трекается **по агенту** (не по модели) — видно, какая комбинация persona+temperature лучше следует формату.

### 4.5. Judge Module

**Модель судьи:** Claude Sonnet 4.6 (Фаза 0). Upgrade на Opus если качество недостаточно.

**Температура судьи:** 0.2 (стабильность важнее креативности).

**Судья НЕ является агентом-участником.** Отдельный вызов, видит все раунды, не имеет persona кроме «нейтральный аналитик».

**Два режима:**

A. **Вердикт раунда** (~500 токенов output):
```json
{
  "round_number": 2,
  "argument_novelty": 0.7,
  "position_changes": ["Response A изменил позицию по пункту X"],
  "stagnation": false,
  "convergence_points": ["все согласны что Y"],
  "remaining_disagreements": ["X vs Z по вопросу W"],
  "should_stop": false,
  "stop_reason": null
}
```

B. **Финальный синтез** (~2000 токенов output): 7 блоков из §6.1 требований.

### 4.6. Web Search Module

Brave Search API. Два режима: общий контекст (раунд 0) + tool use (по запросу агента в раунде). Max 3 поиска на раунд на агента.

### 4.7. Storage Layer

**PostgreSQL, 5 таблиц:**

```sql
CREATE TABLE debates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    context TEXT,
    mode TEXT NOT NULL DEFAULT 'debate',
    agents JSONB NOT NULL,              -- конфигурация агентов этого дебата
    config JSONB NOT NULL,              -- {max_rounds, web_search, ...}
    status TEXT DEFAULT 'active',       -- active | paused | completed | aborted
    synthesis JSONB,                    -- финальный синтез
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd NUMERIC(10,6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    created_by TEXT
);

CREATE TABLE rounds (
    id SERIAL PRIMARY KEY,
    debate_id UUID REFERENCES debates(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    search_context JSONB,               -- результаты web search
    judge_verdict JSONB,                -- оценка судьи
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE responses (
    id SERIAL PRIMARY KEY,
    round_id INTEGER REFERENCES rounds(id) ON DELETE CASCADE,
    debate_id UUID REFERENCES debates(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,             -- "claude-analyst", "gpt-critic", ...
    provider TEXT NOT NULL,             -- "anthropic", "openai"
    anonymous_label TEXT,               -- "Response A", "Response B", ...
    raw_content TEXT NOT NULL,
    parsed_json JSONB,                  -- распарсенные метаданные
    parse_quality TEXT,                 -- json_clean | json_extracted | free_text_fallback
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_usd NUMERIC(10,6),
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE metrics (
    id SERIAL PRIMARY KEY,
    debate_id UUID REFERENCES debates(id) ON DELETE CASCADE,
    round_number INTEGER,
    metric_name TEXT NOT NULL,
    metric_value NUMERIC,
    details JSONB
);

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',           -- admin | user
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 5. Контракты данных

### 5.1. Конфигурация дебата (Frontend → Backend)

```json
{
  "question": "Текст вопроса",
  "context": "Дополнительный контекст (опц.)",
  "document_base64": "base64-содержимое файла (опц.)",
  "mode": "debate",
  "agents": ["claude-analyst", "claude-creative", "gpt-critic", "gpt-generalist"],
  "max_rounds": 3,
  "web_search": true,
  "web_search_mode": "round_0",
  "budget_usd": 5.0,
  "pause_between_rounds": false,
  "language": "ru"
}
```

### 5.2. Ответ агента (LLM → Response Parser)

Гибридный JSON. Ключи фиксированы:

```
position          : str       — краткая позиция
confidence        : str       — "high" | "medium" | "low"
position_changed  : bool
change_reason     : str
agreements        : list[obj] — [{with, point, why}]
disagreements     : list[obj] — [{with, point, counterargument}]
sources           : list[str]
full_argument     : str       — свободный текст
```

### 5.3. SSE-события (Backend → Frontend)

```
event: round_start       data: {round, agents}
event: response_chunk    data: {round, agent_id, chunk}
event: response_complete data: {round, agent_id, parsed, tokens, cost}
event: judge_verdict     data: {round, verdict}
event: round_complete    data: {round, all_parsed}
event: synthesis_complete data: {synthesis}
event: debate_complete   data: {debate_id, total_cost, total_tokens}
event: error             data: {agent_id, error, debate_continues}
```

---

## 6. API-эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/debates` | Создать и запустить дебат |
| GET | `/api/debates` | Список дебатов (с фильтрацией) |
| GET | `/api/debates/{id}` | Полные данные дебата |
| GET | `/api/debates/{id}/stream` | SSE-стрим текущего дебата |
| POST | `/api/debates/{id}/intervene` | Вмешательство между раундами |
| POST | `/api/debates/{id}/stop` | Остановить → синтез |
| POST | `/api/debates/{id}/retry-round` | Повторить последний раунд |
| DELETE | `/api/debates/{id}` | Удалить дебат |
| GET | `/api/debates/{id}/export/{format}` | Экспорт: md / json / pdf |
| GET | `/api/agents` | Список агентов + конфигурация |
| PUT | `/api/agents/{id}` | Изменить агента (persona, temperature) |
| POST | `/api/agents` | Создать кастомного агента |
| GET | `/api/providers/health` | Проверка доступности API |
| GET | `/api/metrics/summary` | Сводная статистика |
| POST | `/api/auth/login` | Аутентификация |

---

## 7. Поток данных: полный цикл

```
1. Пользователь → POST /api/debates
   {question, agents: [...], mode, max_rounds}
                    │
2. Orchestrator: создаёт debate в PostgreSQL (status=active)
                    │
3. [web_search] → Brave API → shared_context
                    │
4. Prompt Builder: для каждого агента:
   persona + system_mode + question + context
                    │
5. LLM Gateway: asyncio.gather(agent_1, agent_2, agent_3, agent_4)
   │ параллельно, стриминг через SSE
                    │
6. Response Parser: raw → ParsedResponse (3 fallback)
                    │
7. Storage: сохранить round + responses в PostgreSQL
                    │
8. Judge: evaluate_round → verdict
   │ SSE: judge_verdict
                    │
9. Стоп? ── нет ──→ Prompt Builder: anonymize + round_n + persona
   │                                  │
   │ да                        ───→ шаг 5
   │
10. Judge: synthesize → synthesis
    │ SSE: debate_complete
                    │
11. Storage: обновить debate (status=completed)
```

---

## 8. Структура проекта

```
sciproof/
├── backend/                   # Все директории-пакеты содержат __init__.py
│   ├── main.py                    # FastAPI app, startup, CORS
│   ├── config.py                  # Pydantic Settings, загрузка YAML
│   ├── auth.py                    # Простая аутентификация
│   ├── api/
│   │   ├── debates.py             # REST-эндпоинты дебатов
│   │   ├── agents.py              # Эндпоинты управления агентами
│   │   └── metrics.py             # Эндпоинты метрик
│   ├── core/
│   │   ├── orchestrator.py        # Debate Orchestrator (ядро)
│   │   ├── llm_gateway.py         # LiteLLM wrapper
│   │   ├── judge.py               # LLM-судья
│   │   ├── web_search.py          # Brave Search API
│   │   ├── prompt_builder.py      # Сборка промтов, persona, анонимизация
│   │   └── response_parser.py     # Парсинг гибридного JSON
│   ├── models/                    # Pydantic-модели данных
│   │   ├── agent.py               # AgentConfig, ProviderConfig
│   │   ├── debate.py              # DebateConfig, DebateResult
│   │   ├── response.py            # ParsedResponse, JudgeVerdict
│   │   └── events.py              # SSE-события
│   ├── storage/
│   │   ├── database.py            # PostgreSQL init, async engine
│   │   ├── models_db.py           # SQLAlchemy ORM models
│   │   └── queries.py             # CRUD-операции
│   ├── prompts/                   # Jinja2-шаблоны
│   │   ├── system_debate.jinja2
│   │   ├── system_consensus.jinja2
│   │   ├── system_devil.jinja2
│   │   ├── system_expert.jinja2
│   │   ├── system_review.jinja2
│   │   ├── format_json.jinja2     # Инструкция формата ответа
│   │   ├── round_n.jinja2
│   │   ├── skeptic_addon.jinja2
│   │   ├── judge_round.jinja2
│   │   └── judge_synthesis.jinja2
│   ├── alembic/                   # Миграции PostgreSQL
│   │   └── versions/
│   └── tests/
│       ├── test_orchestrator.py
│       ├── test_response_parser.py
│       ├── test_prompt_builder.py
│       └── integration/
│           ├── test_full_debate.py
│           └── test_data.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── DebateList.jsx
│   │   │   ├── DebateCreate.jsx
│   │   │   ├── DebateView.jsx
│   │   │   ├── RoundDisplay.jsx
│   │   │   ├── ResponseCard.jsx   # Карточка: persona badge + content
│   │   │   ├── SynthesisView.jsx
│   │   │   ├── InterventionPanel.jsx
│   │   │   ├── AgentConfig.jsx    # Настройка агентов
│   │   │   └── Settings.jsx
│   │   ├── hooks/
│   │   │   └── useSSE.js
│   │   └── utils/
│   │       └── markdown.js
│   ├── package.json
│   └── vite.config.js
├── config/
│   ├── agents.yaml                # GITIGNORED — API-ключи + агенты
│   ├── agents.example.yaml        # Пример без ключей (в git)
│   └── settings.yaml              # PostgreSQL DSN, Brave API key, порты, лимиты
├── tests/
│   └── e2e/
├── scripts/
│   ├── init_db.py                 # PostgreSQL: создание таблиц
│   └── export_debate.py           # CLI-экспорт в Markdown
├── alembic.ini
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── README.md
└── PROJECT_CARD.md
```

---

## 9. Стратегия развёртывания

### 9.1. Схема развёртывания

```
Фаза 0: ЛОКАЛЬНАЯ МАШИНА (разработка)
  ├── Backend: FastAPI на localhost:8001
  ├── Frontend: Vite dev server на localhost:5173
  ├── PostgreSQL: localhost:5432 (уже для SciMap)
  ├── API-ключи: в config/agents.yaml (gitignored)
  └── Доступ: localhost

Фаза 1+: ДВА СЕРВЕРА
  
  DE-сервер (Германия, Coolify):
    ├── SciProof: Docker Compose (backend + frontend + nginx)
    ├── PostgreSQL: на DE-сервере
    ├── API Anthropic/OpenAI: прямой доступ без VPN
    └── Не доступен из РФ напрямую

  RU-сервер (Россия, VPS, nginx):
    ├── Только nginx reverse proxy
    ├── Проксирует всё на DE-сервер
    ├── HTTPS + Let's Encrypt
    └── Точка входа для пользователей из РФ

  Схема доступа:
    Пользователь (РФ) → ru-server (nginx) → de-server (SciProof)
```

### 9.2. Nginx на RU-сервере (минимальный конфиг)

```nginx
server {
    listen 443 ssl;
    server_name sciproof.example.ru;

    ssl_certificate     /etc/letsencrypt/live/sciproof.example.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sciproof.example.ru/privkey.pem;

    location / {
        proxy_pass https://de-server-ip:443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # SSE: отключить буферизацию
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

### 9.3. PostgreSQL: отдельная БД

Раздельные БД на одном PostgreSQL (DE-сервер): `scimap` и `sciproof`. Изоляция без накладных расходов.

### 9.4. Порядок переноса на сервер

```
1. Разработка и тестирование на локалке
2. Dockerfile + docker-compose.yml — проверить локально
3. git push → Coolify (DE-сервер)
4. PostgreSQL: создать БД sciproof, alembic upgrade head
5. HTTPS на DE-сервере
6. RU-сервер: nginx reverse proxy → DE-сервер
7. HTTPS на RU-сервере (Let's Encrypt)
8. Проверить: SSE-стриминг работает через прокси
```

---

## 10. Стратегия разработки (Фаза 0)

### 10.1. Порядок реализации

```
Неделя 1:
  Шаг 1: config.py + agents.yaml + Pydantic-модели (AgentConfig, DebateConfig)
         (контракт данных — ДО кода)
  Шаг 2: llm_gateway.py — LiteLLM wrapper, тест: 4 агента отвечают на один вопрос
  Шаг 3: response_parser.py — парсинг с 3 уровнями fallback
  Шаг 4: prompt_builder.py — persona + system_mode + format_json + анонимизация
  Шаг 5: orchestrator.py — минимальный цикл: 1 вопрос → 4 агента → 2 раунда
         ИНТЕГРАЦИОННЫЙ ТЕСТ: полный дебат через CLI

Неделя 2:
  Шаг 6: judge.py — вердикт раунда + финальный синтез
  Шаг 7: storage/ — PostgreSQL, SQLAlchemy models, Alembic
  Шаг 8: web_search.py — Brave API
  Шаг 9: scripts/export_debate.py — экспорт в Markdown
  Шаг 10: ФИНАЛЬНАЯ ВАЛИДАЦИЯ — 3 полных дебата, чеклист готовности
```

### 10.2. Тестовые вопросы

```python
TEST_QUESTIONS = [
    {
        "id": "factual_dispute",
        "question": "Каковы аргументы за и против OSL-датирования лёссов старше 100 тыс. лет?",
        "expected": "Analyst — факты, Critic — методологические ограничения, Synthesizer — синтез, Generalist — контекст из смежных наук",
    },
    {
        "id": "architecture_choice", 
        "question": "Property graph vs RDF vs реляционная БД с JSONB для хранения научных claims — что выбрать?",
        "expected": "Разные агенты должны защищать разные позиции",
    },
    {
        "id": "methodology",
        "question": "Можно ли считать корреляцию двух разрезов доказанной на основании только литостратиграфии без абсолютных датировок?",
        "expected": "Critic должен найти слабые места в аргументации",
    },
    {
        "id": "interdisciplinary",
        "question": "Как связаны неотектонические движения и формирование речных террас? Какие модели наиболее обоснованы?",
        "expected": "Generalist привлекает данные из тектоники, геофизики",
    },
    {
        "id": "brainstorm",
        "question": "Как организовать кураторский контур для научного knowledge graph?",
        "mode": "consensus",
        "expected": "Convergence к конкретному предложению",
    },
]
```

### 10.3. Критерии готовности Фазы 0

- [ ] 2 провайдера работают через LiteLLM (Anthropic, OpenAI)
- [ ] 4 агента с разными persona дают различающиеся ответы на один вопрос
- [ ] Дебат из 3 раундов с 4 агентами завершается без ошибок
- [ ] JSON-метаданные парсятся у ≥80% ответов
- [ ] Судья выдаёт verdict после каждого раунда
- [ ] Финальный синтез содержит все 7 блоков из §6.1 требований
- [ ] Стоимость типичного дебата: $1–3
- [ ] Экспорт в Markdown читаем
- [ ] Исследователь: «полезнее одиночного ответа» на 3+ из 5 вопросов
- [ ] Persona агентов влияют на характер ответов (analyst ≠ synthesizer)
