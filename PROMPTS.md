# SciProof: Промты для Claude Code Desktop
## Фаза 0 — пошаговая разработка

**Использование:** копировать нужный промт → вставить в Claude Code Desktop.
Каждый промт самодостаточен (содержит контекст, задачу, контракт, тесты, ограничения).
Выполнять строго последовательно — каждый шаг зависит от предыдущего.

---

## СТАНДАРТНАЯ ПРЕАМБУЛА

**Вставляется в начало КАЖДОГО промта** (уже включена во все шаги ниже):

```
## Правила

1. Прочитай CLAUDE.md в корне проекта. Это источник истины по архитектуре, контрактам и правилам.
2. Составь план перед кодированием. Покажи мне план, дождись подтверждения.
3. Если видишь проблему в промте — скажи, не выполняй молча. Лучше спросить, чем сделать неправильно.
4. Имена полей и контракты данных НЕ менять. Если нужно новое поле — сначала скажи, обсудим.
5. После завершения и успешного тестирования — git add + git commit с осмысленным сообщением.
6. Тестирование обязательно. Юнит-тесты + интеграционные. Не коммитить если тесты падают.
```

---

## ШАГ 1: Инициализация проекта + Pydantic-модели

```
## Правила

1. Прочитай CLAUDE.md в корне проекта. Это источник истины по архитектуре, контрактам и правилам.
2. Составь план перед кодированием. Покажи мне план, дождись подтверждения.
3. Если видишь проблему в промте — скажи, не выполняй молча.
4. Имена полей и контракты данных НЕ менять.
5. После завершения и успешного тестирования — git add + git commit с осмысленным сообщением.
6. Тестирование обязательно. Не коммитить если тесты падают.

## Контекст

Проект: SciProof — мульти-агентный дискуссионный сервис.
Путь: ~/projects/sciproof/

Ничего ещё не создано. Начинаем с нуля.

## Задача

1. Создай структуру директорий проекта по CLAUDE.md.
   ВАЖНО: каждая директория-пакет (backend/, backend/core/, backend/models/, 
   backend/storage/, backend/api/) должна содержать __init__.py (пустой).

2. Создай requirements.txt:
   fastapi>=0.115.0
   uvicorn[standard]>=0.30.0
   litellm>=1.60.0
   sqlalchemy[asyncio]>=2.0.0
   asyncpg>=0.30.0
   alembic>=1.14.0
   pydantic>=2.10.0
   pydantic-settings>=2.7.0
   jinja2>=3.1.0
   httpx>=0.28.0
   pyyaml>=6.0
   sse-starlette>=2.0.0
   pytest>=8.0.0
   pytest-asyncio>=0.24.0

3. Создай config/settings.yaml (НЕ gitignored — без секретов):
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

4. Создай config/agents.example.yaml:
   providers:
     anthropic:
       api_key: "sk-ant-xxx"
       model: "anthropic/claude-sonnet-4-6"
     openai:
       api_key: "sk-xxx"
       model: "openai/gpt-5.4"
   
   agents:
     claude-analyst:
       provider: anthropic
       display_name: "Аналитик (Claude)"
       temperature: 0.3
       persona: "Ты — строгий аналитик. Опираешься на факты и источники. Скептически относишься к утверждениям без evidence. Предпочитаешь точность широте охвата."
     claude-creative:
       provider: anthropic
       display_name: "Синтезатор (Claude)"
       temperature: 0.8
       persona: "Ты — креативный синтезатор. Ищешь неожиданные связи между идеями. Предлагаешь нестандартные интерпретации. Не боишься спекулятивных гипотез, но маркируешь их как гипотезы."
     gpt-critic:
       provider: openai
       display_name: "Критик (GPT)"
       temperature: 0.4
       persona: "Ты — методологический критик. Проверяешь логику аргументации. Ищешь скрытые допущения, ошибки вывода, недостаточную обоснованность. Если аргумент строгий — признаёшь это."
     gpt-generalist:
       provider: openai
       display_name: "Эрудит (GPT)"
       temperature: 0.6
       persona: "Ты — широкий эрудит. Привлекаешь данные из смежных областей. Проводишь аналогии. Контекстуализируешь проблему в более широкой картине."
   
   judge:
     provider: anthropic
     temperature: 0.2
     display_name: "Судья"

5. Создай backend/config.py:
   - Pydantic Settings: загрузка из YAML + env
   - Классы: ProviderConfig, AgentConfig, JudgeConfig, AppSettings
   - Валидация: temperature 0.0-1.0, provider только "anthropic"/"openai"

6. Создай Pydantic-модели данных (backend/models/):
   - agent.py: AgentConfig, ProviderConfig
   - debate.py: DebateConfig, DebateResult, RoundData
   - response.py: ParsedResponse, JudgeVerdict, JudgeSynthesis
   - events.py: SSE-события (RoundStart, ResponseChunk, ResponseComplete, JudgeVerdictEvent, DebateComplete, ErrorEvent)

## Контракт данных

ParsedResponse — ключи СТРОГО из CLAUDE.md:
  position: str
  confidence: Literal["high", "medium", "low", "unknown"]
  position_changed: bool = False
  change_reason: str = ""
  agreements: list[Agreement] = []     # Agreement: {with_: str, point: str, why: str}
  disagreements: list[Disagreement] = []  # Disagreement: {with_: str, point: str, counterargument: str}
  sources: list[str] = []
  full_argument: str
  parse_quality: Literal["json_clean", "json_extracted", "free_text_fallback"]

JudgeVerdict:
  round_number: int
  argument_novelty: float  # 0.0-1.0
  position_changes: list[str]
  stagnation: bool
  convergence_points: list[str]
  remaining_disagreements: list[str]
  should_stop: bool
  stop_reason: str | None  # "consensus" | "stagnation" | "max_rounds"

DebateConfig:
  question: str
  context: str = ""
  mode: Literal["debate", "consensus", "devil_advocate", "expert_panel", "peer_review"] = "debate"
  agents: list[str]  # agent IDs
  max_rounds: int = 3  # 1-5
  web_search: bool = False
  budget_usd: float | None = None
  pause_between_rounds: bool = False
  language: str = "ru"

## Тест

После создания прогони ВСЕ проверки:

ТЕСТ 1 — загрузка конфига:
  python -c "from backend.config import load_config; c = load_config('config/agents.example.yaml'); print(c.agents.keys())"
  Ожидание: dict_keys(['claude-analyst', 'claude-creative', 'gpt-critic', 'gpt-generalist'])

ТЕСТ 2 — Pydantic-модели:
  python -c "from backend.models.response import ParsedResponse; r = ParsedResponse(position='test', confidence='high', full_argument='text', parse_quality='json_clean'); print(r.model_dump_json(indent=2))"

ТЕСТ 3 — валидация temperature:
  python -c "from backend.models.agent import AgentConfig; a = AgentConfig(provider='anthropic', display_name='t', temperature=1.5, persona='t')"
  Ожидание: ValidationError (temperature > 1.0)

ТЕСТ 4 — валидация confidence:
  python -c "from backend.models.response import ParsedResponse; r = ParsedResponse(position='t', confidence='wrong', full_argument='t', parse_quality='json_clean')"
  Ожидание: ValidationError (confidence not in allowed values)

ТЕСТ 5 — валидация mode:
  python -c "from backend.models.debate import DebateConfig; d = DebateConfig(question='t', agents=['a'], mode='invalid')"
  Ожидание: ValidationError

ТЕСТ 6 — все модели импортируются без ошибок:
  python -c "from backend.models import agent, debate, response, events; print('OK')"

Формат отчёта:
| # | Тест | Статус | Проблемы |
|---|------|--------|----------|

## Коммит

Если все тесты прошли:
  git init (если ещё нет)
  git add -A
  git commit -m "step-1: project structure, config, pydantic models"

## Ограничения

- НЕ устанавливать пакеты. Только создать файлы.
- НЕ изобретать имена полей — строго из контракта выше.
- НЕ создавать frontend пока. Только backend/ и config/.
- .gitignore: config/agents.yaml, __pycache__/, .env, *.pyc, data/, .pytest_cache/
```

---

## ШАГ 2: LLM Gateway

```
## Правила

1. Прочитай CLAUDE.md в корне проекта. Это источник истины.
2. Составь план перед кодированием. Покажи мне план, дождись подтверждения.
3. Если видишь проблему в промте — скажи, не выполняй молча.
4. Имена полей и контракты данных НЕ менять.
5. После завершения и успешного тестирования — git add + git commit.
6. Тестирование обязательно. Не коммитить если тесты падают.

## Контекст

Проект: SciProof
Шаг 1 выполнен: структура, config.py, Pydantic-модели готовы.

Существующие компоненты:
- backend/config.py: загрузка YAML → AppSettings (providers, agents, judge)
- backend/models/agent.py: AgentConfig, ProviderConfig
- backend/models/response.py: ParsedResponse

## Задача

Создай backend/core/llm_gateway.py:

1. Класс LLMGateway:
   - __init__(self, config: AppSettings)
   - async call(self, agent: AgentConfig, messages: list[dict], stream: bool = True) -> AsyncGenerator[str, None] | str
   - async call_judge(self, messages: list[dict]) -> str  (не стримится, полный ответ)
   - async health_check(self) -> dict[str, bool]  (проверка доступности провайдеров)

2. Использует litellm.acompletion():
   - model = provider.litellm_model_id (из конфига провайдера агента)
   - temperature = agent.temperature
   - api_key = provider.api_key
   - max_tokens = 4096
   - stream = True/False

3. Трекинг: после каждого вызова сохранять в dict:
   - tokens_input, tokens_output (из response.usage)
   - cost_usd (litellm.completion_cost())
   - latency_ms
   - agent_id

4. Retry: 1 повтор при timeout (лителлм может сам, проверь настройки)

## Контракт данных

Вход call(): AgentConfig + list[dict] messages в OpenAI-формате:
  [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

Выход call(stream=True): AsyncGenerator[str, None] — чанки текста
Выход call(stream=False): str — полный текст ответа

Выход call_judge(): str — полный текст (судья не стримится)

Выход health_check(): {"anthropic": True, "openai": False}

## Интеграционный тест

Создай backend/tests/test_llm_gateway.py:

ТЕСТ 1: health_check — оба провайдера доступны
ТЕСТ 2: call без стриминга — каждый из 4 агентов отвечает на "Скажи одно слово"
ТЕСТ 3: call со стримингом — собрать чанки, проверить что строка непустая
ТЕСТ 4: call_judge — ответ непустой
ТЕСТ 5: трекинг — после вызова tokens_input > 0, cost_usd > 0

Прогони тесты.

ДОПОЛНИТЕЛЬНО:
ТЕСТ 6: вызов с невалидным API-ключом → ошибка обрабатывается gracefully, не крашит
ТЕСТ 7: два параллельных вызова (asyncio.gather) → оба завершаются
ТЕСТ 8: стриминг от каждого из 4 агентов — все 4 дают непустой результат

Формат отчёта:
| # | Тест | Статус | Проблемы |
|---|------|--------|----------|

## Коммит

Если все тесты прошли:
  git add -A
  git commit -m "step-2: llm gateway (litellm, async, streaming)"

## Ограничения

- НЕ использовать openai SDK напрямую — только через litellm
- НЕ хардкодить модели или ключи — всё из config
- НЕ блокирующие вызовы — только async
- config/agents.yaml должен существовать (скопировать из agents.example.yaml и вставить реальные ключи)
```

---

## ШАГ 3: Response Parser

```
## Правила

1. Прочитай CLAUDE.md в корне проекта. Это источник истины.
2. Составь план перед кодированием. Покажи мне план, дождись подтверждения.
3. Если видишь проблему в промте — скажи, не выполняй молча.
4. Имена полей и контракты данных НЕ менять.
5. После завершения и успешного тестирования — git add + git commit.
6. Тестирование обязательно. Не коммитить если тесты падают.

## Контекст

Проект: SciProof
Шаги 1-2 выполнены: config, models, llm_gateway готовы.

## Задача

Создай backend/core/response_parser.py:

Функция parse_response(raw: str) -> ParsedResponse

3 уровня fallback:

1. Чистый JSON: raw — валидный JSON → парсим в ParsedResponse
   parse_quality = "json_clean"

2. JSON из markdown: raw содержит ```json...``` → извлечь, парсить
   parse_quality = "json_extracted"

3. Свободный текст: ничего не парсится → обернуть в ParsedResponse с пустыми метаданными
   parse_quality = "free_text_fallback"
   position = "", confidence = "unknown", full_argument = raw

На каждом уровне: если JSON парсится, но не содержит обязательных полей — дополнить дефолтами, не падать.

## Контракт данных

Вход: raw: str — сырой текст ответа LLM
Выход: ParsedResponse (все поля из CLAUDE.md)

## Интеграционный тест

Создай backend/tests/test_response_parser.py с 6+ тестами:

ТЕСТ 1 — чистый JSON:
  '{"position": "OSL ненадёжен", "confidence": "high", "position_changed": false, "agreements": [], "disagreements": [], "sources": [], "full_argument": "Аргументация..."}'
  → parse_quality == "json_clean"

ТЕСТ 2 — JSON в markdown:
  'Вот мой анализ:\n```json\n{"position": "test", "confidence": "medium", "full_argument": "..."}\n```\nПрим.'
  → parse_quality == "json_extracted"

ТЕСТ 3 — свободный текст:
  'Я считаю что OSL надёжен для лёссов, потому что...'
  → parse_quality == "free_text_fallback", full_argument содержит весь текст

ТЕСТ 4 — JSON с неполными полями:
  '{"position": "test", "full_argument": "..."}'
  → parse_quality == "json_clean", confidence == "unknown", agreements == []

ТЕСТ 5 — битый JSON в markdown:
  '```json\n{"position": "test", bad json\n```'
  → parse_quality == "free_text_fallback"

ТЕСТ 6 — реальный ответ LLM (скопируй из теста шага 2):
  Взять реальный ответ одного из агентов, прогнать через парсер.

Все тесты должны пройти.

ДОПОЛНИТЕЛЬНО:
ТЕСТ 7: пустая строка → parse_quality == "free_text_fallback", full_argument == ""
ТЕСТ 8: JSON с кириллицей в значениях парсится корректно
ТЕСТ 9: очень длинный текст (10000 символов) → не падает, parse_quality определён

Формат отчёта:
| # | Тест | Статус | Проблемы |
|---|------|--------|----------|

## Коммит

Если все тесты прошли:
  git add -A
  git commit -m "step-3: response parser (3 fallback levels)"

## Ограничения

- НИКОГДА не бросать исключение. Всегда возвращать ParsedResponse.
- НЕ менять имена полей ParsedResponse.
- import json, re — только стандартная библиотека для парсинга.
```

---

## ШАГ 4: Prompt Builder + шаблоны промтов

```
## Правила

1. Прочитай CLAUDE.md в корне проекта. Это источник истины.
2. Составь план перед кодированием. Покажи мне план, дождись подтверждения.
3. Если видишь проблему в промте — скажи, не выполняй молча.
4. Имена полей и контракты данных НЕ менять.
5. После завершения и успешного тестирования — git add + git commit.
6. Тестирование обязательно. Не коммитить если тесты падают.

## Контекст

Проект: SciProof
Шаги 1-3 выполнены.

## Задача

### A. Создай Jinja2-шаблоны (backend/prompts/):

1. format_json.jinja2 — инструкция формата ответа:
   Обязательно включи ПОЛНЫЙ пример JSON с описанием каждого поля.
   Модель должна понимать структуру однозначно.
   Язык инструкции: русский.
   Укажи: "Ответь СТРОГО в формате JSON. Никакого текста до или после JSON."

2. system_debate.jinja2 — режим Debate:
   "Ты участвуешь в научной дискуссии. Сформулируй свою позицию, приведи аргументы."
   + включить {{ agent_persona }}
   + включить {{ format_json }}

3. round_n.jinja2 — раунд 2+:
   "Ниже ответы других участников (анонимизированы). Пересмотри свою позицию."
   + Для КАЖДОГО оппонента: найди минимум одно слабое место.
   + Если изменил позицию — объясни почему.
   + {% for resp in anonymized_responses %} Response {{ resp.label }}: {{ resp.content }} {% endfor %}
   + Полная история предыдущих раундов (если раунд > 2)

4. skeptic_addon.jinja2 — дополнение для скептика:
   "В этом раунде ты дополнительно выполняешь роль скептика. Твоя задача — найти дыры в аргументации каждого оппонента. Если аргумент безупречен — объясни почему."

5. judge_round.jinja2 — вердикт судьи:
   "Ты нейтральный судья. Оцени раунд дискуссии."
   Формат вывода: JSON JudgeVerdict (из CLAUDE.md).

6. judge_synthesis.jinja2 — финальный синтез:
   "Ты нейтральный аналитик. Составь финальный синтез дискуссии."
   7 блоков: вопрос и контекст, консенсус, разногласия, эволюция позиций, оценка аргументации, пробелы и рекомендации, источники.

7. system_consensus.jinja2, system_devil.jinja2, system_expert.jinja2, system_review.jinja2 — аналогично debate, но с другими инструкциями по режиму. Для Фазы 0 можно минимально, главное — отличие system message.

### B. Создай backend/core/prompt_builder.py:

Класс PromptBuilder:
  - __init__(self, prompts_dir: str)
  - round_1(agent, config, search_context) -> list[dict]
  - round_n(agent, config, history, anonymized, is_skeptic) -> list[dict]
  - judge_round(debate) -> list[dict]
  - judge_synthesis(debate) -> list[dict]
  - anonymize(responses: list[AgentResponse]) -> tuple[list[AnonymizedResponse], dict[str, str]]
    # Возвращает анонимизированные ответы + маппинг {"Response A": "claude-analyst", ...}

Каждый метод возвращает list[dict] в OpenAI-формате:
  [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

## Контракт данных

anonymize():
  Вход: list[AgentResponse] — [{agent_id: "claude-analyst", content: "..."}]
  Выход: (
    [AnonymizedResponse(label="Response A", content="..."), ...],
    {"Response A": "claude-analyst", "Response B": "gpt-critic", ...}
  )
  Метки: Response A, Response B, Response C, Response D (фиксированный порядок)

## Тест

Создай backend/tests/test_prompt_builder.py:

ТЕСТ 1: round_1 возвращает 2 сообщения (system + user), system содержит persona агента
ТЕСТ 2: round_n содержит ответы оппонентов с метками Response A/B/C/D (не имена агентов)
ТЕСТ 3: round_n для скептика содержит текст из skeptic_addon
ТЕСТ 4: anonymize — 4 ответа → 4 анонимизированных + маппинг из 4 записей
ТЕСТ 5: anonymize — в анонимизированных ответах НЕТ agent_id, provider, display_name
ТЕСТ 6: judge_round — system содержит "нейтральный судья"
ТЕСТ 7: промты на русском языке (system содержит кириллицу)
ТЕСТ 8: round_n содержит полную историю предыдущих раундов (не только последний)
ТЕСТ 9: промт для mode="consensus" отличается от mode="debate"

Формат отчёта:
| # | Тест | Статус | Проблемы |
|---|------|--------|----------|

## Коммит

Если все тесты прошли:
  git add -A
  git commit -m "step-4: prompt builder + jinja2 templates"

## Ограничения

- Все промты — на РУССКОМ. Ключи JSON в примерах внутри промтов — на английском.
- Шаблоны в backend/prompts/*.jinja2 — НЕ хардкодить текст в Python.
- Не включать имена агентов/провайдеров в промты — только persona.
```

---

## ШАГ 5: Orchestrator (MVP)

```
## Правила

1. Прочитай CLAUDE.md в корне проекта. Это источник истины.
2. Составь план перед кодированием. Покажи мне план, дождись подтверждения.
3. Если видишь проблему в промте — скажи, не выполняй молча.
4. Имена полей и контракты данных НЕ менять.
5. После завершения и успешного тестирования — git add + git commit.
6. Тестирование обязательно. Не коммитить если тесты падают.

## Контекст

Проект: SciProof
Шаги 1-4 выполнены:
- config.py: загрузка YAML → AppSettings
- llm_gateway.py: call(agent, messages), call_judge(messages)
- response_parser.py: parse_response(raw) → ParsedResponse
- prompt_builder.py: round_1(), round_n(), anonymize(), judge_round(), judge_synthesis()
- Pydantic-модели: DebateConfig, ParsedResponse, JudgeVerdict

## Задача

Создай backend/core/orchestrator.py:

Класс DebateOrchestrator:
  - __init__(self, gateway, prompt_builder, response_parser, config)
  - async run_debate(config: DebateConfig) -> DebateResult

Алгоритм run_debate (упрощённый, без storage, SSE и судьи — добавим позже):

1. Раунд 1: asyncio.gather → 4 вызова → parse_response каждый
2. Раунды 2+:
   a. anonymize предыдущие ответы
   b. определить скептика (ротация: агент[round_num % len(agents)])
   c. asyncio.gather → 4 вызова с round_n промтами
   d. parse_response каждый
   e. проверка max_rounds → break
3. Собрать DebateResult: все раунды + метрики (токены, стоимость)

ПРИМЕЧАНИЕ: судья (judge.evaluate_round, judge.synthesize) добавляется на Шаге 6.
На этом шаге orchestrator работает без судьи — только раунды и парсинг.

Создай CLI-скрипт scripts/run_debate.py:
  python scripts/run_debate.py "Каковы аргументы за и против OSL-датирования лёссов старше 100 тыс. лет?"
  
  Выводит:
  - Каждый раунд: 4 ответа (agent_id + позиция + confidence)
  - Вердикт судьи после каждого раунда
  - Финальный синтез
  - Итого: токены, стоимость

## Контракт данных

Orchestrator → DebateResult:
  debate_id: str (uuid)
  question: str
  mode: str
  agents: list[str]
  rounds: list[RoundData]
    RoundData:
      round_number: int
      responses: list[AgentResponse]
        AgentResponse:
          agent_id: str
          anonymous_label: str
          parsed: ParsedResponse
          tokens_input: int
          tokens_output: int
          cost_usd: float
          latency_ms: int
      judge_verdict: JudgeVerdict | None
      anonymization_mapping: dict[str, str]
  synthesis: JudgeSynthesis | None
  total_tokens: int
  total_cost_usd: float

## Интеграционный тест — КЛЮЧЕВОЙ

Это END-TO-END тест через весь pipeline. Прогони:

python scripts/run_debate.py "Стоит ли использовать property graph вместо реляционной БД для хранения научных утверждений?"

Критерии прохождения:
1. [ ] 4 агента дали ответы в раунде 1
2. [ ] Ответы различаются по характеру (analyst ≠ creative ≠ critic ≠ generalist)
3. [ ] parse_quality != "free_text_fallback" хотя бы у 3 из 4
4. [ ] Раунд 2: агенты ссылаются на Response A/B/C/D (не на имена)
5. [ ] Раунд 2: хотя бы 1 агент изменил позицию ИЛИ привёл контраргумент
6. [ ] Раунд 3: автостоп по max_rounds работает
7. [ ] Все 4 агента завершили каждый раунд (нет зависших)
8. [ ] Стоимость: вывести total_cost_usd (ожидание: $0.50–3.00)

Если parse_quality == "free_text_fallback" у >1 агента → проблема в промте format_json.jinja2. Исправить и повторить.

ДОПОЛНИТЕЛЬНО:
9. [ ] Стриминг в CLI: ответы печатаются по мере получения (print по чанкам), а не после полного завершения
10. [ ] Retry: если один агент упал — остальные продолжают
11. [ ] Анонимизация: в raw_content ответов раунда 2 нет строк "claude", "gpt", имён агентов

Выведи отчёт:
| # | Критерий | Статус | Детали |
|---|----------|--------|--------|

## Коммит

Если все критерии пройдены:
  git add -A
  git commit -m "step-5: orchestrator MVP (4 agents, 3 rounds, judge, cli)"

## Ограничения

- БЕЗ storage (PostgreSQL добавим на шаге 7). Результат возвращается in-memory.
- БЕЗ SSE (добавим на шаге 8). Только синхронный CLI-вывод.
- БЕЗ web search (шаг 8).
- БЕЗ pause_between_rounds (шаг 8).
- Максимум 3 раунда на этом этапе.
```

---

## ШАГ 6: Judge + итерация по промтам

```
## Правила

1. Прочитай CLAUDE.md в корне проекта. Это источник истины.
2. Составь план перед кодированием. Покажи мне план, дождись подтверждения.
3. Если видишь проблему в промте — скажи, не выполняй молча.
4. Имена полей и контракты данных НЕ менять.
5. После завершения и успешного тестирования — git add + git commit.
6. Тестирование обязательно. Не коммитить если тесты падают.

## Контекст

Проект: SciProof
Шаг 5 выполнен: orchestrator работает без судьи, CLI-скрипт запускает дебаты (раунды + парсинг).

Нужно:
A. Создать judge.py (вердикт раунда + финальный синтез)
B. Интегрировать судью в orchestrator (evaluate_round после каждого раунда, synthesize в конце)
C. Откалибровать промты на 5 тестовых вопросах

## Задача

Прогони 5 тестовых дебатов и оптимизируй промты по результатам.

### Тестовые вопросы

1. "Каковы аргументы за и против OSL-датирования лёссов старше 100 тыс. лет?"
2. "Property graph vs RDF vs реляционная БД с JSONB для хранения научных claims?"
3. "Можно ли считать корреляцию двух разрезов доказанной на основании только литостратиграфии без абсолютных датировок?"
4. "Как связаны неотектонические движения и формирование речных террас?"
5. "Как организовать кураторский контур для научного knowledge graph?" (режим consensus)

### Для каждого дебата оцени и запиши:

| Метрика | Значение |
|---------|----------|
| parse_quality (% json_clean) | ? |
| Различаются ли ответы агентов по характеру? | да/нет |
| Есть ли реальная дискуссия в раунде 2 (не просто "согласен")? | да/нет |
| Качество синтеза (1-5) | ? |
| Стоимость $ | ? |
| Главная проблема | ? |

### Типичные проблемы и фиксы:

- Агенты не следуют JSON → усилить format_json.jinja2, добавить "СТРОГО JSON, никакого текста вне JSON"
- Все соглашаются в раунде 2 → усилить round_n.jinja2 "обязательно найди слабое место"
- Persona не влияет → сделать persona более конкретной, с примерами поведения
- Синтез поверхностный → усилить judge_synthesis.jinja2, потребовать конкретных цитат из раундов
- Ответы на английском → добавить "Отвечай ТОЛЬКО на русском языке"

### После 5 дебатов

1. Зафиксируй финальные версии промтов (git commit)
2. Запиши: какие промты менялись и почему (в комментарии коммита)
3. Средние метрики по 5 дебатам

## Коммит

  git add -A
  git commit -m "step-6: prompt calibration (N iterations, parse_quality=XX%)"

## Ограничения

- НЕ менять код Python на этом шаге — только шаблоны Jinja2.
- НЕ менять контракт данных.
- Если parse_quality < 80% json_clean — ЭТО БЛОКЕР. Не двигаться дальше пока не исправлено.
```

---

## ШАГ 7: PostgreSQL + Storage

```
## Правила

1. Прочитай CLAUDE.md в корне проекта. Это источник истины.
2. Составь план перед кодированием. Покажи мне план, дождись подтверждения.
3. Если видишь проблему в промте — скажи, не выполняй молча.
4. Имена полей и контракты данных НЕ менять.
5. После завершения и успешного тестирования — git add + git commit.
6. Тестирование обязательно. Не коммитить если тесты падают.

## Контекст

Проект: SciProof
Шаги 1-6 выполнены: pipeline работает in-memory, промты откалиброваны.
PostgreSQL уже запущен на localhost:5432.

## Задача

1. Создай БД:
   psql -U postgres -c "CREATE DATABASE sciproof;"

2. Создай backend/storage/models_db.py — SQLAlchemy ORM модели:
   Таблицы: debates, rounds, responses, metrics, users
   Схема — из CLAUDE.md / Architecture v2 (PostgreSQL DDL).
   Используй mapped_column, Mapped[] (SQLAlchemy 2.0 стиль).

3. Настрой Alembic:
   alembic init backend/alembic
   Настрой alembic.ini и env.py (async engine, asyncpg).
   alembic revision --autogenerate -m "initial"
   alembic upgrade head

4. Создай backend/storage/database.py:
   - async engine (create_async_engine)
   - async session factory (async_sessionmaker)
   - get_session() — dependency для FastAPI

5. Создай backend/storage/queries.py — CRUD:
   - create_debate(session, config) -> debate_id
   - add_round(session, debate_id, round_data)
   - add_response(session, round_id, agent_response)
   - add_verdict(session, round_id, verdict)
   - update_synthesis(session, debate_id, synthesis)
   - get_debate(session, debate_id) -> DebateResult
   - list_debates(session, limit, offset) -> list[DebateSummary]
   - delete_debate(session, debate_id)

6. Интегрируй storage в orchestrator:
   - В начале run_debate: create_debate
   - После каждого раунда: add_round + add_responses + add_verdict
   - В конце: update_synthesis

## Контракт данных

PostgreSQL поля — строго из CLAUDE.md:
  debates.agents: JSONB
  debates.config: JSONB
  debates.synthesis: JSONB
  responses.parsed_json: JSONB
  responses.agent_id: TEXT (не model_id!)
  rounds.judge_verdict: JSONB

## Тест

1. Прогони один дебат через CLI:
   python scripts/run_debate.py "Тестовый вопрос"

2. Проверь БД:
   psql sciproof -c "SELECT id, question, status, total_cost FROM debates;"
   psql sciproof -c "SELECT agent_id, parse_quality, cost_usd FROM responses WHERE debate_id = '...';"

3. Прогони: get_debate(id) → проверь что все раунды и ответы загрузились.

ДОПОЛНИТЕЛЬНО:
4. delete_debate(id) → каскадное удаление (rounds, responses, metrics)
5. list_debates() → возвращает список, сортировка по дате
6. Повторный запуск дебата → новая запись, не перезапись старой

## Коммит

Если все тесты прошли:
  git add -A
  git commit -m "step-7: postgresql storage (sqlalchemy, alembic, crud)"

## Ограничения

- Async everywhere: asyncpg, не psycopg2.
- UUID для debate_id (gen_random_uuid в PostgreSQL).
- Каскадное удаление: ON DELETE CASCADE.
- НЕ создавать таблицы напрямую SQL — только через Alembic.
```

---

## ШАГ 8: Web Search + Judge улучшения

```
## Правила

1. Прочитай CLAUDE.md в корне проекта. Это источник истины.
2. Составь план перед кодированием. Покажи мне план, дождись подтверждения.
3. Если видишь проблему в промте — скажи, не выполняй молча.
4. Имена полей и контракты данных НЕ менять.
5. После завершения и успешного тестирования — git add + git commit.
6. Тестирование обязательно. Не коммитить если тесты падают.

## Контекст

Проект: SciProof
Шаги 1-7 выполнены: pipeline + PostgreSQL работают.

## Задача

1. Создай backend/core/web_search.py:
   - async search(query: str, max_results: int = 5) -> SearchContext
   - Brave Search API (ключ из config/settings.yaml)
   - SearchContext: {snippets: list[str], urls: list[str], query: str}

2. Интегрируй в orchestrator:
   - Если config.web_search == True:
     a. Перед раундом 1: search(question) → shared_context
     b. shared_context добавляется в промт round_1 и round_n как контекст

3. Настрой Brave API ключ:
   В config/settings.yaml:
     brave_search_api_key: "${BRAVE_API_KEY}"

## Тест

Прогони дебат с web_search=True:
  python scripts/run_debate.py --web-search "Какие новые методы датирования появились в 2025 году?"

Критерии:
- [ ] search выполнился, snippets непустые
- [ ] В ответах агентов есть ссылки на URL из поиска
- [ ] Синтез содержит раздел "источники"

## Ограничения

- Brave API: max 3 запроса на раунд (раунд 0 = 1 запрос, tool use пока не реализуем).
- Если Brave API недоступен — дебат продолжается без поиска (предупреждение в логе).

ДОПОЛНИТЕЛЬНО:
- [ ] Дебат без web_search по-прежнему работает (регрессия)
- [ ] search_context сохраняется в PostgreSQL (таблица rounds)

## Коммит

Если все тесты прошли:
  git add -A
  git commit -m "step-8: web search (brave api, round 0)"
```

---

## ШАГ 9: Экспорт в Markdown

```
## Правила

1. Прочитай CLAUDE.md в корне проекта. Это источник истины.
2. Составь план перед кодированием. Покажи мне план, дождись подтверждения.
3. Если видишь проблему в промте — скажи, не выполняй молча.
4. Имена полей и контракты данных НЕ менять.
5. После завершения и успешного тестирования — git add + git commit.
6. Тестирование обязательно. Не коммитить если тесты падают.

## Контекст

Проект: SciProof
Шаги 1-8 выполнены.

## Задача

Создай scripts/export_debate.py:

  python scripts/export_debate.py <debate_id> [--output sciproof_export.md]

Формат Markdown:

# Дебат: <question>
Дата: <created_at> | Режим: <mode> | Раунды: <N> | Стоимость: $<total_cost>

## Участники
| Агент | Роль | Провайдер |
...

## Раунд 1: Независимые ответы
### Аналитик (Claude)
<full_argument>
**Позиция:** <position> | **Уверенность:** <confidence>

### Критик (GPT)
...

## Раунд 2: Перекрёстное рецензирование
### Аналитик (Claude)
**Изменил позицию:** да/нет
**Согласие:** ...
**Несогласие:** ...
<full_argument>

### Вердикт судьи (Раунд 2)
...

## Финальный синтез
<synthesis — все 7 блоков>

## Метрики
| Раунд | Novelty | Stagnation | Convergence |
...

## Ограничения

- Читать из PostgreSQL (через queries.get_debate).
- Показывать РЕАЛЬНЫЕ имена агентов (не Response A/B/C/D — анонимизация только для агентов (при вызове LLM)).

ДОПОЛНИТЕЛЬНО:
- [ ] Экспорт дебата без web search — секция "Источники" пустая или отсутствует
- [ ] Экспорт дебата с consensus mode — формат корректен
- [ ] Markdown открывается и читается в обычном текстовом редакторе

## Коммит

  git add -A
  git commit -m "step-9: markdown export"
```

---

## ШАГ 10: Финальная валидация Фазы 0

```
## Правила

1. Прочитай CLAUDE.md в корне проекта. Это источник истины.
2. Составь план перед кодированием. Покажи мне план, дождись подтверждения.
3. Если видишь проблему в промте — скажи, не выполняй молча.
4. Имена полей и контракты данных НЕ менять.
5. После завершения и успешного тестирования — git add + git commit.
6. Тестирование обязательно. Не коммитить если тесты падают.

## Контекст

Проект: SciProof
Все шаги 1-9 выполнены.

## Задача

Прогони 3 полных дебата и проверь ВСЕ критерии готовности Фазы 0:

Дебат 1: "Каковы аргументы за и против OSL-датирования лёссов старше 100 тыс. лет?" (debate, web_search=true)
Дебат 2: "Property graph vs RDF vs реляционная БД с JSONB для научных claims?" (debate)
Дебат 3: "Как организовать кураторский контур для научного knowledge graph?" (consensus)

### Чеклист

- [ ] 2 провайдера работают через LiteLLM (Anthropic, OpenAI)
- [ ] 4 агента с разными persona дают различающиеся ответы
- [ ] Дебат из 3 раундов завершается без ошибок
- [ ] JSON-метаданные: parse_quality != free_text_fallback у ≥80% ответов
- [ ] Судья выдаёт verdict после каждого раунда
- [ ] Финальный синтез содержит все 7 блоков
- [ ] Web search работает (Дебат 1)
- [ ] Результаты сохраняются в PostgreSQL
- [ ] Экспорт в Markdown читаем
- [ ] Persona влияют на характер ответов
- [ ] Стоимость: $1–3 за дебат

### Отчёт

| Критерий | Дебат 1 | Дебат 2 | Дебат 3 |
|----------|---------|---------|---------|
| ... | ✅/❌ | ✅/❌ | ✅/❌ |

Если ≥2 критерия провалены → исправить и повторить.

### Что НЕ входит в Фазу 0 (переносится в Фазу 1):
- FastAPI REST API endpoints (backend/api/*.py)
- SSE-стриминг через HTTP
- React frontend
- Docker / Coolify деплой
- Аутентификация

## Финальный коммит

Если OK:
  git add -A
  git commit -m "phase-0 complete: 4 agents, 3 rounds, judge, web search, postgresql, export"
  git tag v0.1.0
```
