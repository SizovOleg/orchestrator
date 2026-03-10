import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8004";

const sampleFactCheckText = `Целевая оптико-электронная аппаратура HUEOP: подтверждённые сведения и supplier capability envelope
Что подтверждено для HULEO напрямую. REMRED выбрала TelePIX в качестве поставщика electro-optical camera systems для HULEO; 4iG указывает на поставку state-of-the-art VHR camera and sensor suites. В том же официальном сообщении говорится, что TelePIX специализируется на high-resolution, space-qualified EO payload systems для small- and medium-satellite missions и развивает on-board data processing technologies.
Параметр\tСтатус для HULEO\tОпубликованное значение / формулировка\tИнженерный смысл
Поставщик EO-полезной нагрузки\tПодтверждено\tTelePIX\tЗафиксирован конкретный поставщик камер и сенсорных систем
Класс целевой аппаратуры\tПодтверждено\tVHR camera and sensor suites\tРечь идёт именно о very-high-resolution оптической нагрузке
Целевой тип миссии у поставщика\tПодтверждено на уровне профиля поставщика\tEO payload systems for small- and medium-satellite missions\tУказывает на компактный payload-class и совместимость с малым/средним bus, но не раскрывает bus HULEO
Публичная продуктовая линия TelePIX\tНе подтверждено как HULEO-specific\tCHOUETTE VHR optical payload with WFOV\tРелевантный ориентир по текущему уровню техники поставщика
GSD при 500 км (надир)\tНе подтверждено как HULEO-specific\tдо 0,75 м\tПоказывает достижимый публично заявленный уровень детальности для продуктовой линии CHOUETTE
Ширина полосы захвата при 500 км\tНе подтверждено как HULEO-specific\t24 км\tКомпромисс между субметровой детальностью и рабочей полосой
Оптическая схема\tНе подтверждено как HULEO-specific\tUnobscured TMA\tТрёхзеркальная анастигматическая схема типична для компактных VHR-систем
Габариты нагрузки\tНе подтверждено как HULEO-specific\t240 × 430 × 528 мм\tДаёт представление о посадочном объёме и компоновочных ограничениях платформы
Масса нагрузки\tНе подтверждено как HULEO-specific\t30 кг\tВажный ориентир для mass budget и центра масс аппарата
Спектральный состав\tНе подтверждено как HULEO-specific\t6 MS + 1 PAN (VIS/NIR)\tУказывает на panchromatic + multispectral конфигурацию
Потребляемая мощность\tНе подтверждено как HULEO-specific\t28 W\tМинимальный ориентир для EPS и теплового контура полезной нагрузки
Интерфейсы\tНе подтверждено как HULEO-specific\tSpaceWire, Wizardlink, CameraLink, Ethernet, RS-422\tНужна высокоскоростная и разнородная бортовая коммутация
On-board processing\tПодтверждено на уровне продуктового портфеля поставщика, но не HULEO-specific\tTetraPLEX AI on-board processor for edge computing in space\tПоставщик уже имеет публичную линию бортовой обработки данных и edge processing`;

const initialForm = {
  task_type: "review_text",
  question: "Улучши текст: сделай его яснее, логичнее и проверь спорные утверждения.",
  source_text: "",
  context: "",
  preserve_style: true,
  allow_restructure: false,
  ask_clarifying_questions: true,
  mode: "peer_review",
  max_rounds: 2,
  web_search: true,
  language: "ru"
};

const reviewSample = {
  ...initialForm,
  task_type: "review_text",
  question: "Сделай текст яснее для деловой аудитории, сохрани логику и проверь слабые места аргументации.",
  source_text:
    "Данное предложение имеет целью сформировать набор мер, направленных на обеспечение повышения операционной устойчивости подразделения, что, при условии последовательной реализации, может позитивно повлиять на качество принимаемых управленческих решений и общую предсказуемость сроков исполнения задач.",
  context:
    "Аудитория: руководители и менеджеры проектов. Нужен деловой русский язык без канцелярита. Смысл сокращать нельзя.",
  preserve_style: false,
  allow_restructure: true,
  ask_clarifying_questions: true,
  web_search: false
};

const factCheckSample = {
  ...initialForm,
  task_type: "fact_check",
  question:
    "Проверь корректность текста. Не задавай уточняющих вопросов, если часть данных нельзя подтвердить, явно пометь их как неподтвержденные или требующие источника.",
  source_text: sampleFactCheckText,
  context:
    "Это русскоязычная аналитическая записка по космической EO-нагрузке. Нужно развести официально подтвержденное для HULEO и supplier capability envelope поставщика.",
  preserve_style: true,
  allow_restructure: false,
  ask_clarifying_questions: false,
  web_search: true
};

function formatUsd(value) {
  return typeof value === "number" ? `$${value.toFixed(6)}` : "—";
}

function formatInteger(value) {
  return typeof value === "number" ? new Intl.NumberFormat("ru-RU").format(value) : "—";
}

function formatMs(value) {
  return typeof value === "number" ? `${value} ms` : "—";
}

function summarizeResult(result) {
  if (!result) {
    return { inputTokens: 0, outputTokens: 0, errors: 0, agentCalls: 0, parseFallbacks: 0 };
  }

  let inputTokens = 0;
  let outputTokens = 0;
  let errors = 0;
  let agentCalls = 0;
  let parseFallbacks = 0;

  for (const round of result.rounds || []) {
    for (const response of round.responses || []) {
      inputTokens += response.tokens_input || 0;
      outputTokens += response.tokens_output || 0;
      agentCalls += 1;
      if (response.error) {
        errors += 1;
      }
      if (response.parsed?.parse_quality === "free_text_fallback") {
        parseFallbacks += 1;
      }
    }
  }

  return { inputTokens, outputTokens, errors, agentCalls, parseFallbacks };
}

function buildProgressSteps(form, result, loading, elapsedSeconds) {
  const roundCount = result?.rounds?.length || Number(form.max_rounds) || 1;
  const steps = [{ key: "accepted", label: "Запрос принят" }];
  if (form.web_search) {
    steps.push({ key: "search", label: "Web search" });
  }
  for (let index = 1; index <= roundCount; index += 1) {
    steps.push({ key: `round-${index}`, label: `Раунд ${index}` });
    steps.push({ key: `judge-${index}`, label: `Судья ${index}` });
  }
  steps.push({ key: "synthesis", label: "Синтез" });

  if (result) {
    return steps.map((step) => {
      const roundMatch = step.key.match(/^round-(\d+)$/);
      const judgeMatch = step.key.match(/^judge-(\d+)$/);
      let status = "completed";

      if (roundMatch && Number(roundMatch[1]) > (result.rounds?.length || 0)) {
        status = "pending";
      }
      if (judgeMatch && Number(judgeMatch[1]) > (result.rounds?.filter((item) => item.judge_verdict).length || 0)) {
        status = "pending";
      }
      if (step.key === "synthesis" && !result.synthesis) {
        status = result.status === "needs_user_input" ? "pending" : "active";
      }
      return { ...step, status };
    });
  }

  if (!loading) {
    return steps.map((step, index) => ({ ...step, status: index === 0 ? "active" : "pending" }));
  }

  const activeIndex = Math.min(Math.floor(elapsedSeconds / 3), steps.length - 1);
  return steps.map((step, index) => ({
    ...step,
    status: index < activeIndex ? "completed" : index === activeIndex ? "active" : "pending"
  }));
}

function App() {
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [extraContext, setExtraContext] = useState("");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [health, setHealth] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [agents, setAgents] = useState([]);
  const [diagnosticsError, setDiagnosticsError] = useState("");
  const [sessionHistory, setSessionHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    refreshDiagnostics();
    refreshHistory();
  }, []);

  useEffect(() => {
    if (!loading) {
      setElapsedSeconds(0);
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setElapsedSeconds((current) => current + 1);
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [loading]);

  const agentMap = useMemo(() => Object.fromEntries(agents.map((agent) => [agent.id, agent])), [agents]);
  const totals = useMemo(() => summarizeResult(result), [result]);
  const progressSteps = useMemo(
    () => buildProgressSteps(form, result, loading, elapsedSeconds),
    [elapsedSeconds, form, loading, result]
  );

  async function refreshDiagnostics() {
    setDiagnosticsError("");
    try {
      const [healthResponse, metricsResponse, agentsResponse] = await Promise.all([
        fetch(`${API_BASE}/api/health`),
        fetch(`${API_BASE}/api/metrics/summary`),
        fetch(`${API_BASE}/api/agents`)
      ]);

      if (!healthResponse.ok || !metricsResponse.ok || !agentsResponse.ok) {
        throw new Error("Не удалось загрузить диагностику backend.");
      }

      const [healthData, metricsData, agentsData] = await Promise.all([
        healthResponse.json(),
        metricsResponse.json(),
        agentsResponse.json()
      ]);

      setHealth(healthData);
      setMetrics(metricsData);
      setAgents(agentsData);
    } catch (err) {
      setDiagnosticsError(err.message || "Диагностика недоступна.");
    }
  }

  async function refreshHistory() {
    setHistoryLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/sessions?limit=12`);
      if (!response.ok) {
        throw new Error("History is unavailable.");
      }
      const data = await response.json();
      setSessionHistory(data);
    } catch (err) {
      setDiagnosticsError(err.message || "History is unavailable.");
    } finally {
      setHistoryLoading(false);
    }
  }

  async function loadSession(sessionId) {
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
      if (!response.ok) {
        throw new Error(`Session load failed: ${response.status}`);
      }
      const data = await response.json();
      setForm(data.config);
      setResult(data.result);
      setExtraContext("");
    } catch (err) {
      setError(err.message || "Failed to load saved session.");
    }
  }

  async function submit(payload) {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch(`${API_BASE}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      const data = await response.json();
      setResult(data);
      await Promise.all([refreshDiagnostics(), refreshHistory()]);
    } catch (err) {
      setError(err.message || "Не удалось выполнить запрос.");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    submit(form);
  }

  function handleClarificationSubmit(event) {
    event.preventDefault();
    const mergedContext = [form.context, extraContext].filter(Boolean).join("\n\n");
    const nextPayload = { ...form, context: mergedContext };
    setForm(nextPayload);
    submit(nextPayload);
  }

  function updateField(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function loadSample(sample) {
    setForm(sample);
    setExtraContext("");
    setError("");
    setResult(null);
  }

  return (
    <div className="page">
      <aside className="hero">
        <p className="eyebrow">SciProof</p>
        <h1>Локальный стенд для multi-agent review и fact-check</h1>
        <p className="lead">
          Здесь можно полноценно тестировать локальный пайплайн: проверять backend, модели,
          токены, стоимость, ход раундов, вердикты судьи и сырые ответы агентов.
        </p>

        <section className="diagnostics-card">
          <div className="section-head">
            <h2>Диагностика</h2>
            <button type="button" className="ghost-button" onClick={refreshDiagnostics}>
              Обновить
            </button>
          </div>

          {diagnosticsError && <div className="error compact">{diagnosticsError}</div>}

          <div className="chips">
            <span className={`chip ${health?.status === "ok" ? "ok" : "idle"}`}>
              Backend: {health?.status || "unknown"}
            </span>
            <span className={`chip ${health?.providers?.anthropic ? "ok" : "warn"}`}>
              Anthropic: {health?.providers?.anthropic ? "ready" : "missing"}
            </span>
            <span className={`chip ${health?.providers?.openai ? "ok" : "warn"}`}>
              OpenAI: {health?.providers?.openai ? "ready" : "missing"}
            </span>
          </div>

          {metrics && (
            <div className="diagnostics-grid">
              <div className="diagnostic-item">
                <strong>Режим</strong>
                <span>{metrics.mode}</span>
              </div>
              <div className="diagnostic-item">
                <strong>Порт</strong>
                <span>{metrics.server?.port}</span>
              </div>
              <div className="diagnostic-item">
                <strong>Anthropic model</strong>
                <span>{metrics.providers?.anthropic?.model || "—"}</span>
              </div>
              <div className="diagnostic-item">
                <strong>OpenAI model</strong>
                <span>{metrics.providers?.openai?.model || "—"}</span>
              </div>
              <div className="diagnostic-item">
                <strong>Storage</strong>
                <span>{metrics.storage?.backend || "—"}</span>
              </div>
              <div className="diagnostic-item">
                <strong>Saved sessions</strong>
                <span>{metrics.storage?.sessions_saved ?? 0}</span>
              </div>
            </div>
          )}

          <div className="agents-list">
            {agents.map((agent) => (
              <article key={agent.id} className="agent-pill">
                <strong>{agent.display_name}</strong>
                <span>{agent.provider}</span>
                <span>t={agent.temperature}</span>
              </article>
            ))}
          </div>
        </section>

        <section className="diagnostics-card">
          <h2>Быстрые сценарии</h2>
          <div className="sample-actions">
            <button type="button" className="ghost-button" onClick={() => loadSample(reviewSample)}>
              Загрузить sample review
            </button>
            <button type="button" className="ghost-button" onClick={() => loadSample(factCheckSample)}>
              Загрузить sample fact-check
            </button>
          </div>
        </section>
        <section className="diagnostics-card">
          <div className="section-head">
            <h2>History</h2>
            <button type="button" className="ghost-button" onClick={refreshHistory} disabled={historyLoading}>
              {historyLoading ? "Loading..." : "Refresh"}
            </button>
          </div>
          <div className="history-list">
            {sessionHistory.map((item) => (
              <button
                key={item.session_id}
                type="button"
                className="history-item"
                onClick={() => loadSession(item.session_id)}
              >
                <strong>{item.task_type}</strong>
                <span>{new Date(item.created_at).toLocaleString("ru-RU")}</span>
                <span>{item.status}</span>
                <span>{item.total_tokens} tok</span>
              </button>
            ))}
            {sessionHistory.length === 0 && <p className="history-empty">No saved sessions yet.</p>}
          </div>
        </section>
      </aside>

      <main className="panel">
        <form className="form" onSubmit={handleSubmit}>
          <div className="grid">
            <label>
              <span>Сценарий</span>
              <select value={form.task_type} onChange={(event) => updateField("task_type", event.target.value)}>
                <option value="review_text">Review текста</option>
                <option value="fact_check">Проверка факта</option>
              </select>
            </label>

            <label>
              <span>Раунды</span>
              <select value={form.max_rounds} onChange={(event) => updateField("max_rounds", Number(event.target.value))}>
                <option value={1}>1</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
              </select>
            </label>
          </div>

          <label>
            <span>Задача / вопрос</span>
            <textarea rows={3} value={form.question} onChange={(event) => updateField("question", event.target.value)} />
          </label>

          <label>
            <span>Исходный текст</span>
            <textarea
              rows={12}
              value={form.source_text}
              onChange={(event) => updateField("source_text", event.target.value)}
              placeholder="Вставьте фрагмент текста объёмом примерно 3–4 тыс. знаков"
            />
          </label>

          <label>
            <span>Дополнительный контекст</span>
            <textarea
              rows={5}
              value={form.context}
              onChange={(event) => updateField("context", event.target.value)}
              placeholder="Желаемый стиль, ограничения, аудитория, известные факты, тон"
            />
          </label>

          <div className="toggles">
            <label className="toggle">
              <input type="checkbox" checked={form.preserve_style} onChange={(event) => updateField("preserve_style", event.target.checked)} />
              <span>Сохранять стиль автора</span>
            </label>

            <label className="toggle">
              <input type="checkbox" checked={form.allow_restructure} onChange={(event) => updateField("allow_restructure", event.target.checked)} />
              <span>Разрешить глубокую перестройку</span>
            </label>

            <label className="toggle">
              <input
                type="checkbox"
                checked={form.ask_clarifying_questions}
                onChange={(event) => updateField("ask_clarifying_questions", event.target.checked)}
              />
              <span>Разрешить уточняющие вопросы</span>
            </label>

            <label className="toggle">
              <input type="checkbox" checked={form.web_search} onChange={(event) => updateField("web_search", event.target.checked)} />
              <span>Включить web search</span>
            </label>
          </div>

          <div className="actions-row">
            <button type="submit" disabled={loading}>
              {loading ? "Идёт обработка..." : "Запустить"}
            </button>
            <button
              type="button"
              className="ghost-button"
              disabled={loading}
              onClick={() => {
                setForm(initialForm);
                setExtraContext("");
                setError("");
                setResult(null);
              }}
            >
              Сбросить
            </button>
          </div>
        </form>

        <section className="result-card">
          <div className="section-head">
            <h2>Ход выполнения</h2>
            {loading && <span className="status-badge active">В работе · {elapsedSeconds}s</span>}
            {!loading && result && <span className="status-badge ok">{result.status}</span>}
          </div>

          <div className="timeline">
            {progressSteps.map((step) => (
              <div key={step.key} className={`timeline-step ${step.status}`}>
                <span className="timeline-dot" />
                <span>{step.label}</span>
              </div>
            ))}
          </div>
        </section>

        {error && <div className="error">{error}</div>}

        {result && (
          <section className="result-card">
            <div className="section-head">
              <h2>Метрики прогона</h2>
              <span className={`status-badge ${result.status === "completed" ? "ok" : "warn"}`}>{result.status}</span>
            </div>

            <div className="stats-grid">
              <article className="stat-card">
                <strong>Всего токенов</strong>
                <span>{formatInteger(result.total_tokens)}</span>
              </article>
              <article className="stat-card">
                <strong>Input / Output</strong>
                <span>{formatInteger(totals.inputTokens)} / {formatInteger(totals.outputTokens)}</span>
              </article>
              <article className="stat-card">
                <strong>Стоимость</strong>
                <span>{formatUsd(result.total_cost_usd)}</span>
              </article>
              <article className="stat-card">
                <strong>Вызовы агентов</strong>
                <span>{formatInteger(totals.agentCalls)}</span>
              </article>
              <article className="stat-card">
                <strong>Ошибки агентов</strong>
                <span>{formatInteger(totals.errors)}</span>
              </article>
              <article className="stat-card">
                <strong>Parse fallbacks</strong>
                <span>{formatInteger(totals.parseFallbacks)}</span>
              </article>
            </div>
          </section>
        )}

        {result?.status === "needs_user_input" && (
          <section className="result-card">
            <h2>Нужен дополнительный контекст</h2>
            <ul className="plain-list">
              {result.clarification_requests.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <form onSubmit={handleClarificationSubmit} className="form">
              <label>
                <span>Ответы на вопросы / дополнительный контекст</span>
                <textarea rows={5} value={extraContext} onChange={(event) => setExtraContext(event.target.value)} />
              </label>
              <button type="submit" disabled={loading || !extraContext.trim()}>
                Перезапустить с ответами
              </button>
            </form>
          </section>
        )}

        {result?.status === "completed" && result?.synthesis && (
          <section className="result-card">
            <h2>Итоговый синтез</h2>
            <p className="summary-text">{result.synthesis.summary}</p>

            <div className="result-block">
              <h3>Исправленный текст</h3>
              <pre>{result.synthesis.revised_text || "Синтез не предложил переписанный текст."}</pre>
            </div>

            <div className="two-col">
              <div className="result-block">
                <h3>Ключевые правки</h3>
                <ul className="plain-list">
                  {result.synthesis.key_changes.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className="result-block">
                <h3>Fact-check summary</h3>
                <ul className="plain-list">
                  {result.synthesis.fact_check_summary.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>

            {(result.synthesis.open_questions?.length > 0 ||
              result.synthesis.remaining_disagreements?.length > 0) && (
              <div className="two-col">
                <div className="result-block">
                  <h3>Открытые вопросы</h3>
                  <ul className="plain-list">
                    {result.synthesis.open_questions.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>

                <div className="result-block">
                  <h3>Оставшиеся разногласия</h3>
                  <ul className="plain-list">
                    {result.synthesis.remaining_disagreements.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {result.synthesis.sources?.length > 0 && (
              <div className="result-block">
                <h3>Источники</h3>
                <ul className="plain-list">
                  {result.synthesis.sources.map((item) => (
                    <li key={item}>
                      <a href={item} target="_blank" rel="noreferrer">
                        {item}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {result?.rounds?.length > 0 && (
          <section className="result-card">
            <h2>Панель хода спора и рассуждений</h2>

            {result.rounds.map((round) => (
              <article key={round.round_number} className="round-card">
                <div className="section-head">
                  <h3>Раунд {round.round_number}</h3>
                  <span className="status-badge neutral">{round.responses.length} ответов</span>
                </div>

                {round.judge_verdict && (
                  <div className="judge-card">
                    <div className="chips">
                      <span className="chip neutral">novelty {round.judge_verdict.argument_novelty}</span>
                      <span className={`chip ${round.judge_verdict.stagnation ? "warn" : "ok"}`}>
                        {round.judge_verdict.stagnation ? "stagnation" : "moving"}
                      </span>
                      <span className={`chip ${round.judge_verdict.should_stop ? "warn" : "ok"}`}>
                        {round.judge_verdict.should_stop ? "stop" : "continue"}
                      </span>
                    </div>

                    <div className="two-col">
                      <div>
                        <h4>Точки схождения</h4>
                        <ul className="plain-list">
                          {round.judge_verdict.convergence_points.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h4>Разногласия</h4>
                        <ul className="plain-list">
                          {round.judge_verdict.remaining_disagreements.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}

                <div className="responses">
                  {round.responses.map((response) => {
                    const agent = agentMap[response.agent_id];
                    return (
                      <section key={`${round.round_number}-${response.agent_id}`} className="response-card">
                        <div className="response-head">
                          <div>
                            <strong>{agent?.display_name || response.agent_id}</strong>
                            <div className="meta-line">
                              <span>{response.agent_id}</span>
                              <span>{response.anonymous_label}</span>
                              <span>{agent?.provider || "unknown"}</span>
                            </div>
                          </div>
                          <div className="chips">
                            <span className={`chip ${response.error ? "warn" : "ok"}`}>{response.error ? "error" : "ok"}</span>
                            <span className="chip neutral">{response.parsed.parse_quality}</span>
                          </div>
                        </div>

                        <div className="metrics-line">
                          <span>in {formatInteger(response.tokens_input)}</span>
                          <span>out {formatInteger(response.tokens_output)}</span>
                          <span>{formatUsd(response.cost_usd)}</span>
                          <span>{formatMs(response.latency_ms)}</span>
                        </div>

                        <p className="position-text">{response.parsed.position}</p>

                        {response.parsed.issues.length > 0 && (
                          <div className="result-block">
                            <h4>Проблемы</h4>
                            <ul className="plain-list">
                              {response.parsed.issues.map((issue, index) => (
                                <li key={`${response.agent_id}-issue-${index}`}>
                                  <strong>{issue.severity}:</strong> {issue.problem}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {response.parsed.clarification_requests.length > 0 && (
                          <div className="result-block">
                            <h4>Уточняющие вопросы</h4>
                            <ul className="plain-list">
                              {response.parsed.clarification_requests.map((item) => (
                                <li key={item}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {response.parsed.sources.length > 0 && (
                          <div className="result-block">
                            <h4>Источники агента</h4>
                            <ul className="plain-list">
                              {response.parsed.sources.map((item) => (
                                <li key={item}>
                                  <a href={item} target="_blank" rel="noreferrer">
                                    {item}
                                  </a>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {response.error && <div className="error compact">{response.error}</div>}

                        <details className="details-block">
                          <summary>Развернуть аргументацию и raw output</summary>
                          {response.parsed.revised_text && (
                            <>
                              <h4>Revised text</h4>
                              <pre>{response.parsed.revised_text}</pre>
                            </>
                          )}
                          <h4>Full argument</h4>
                          <pre>{response.parsed.full_argument}</pre>
                          <h4>Raw content</h4>
                          <pre>{response.raw_content || "Пусто"}</pre>
                        </details>
                      </section>
                    );
                  })}
                </div>
              </article>
            ))}
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
