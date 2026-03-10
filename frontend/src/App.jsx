import { useState } from "react";

const API_BASE = "http://127.0.0.1:8001";

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

function App() {
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [extraContext, setExtraContext] = useState("");

  async function submit(payload) {
    setLoading(true);
    setError("");
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

  return (
    <div className="page">
      <aside className="hero">
        <p className="eyebrow">SciProof</p>
        <h1>Коллективная редактура текста и проверка фактов</h1>
        <p className="lead">
          Вставьте научный или деловой текст, задайте цель правки и получите
          исправленную версию после multi-agent review.
        </p>
      </aside>

      <main className="panel">
        <form className="form" onSubmit={handleSubmit}>
          <div className="grid">
            <label>
              <span>Сценарий</span>
              <select
                value={form.task_type}
                onChange={(event) => updateField("task_type", event.target.value)}
              >
                <option value="review_text">Review текста</option>
                <option value="fact_check">Проверка факта</option>
              </select>
            </label>

            <label>
              <span>Раунды</span>
              <select
                value={form.max_rounds}
                onChange={(event) => updateField("max_rounds", Number(event.target.value))}
              >
                <option value={1}>1</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
              </select>
            </label>
          </div>

          <label>
            <span>Задача / вопрос</span>
            <textarea
              rows={3}
              value={form.question}
              onChange={(event) => updateField("question", event.target.value)}
            />
          </label>

          <label>
            <span>Исходный текст</span>
            <textarea
              rows={10}
              value={form.source_text}
              onChange={(event) => updateField("source_text", event.target.value)}
              placeholder="Вставьте фрагмент текста объёмом примерно 3–4 тыс. знаков"
            />
          </label>

          <label>
            <span>Дополнительный контекст</span>
            <textarea
              rows={4}
              value={form.context}
              onChange={(event) => updateField("context", event.target.value)}
              placeholder="Желаемый стиль, ограничения, целевая аудитория, известные факты"
            />
          </label>

          <div className="toggles">
            <label className="toggle">
              <input
                type="checkbox"
                checked={form.preserve_style}
                onChange={(event) => updateField("preserve_style", event.target.checked)}
              />
              <span>Сохранять стиль автора</span>
            </label>

            <label className="toggle">
              <input
                type="checkbox"
                checked={form.allow_restructure}
                onChange={(event) => updateField("allow_restructure", event.target.checked)}
              />
              <span>Разрешить глубокую перестройку</span>
            </label>

            <label className="toggle">
              <input
                type="checkbox"
                checked={form.web_search}
                onChange={(event) => updateField("web_search", event.target.checked)}
              />
              <span>Включить web search</span>
            </label>
          </div>

          <button type="submit" disabled={loading}>
            {loading ? "Идёт обработка..." : "Запустить"}
          </button>
        </form>

        {error && <div className="error">{error}</div>}

        {result?.status === "needs_user_input" && (
          <section className="result-card">
            <h2>Нужен дополнительный контекст</h2>
            <ul>
              {result.clarification_requests.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <form onSubmit={handleClarificationSubmit}>
              <label>
                <span>Ответы на вопросы / дополнительный контекст</span>
                <textarea
                  rows={5}
                  value={extraContext}
                  onChange={(event) => setExtraContext(event.target.value)}
                />
              </label>
              <button type="submit" disabled={loading || !extraContext.trim()}>
                Перезапустить с ответами
              </button>
            </form>
          </section>
        )}

        {result?.status === "completed" && result?.synthesis && (
          <section className="result-card">
            <h2>Итог</h2>
            <p>{result.synthesis.summary}</p>

            <div className="result-block">
              <h3>Исправленный текст</h3>
              <pre>{result.synthesis.revised_text}</pre>
            </div>

            <div className="two-col">
              <div className="result-block">
                <h3>Ключевые правки</h3>
                <ul>
                  {result.synthesis.key_changes.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className="result-block">
                <h3>Фактчекинг</h3>
                <ul>
                  {result.synthesis.fact_check_summary.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="result-block">
              <h3>Раунды</h3>
              {result.rounds.map((round) => (
                <article key={round.round_number} className="round-card">
                  <h4>Раунд {round.round_number}</h4>
                  <div className="responses">
                    {round.responses.map((response) => (
                      <section key={`${round.round_number}-${response.agent_id}`} className="response-card">
                        <strong>{response.agent_id}</strong>
                        <p>{response.parsed.position}</p>
                        {response.parsed.issues.length > 0 && (
                          <ul>
                            {response.parsed.issues.map((issue, index) => (
                              <li key={`${response.agent_id}-${index}`}>
                                {issue.problem}
                              </li>
                            ))}
                          </ul>
                        )}
                      </section>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;

