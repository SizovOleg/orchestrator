# AGENTS.md — SciProof

## Проект

SciProof — мульти-агентный сервис для коллективной проверки, обсуждения и корректировки текстов.

Основной сценарий:
- пользователь вставляет крупный блок научного или делового текста;
- 4 LLM-агента независимо рецензируют его, затем обсуждают между собой;
- при нехватке данных агенты формируют уточняющие вопросы пользователю;
- после уточнения контекста агенты выдают исправленный текст, пояснения к правкам, спорные места и фактчекинг по возможности.

Второй обязательный сценарий:
- проверка конкретного факта, тезиса или утверждения с привлечением web search.

Типичный размер текста для локального MVP:
- 1–2 страницы;
- примерно 3 000–4 000 знаков.

По умолчанию:
- авторская стилистика сохраняется;
- глубокая переработка структуры делается только по явному запросу пользователя.

## Базовый workflow

```text
Пользователь → загружает текст / утверждение + задачу + контекст
            → Раунд 1: независимый review 4 агентов
            → Если контекста не хватает: список уточняющих вопросов пользователю
            → Пользователь отвечает
            → Раунд 2+: перекрёстное обсуждение и корректировка
            → Судья оценивает сходимость и качество правок
            → Финал: исправленный текст + changelog + комментарии + фактчекинг
```

## Архитектура

```text
Frontend (React+Vite) → Backend (FastAPI) → LLM Gateway (LiteLLM) → Anthropic API / OpenAI API
                                          → Judge Module (Sonnet)
                                          → Web Search (Brave API)
                                          → PostgreSQL
```

### Компоненты бэкенда

| Компонент | Файл | Вход | Выход |
|-----------|------|------|-------|
| Orchestrator | `backend/core/orchestrator.py` | SessionConfig | SessionResult |
| LLM Gateway | `backend/core/llm_gateway.py` | AgentConfig + messages | str |
| Prompt Builder | `backend/core/prompt_builder.py` | Agent + Config + History | list[dict] |
| Response Parser | `backend/core/response_parser.py` | raw str | ParsedResponse |
| Judge | `backend/core/judge.py` | Session history | JudgeVerdict / JudgeSynthesis |
| Web Search | `backend/core/web_search.py` | query str | SearchContext |
| Storage | `backend/storage/` | Pydantic models | PostgreSQL rows |

## Провайдеры

Только два провайдера, прямые API-ключи через LiteLLM:
- **Anthropic:** `anthropic/claude-sonnet-4-20250514`
- **OpenAI:** `openai/gpt-5.4`

## 4 агента по умолчанию

| ID | Провайдер | Persona | Temperature |
|----|-----------|---------|-------------|
| `claude-analyst` | anthropic | Строгий аналитик. Факты, evidence, проверяемость | 0.3 |
| `claude-creative` | anthropic | Синтезатор. Перестройка текста, альтернативные формулировки | 0.8 |
| `gpt-critic` | openai | Методологический критик. Логика, допущения, слабые места | 0.4 |
| `gpt-generalist` | openai | Контекстный эрудит. Смежные области, прикладной и деловой контекст | 0.6 |

Судья:
- отдельный вызов Sonnet с `t=0.2`;
- судья не участвует в дебате как обычный агент.

## Основные режимы

### 1. `review_text`

Основной режим локального MVP.

Назначение:
- отредактировать и улучшить крупный текст;
- найти логические, стилистические, структурные и фактологические проблемы;
- при необходимости предложить переписанную версию текста.

### 2. `fact_check`

Проверка конкретного утверждения или небольшого фрагмента.

Назначение:
- проверить тезис;
- найти подтверждение / опровержение / неопределённость;
- выдать краткий исправленный вариант формулировки при необходимости.

## Контракт входа

`SessionConfig`:

```yaml
task_type: "review_text" | "fact_check"
question: str                  # что нужно сделать с текстом / какой тезис проверить
source_text: str               # для review_text обязателен; для fact_check опционален
context: str                   # дополнительный контекст от пользователя
preserve_style: bool           # default true
allow_restructure: bool        # default false
ask_clarifying_questions: bool # default true
mode: "debate" | "consensus" | "peer_review"
agents: list[str]
max_rounds: int                # 1-5
web_search: bool
budget_usd: float | null
language: str                  # default "ru"
```

Правила:
- для `review_text` поле `source_text` обязательно;
- для `fact_check` обязательно либо `question`, либо `source_text`, либо оба;
- по умолчанию сервис должен сохранять стиль автора;
- если `allow_restructure=true`, агенты могут заметно перестраивать композицию текста.

## Контракт ответа агента

Ответ агента — гибридный JSON. Ключи фиксированы.

```text
position               : str       — краткая позиция агента
confidence             : str       — "high" | "medium" | "low"
position_changed       : bool
change_reason          : str
agreements             : list[obj] — [{with: str, point: str, why: str}]
disagreements          : list[obj] — [{with: str, point: str, counterargument: str}]
issues                 : list[obj] — [{segment: str, problem: str, severity: str, suggestion: str}]
clarification_requests : list[str]
sources                : list[str] — URL
revised_text           : str       — полная исправленная версия текста или пустая строка
full_argument          : str       — свободный текст (Markdown)
```

Ограничения:
- `severity` только `high` | `medium` | `low`;
- `clarification_requests` заполняется, если агенту не хватает контекста;
- `revised_text` должен содержать полный исправленный текст, если агент считает, что контекста достаточно;
- если контекста не хватает, `revised_text` может быть пустым;
- в `fact_check` режиме `revised_text` можно использовать для исправленной формулировки тезиса.

**Раунд 1:**
- `agreements`, `disagreements` пустые;
- `position_changed = false`.

**Раунд 2+:**
- все поля должны быть заполнены содержательно;
- агент обязан указать хотя бы по одному слабому месту у каждого оппонента.

## Вердикт судьи

```text
round_number             : int
argument_novelty         : float (0.0–1.0)
position_changes         : list[str]
stagnation               : bool
convergence_points       : list[str]
remaining_disagreements  : list[str]
needs_user_input         : bool
clarification_requests   : list[str]
should_stop              : bool
stop_reason              : str | null — "consensus" | "stagnation" | "max_rounds" | "needs_user_input"
```

Если `needs_user_input=true`:
- оркестратор должен остановить автоматическое продолжение;
- пользователю показывается агрегированный список вопросов;
- после ответа пользователя запускается следующий раунд.

## Финальный синтез судьи

```text
summary               : str
revised_text          : str
key_changes           : list[str]
fact_check_summary    : list[str]
open_questions        : list[str]
remaining_disagreements: list[str]
sources               : list[str]
```

Требования:
- `revised_text` — итоговая согласованная версия текста;
- `key_changes` — краткий changelog;
- `fact_check_summary` — проверенные факты, спорные утверждения, неподтверждённые места;
- `open_questions` — что осталось неясным даже после дискуссии.

## Контракт результата сессии

```text
session_id             : str
status                 : "completed" | "needs_user_input"
task_type              : str
question               : str
source_text            : str
context                : str
rounds                 : list[RoundData]
clarification_requests : list[str]
synthesis              : JudgeSynthesis | null
total_tokens           : int
total_cost_usd         : float
```

Если `status = "needs_user_input"`:
- `synthesis = null`;
- `clarification_requests` заполнен;
- фронтенд должен показать вопросы и дать пользователю быстро перезапустить сессию с новым контекстом.

## Анонимизация

Ответы оппонентов подаются моделям как `Response A / B / C / D`.
Маппинг хранится только в бэкенде.
Модели никогда не видят реальные `agent_id`, brand и provider оппонента.

## Web Search

Web search обязателен как опция уже на уровне требований, потому что:
- нужен для фактчекинга научных и деловых утверждений;
- нужен для верификации спорных чисел, дат, ссылок и формулировок;
- должен быть отключаемым, если пользователь хочет review только по исходному тексту.

Правила:
- в `fact_check` режиме web search по умолчанию включён;
- в `review_text` режиме web search опционален и включается пользователем;
- при отсутствии search сервис не должен выдумывать источники.

## UI для локального MVP

Обязательный минимум:
- textarea для текста;
- textarea для задачи / вопроса;
- textarea для дополнительного контекста;
- переключатели:
  - `review_text` / `fact_check`
  - `preserve_style`
  - `allow_restructure`
  - `web_search`
- запуск процесса;
- экран уточняющих вопросов к пользователю;
- экран результата:
  - итоговый исправленный текст;
  - ключевые правки;
  - замечания агентов;
  - фактчекинг;
  - спорные места.

## Правила разработки

1. **Контракт данных — из этого файла.** Если нужно новое поле — сначала обновить AGENTS.md.
2. **Интеграционный тест обязателен** для любого изменённого компонента.
3. **Промты — на русском.** Ключи JSON — на английском.
4. **Шаблоны промтов — Jinja2** в `backend/prompts/`.
5. **Async everywhere.**
6. **Response Parser — 3 fallback:** чистый JSON → JSON из markdown code block → свободный текст.
7. **Validate on Exit.**
8. **Каждый коммит — рабочее состояние.**
9. **requirements.txt актуален.**
10. **Никаких правок на сервере.** Сначала локальная версия, потом перенос.

## Ограничения

- НЕ использовать LangChain, CrewAI и аналогичные фреймворки поверх LiteLLM
- НЕ использовать SQLite
- НЕ использовать WebSocket, если нужен стриминг; только SSE
- НЕ хардкодить API-ключи, модели и URL
- НЕ создавать локальные модели / Ollama интеграции
- НЕ менять структуру гибридного JSON ответа без обновления AGENTS.md
