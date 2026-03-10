# SciProof Service Flow

## Основная схема

```mermaid
flowchart TD
    U["Пользователь"] --> FE["Frontend (React + Vite)"]
    FE --> API["Backend API (FastAPI)"]
    API --> ORCH["SessionOrchestrator"]

    ORCH --> PB["PromptBuilder (Jinja2 prompts)"]
    ORCH --> WS["WebSearch (Brave API)"]
    ORCH --> G1["LLM Gateway -> Anthropic"]
    ORCH --> G2["LLM Gateway -> OpenAI"]
    ORCH --> JP["Judge"]
    ORCH --> RP["ResponseParser"]

    G1 --> A1["claude-analyst\nAnthropic Claude Sonnet\nТип: analytical reviewer"]
    G1 --> A2["claude-creative\nAnthropic Claude Sonnet\nТип: rewriting / synthesis"]

    G2 --> A3["gpt-critic\nOpenAI GPT-5.4\nТип: methodological critic"]
    G2 --> A4["gpt-generalist\nOpenAI GPT-5.4\nТип: broad-context reviewer"]

    JP --> J1["judge\nAnthropic Claude Sonnet\nТип: evaluator / synthesizer"]

    A1 --> RP
    A2 --> RP
    A3 --> RP
    A4 --> RP
    RP --> ORCH
    ORCH --> FE
    FE --> U
```

## Цикл работы review_text

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as FastAPI
    participant O as Orchestrator
    participant W as Brave Search
    participant C as Claude Agents
    participant G as GPT Agents
    participant J as Judge

    U->>FE: Вставляет текст + задачу + контекст
    FE->>API: POST /api/sessions
    API->>O: SessionConfig
    O->>W: search(query) if web_search=true
    O->>C: Раунд 1
    O->>G: Раунд 1
    C-->>O: JSON ответы
    G-->>O: JSON ответы
    O->>J: Оценить раунд
    J-->>O: JudgeVerdict

    alt Недостаточно контекста
        O-->>API: status=needs_user_input + clarification_requests
        API-->>FE: вопросы пользователю
        FE-->>U: показать вопросы
    else Контекста достаточно
        O->>C: Раунд 2+ с анонимизированными ответами
        O->>G: Раунд 2+ с анонимизированными ответами
        C-->>O: revised_text + issues + sources
        G-->>O: revised_text + issues + sources
        O->>J: Финальный синтез
        J-->>O: summary + revised_text + key_changes
        O-->>API: SessionResult
        API-->>FE: completed
        FE-->>U: показать итоговую редакцию
    end
```

## Какие модели используются

| Узел | Модель | Провайдер | Роль модели | Тип |
|------|--------|-----------|-------------|-----|
| `claude-analyst` | `anthropic/claude-sonnet-4-6` | Anthropic | проверка фактов, логики, доказательности | analytical reviewer |
| `claude-creative` | `anthropic/claude-sonnet-4-6` | Anthropic | переписывание, синтез, улучшение формулировок | rewriting / synthesis |
| `gpt-critic` | `openai/gpt-5.4` | OpenAI | критика допущений, структуры и аргументации | methodological critic |
| `gpt-generalist` | `openai/gpt-5.4` | OpenAI | широкий контекст, деловой и междисциплинарный взгляд | generalist reviewer |
| `judge` | `anthropic/claude-sonnet-4-6` | Anthropic | вердикт раунда, остановка, финальный синтез | evaluator / synthesizer |

## Какие виды моделей НЕ используются сейчас

- локальные модели;
- эмбеддинги;
- reranker;
- OCR / vision models;
- speech models;
- LangChain / CrewAI orchestration layers.

## Где что применяется

- Frontend: только UI, моделей нет.
- FastAPI: только API и маршрутизация, моделей нет.
- PromptBuilder: не модель, а шаблонизация промтов.
- ResponseParser: не модель, а парсинг JSON/fallback.
- WebSearch: Brave Search API, не LLM.
- LLM Gateway: единая точка вызова frontier LLM.
- Judge: отдельный LLM-вызов той же Anthropic модели, но с другой ролью.
