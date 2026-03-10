# SciProof

Локальный MVP для multi-agent review и fact-check научных и деловых текстов.

## Что уже работает

- `review_text` для редактуры и улучшения больших текстовых блоков
- `fact_check` для проверки конкретных утверждений
- 4 агента + судья
- web search через Brave API
- подсчёт токенов, стоимости и latency по агентам
- сохранение сессий и истории в локальный file store
- восстановление прошлых прогонов через UI и API

## Локальные адреса

- frontend: `http://127.0.0.1:5173`
- backend: `http://127.0.0.1:8004`
- health: `http://127.0.0.1:8004/api/health`
- metrics: `http://127.0.0.1:8004/api/metrics/summary`

## Конфигурация

1. Скопируйте `config/agents.example.yaml` в `config/agents.yaml`, если хотите хранить локальные настройки отдельно.
2. Положите секреты в переменные окружения или используйте `secrets.txt` для локального запуска.
3. Для поиска нужен `BRAVE_API_KEY`.

## Запуск backend

```powershell
python scripts/run_backend_local.py
```

`run_backend_local.py` читает `secrets.txt`, нормализует локальные ключи и поднимает backend на порту из `config/settings.yaml`.

## Запуск frontend

```powershell
cd frontend
npm install
npm run dev
```

## История сессий

- локальный store: `data/sessions/`
- список сессий: `GET /api/sessions`
- полная сохранённая сессия: `GET /api/sessions/{session_id}`
- каждая новая сессия автоматически сохраняется после `POST /api/sessions`

## Тесты

```powershell
pytest -q backend/tests
```

```powershell
cd frontend
npm run build
```

## Полезный smoke-check

1. Откройте frontend.
2. Нажмите `sample review` или `sample fact-check`.
3. Запустите сессию.
4. Проверьте:
   - `Диагностика`
   - `Метрики прогона`
   - `Панель хода спора и рассуждений`
   - `History`
