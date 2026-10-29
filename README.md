# Шаг за шагом

**Виртуальный равный консультант** — анонимный чат-бот на основе ИИ (YandexGPT), который поддерживает людей в выздоровлении от алкогольной и наркотической зависимости по принципам программы «12 шагов» 24 часа в сутки и при кризисе направляет к живой помощи.

## Команда (группа П-311)

| Участник | Роль |
|---|---|
| Локутанский Данила | Тимлид, бэкенд |
| Салахов Карим | Фронтенд, дизайн |

## Этапы проекта

| Этап | Срок | Статус |
|---|---|---|
| 1. Анализ | 19.10 | готово |
| 2. Разработка (BE, FE, тесты, инфраструктура, e2e) | 27.11 | в работе: MVP готов |
| 3. Релиз | 01.12 | — |

## Документы этапа 1 (бизнес-анализ)

1. [Анализ предметной области](01_subject_area.md)
2. [Проблема, которую решает проект](02_problem.md)
3. [Функционал](03_functions.md)
4. [Архитектура](04_architecture.md)
5. [Краткая сводка](05_summary.md)
6. Схема архитектуры: [architecture.excalidraw](architecture.excalidraw) (открывается на [excalidraw.com](https://excalidraw.com)), картинкой — [architecture_preview.png](architecture_preview.png)

## Репозитории

- GitHub — основной репозиторий, ревью и Pull Request'ы.
- [SourceCraft](https://sourcecraft.dev/danillokutanskij/stepafterstep) — зеркало репозитория (те же ветки и коммиты).

## Что умеет

- Анонимный чат без регистрации (пациент или родственник).
- Ответы YandexGPT в роли «равного консультанта» с опорой на базу знаний 12 шагов.
- **Кризисный сценарий**: при признаках угрозы жизни, а также на фразы вроде «мне плохо», «помогите», «не справляюсь» — сразу карточка помощи (112, телефон доверия, клиника).
- **Защита от обхода ограничений** в три слоя: фильтр входящих сообщений → ИИ-проверка → проверка ответа перед показом.
- Счётчик трезвых дней, этапы, «шаг дня», удаление истории одной кнопкой.
- **Виджет** для сайта клиники — одна строка кода.
- **Кабинет клиники**: обезличенная статистика (сколько диалогов, в какие часы, сколько кризисов).
- **Демо-режим**: без ключа Яндекса бот отвечает по шаблонам из базы знаний — удобно для показа.

## Структура

```
backend/            сервер на Python (FastAPI)
  app/main.py         все адреса API
  app/safety.py       фильтры: кризис, атаки, проверка ответа
  app/prompts.py      промпты для YandexGPT
  app/llm.py          подключение к YandexGPT + демо-режим
  app/knowledge*.     база знаний (12 шагов, техники самопомощи)
  tests/              автотесты (pytest)
frontend/           сайт (HTML + CSS + JavaScript, без сборки)
  index.html          чат
  clinic-demo.html    демо-сайт клиники с виджетом
  admin.html          кабинет клиники
  widget.js           виджет для встраивания
docker-compose.yml  запуск всего проекта одной командой
01–05_*.md          документы этапа анализа
```

## Запуск

### Вариант 1. Docker (рекомендуется)

1. Установить [Docker Desktop](https://www.docker.com/products/docker-desktop/) и запустить его.
2. В папке проекта скопировать `.env.example` в `.env` (можно оставить пустым — будет демо-режим).
3. В терминале в папке проекта:
   ```
   docker compose up --build
   ```
4. Открыть в браузере:
   - http://localhost:8080/clinic-demo.html — сайт клиники с виджетом
   - http://localhost:8080/ — чат
   - http://localhost:8080/admin.html — кабинет клиники (ключ `demo`, токен `demo-admin`)

### Вариант 2. Без Docker (нужен Python 3.11+)

```
cd backend
python -m venv .venv
.venv\Scripts\activate          (Windows)   |   source .venv/bin/activate   (Mac/Linux)
pip install -r requirements.txt
set STATIC_DIR=../frontend      (Windows)   |   export STATIC_DIR=../frontend
uvicorn app.main:app --reload
```
Открыть http://localhost:8000/clinic-demo.html. База данных — файл `shag.db` (SQLite).

### Подключить YandexGPT

1. В [Yandex Cloud](https://console.yandex.cloud) создать каталог и сервисный аккаунт с ролью `ai.languageModels.user`.
2. Создать для него API-ключ.
3. В `.env` заполнить `YANDEX_API_KEY` и `YANDEX_FOLDER_ID` (идентификатор каталога).
4. Перезапустить. Проверка: http://localhost:8080/api/health должен показать `"llm": "yandexgpt"`.

## Тесты

```
cd backend
python -m pytest -v
```
63 теста: фильтры безопасности (кризисные фразы, «мне плохо», атаки, опасные ответы), весь сценарий API, работа с YandexGPT (с подменой ответов нейросети). Испытание фильтров безопасности на рабочем и контрольном наборах фраз: `python -m eval.eval_safety` (из папки backend).

Автотесты запускаются на GitHub Actions (`.github/workflows/tests.yml`) при каждом push и Pull Request: установка зависимостей, `pytest` и испытание фильтров безопасности.

## API

| Метод | Адрес | Что делает |
|---|---|---|
| GET | `/api/health` | Проверка работы, режим ИИ |
| POST | `/api/sessions` | Создать анонимную сессию |
| GET | `/api/sessions/{id}` | Данные сессии, счётчик дней |
| GET | `/api/sessions/{id}/messages` | История |
| DELETE | `/api/sessions/{id}` | Удалить историю |
| PUT | `/api/sessions/{id}/sober-date` | Дата начала трезвости |
| GET | `/api/sessions/{id}/help` | Контакты помощи |
| POST | `/api/chat` | Отправить сообщение |
| POST | `/api/messages/{id}/rating` | Оценка ответа |
| GET | `/api/step-of-day` | Шаг дня |
| GET | `/api/clinics/{key}/stats` | Статистика клиники (заголовок `X-Admin-Token`) |

Интерактивная документация API: http://localhost:8080/api/docs (без Docker — http://localhost:8000/api/docs).

## Что дальше

- Перенести базу знаний и реальные истории выздоровления (анонимизированные, с согласия авторов) в Yandex AI Search.
- Развернуть в Яндекс Облаке: Container Registry + Serverless Containers + Managed PostgreSQL + Lockbox.
- Голосовой ввод через SpeechKit, дашборд в DataLens.
- Проверить номер телефона доверия для региона и вписать в `HELPLINE_PHONE`.

> Бот не является медицинским изделием и не заменяет врача, психолога, группу или спонсора.
