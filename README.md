<h1 align="center"> 🚶IU8-QueueBot🚶🚶 </h1>

[comment]: <> (Badges)

<p align="center">
  <a href="https://img.shields.io/badge/aiogram-v3.31-orange?style=plastic">
    <img alt="Aiogram" src="https://img.shields.io/badge/aiogram-v3.31-orange?style=plastic">
  </a>
  <a href="https://github.com/aaaaaaaalesha/iu8_queue_bot/deployments/activity_log?environment=iu8-queue-bot">
    <img alt="Deployment" src="https://img.shields.io/github/deployments/aaaaaaaalesha/iu8_queue_bot/iu8-queue-bot?style=plastic">
  </a>
  <a href="https://www.npmjs.com/package/readme-md-generator">
    <img alt="Build Status" src="https://github.com/aaaaaaaalesha/iu8_queue_bot/actions/workflows/main.yaml/badge.svg">
  </a>
  <a href="https://www.codefactor.io/repository/github/aaaaaaaalesha/iu8_queue_bot/overview/main">
    <img alt="CodeFactor" src="https://www.codefactor.io/repository/github/aaaaaaaalesha/iu8_queue_bot/badge/main?style=plastic">
  </a>
  <a href="https://img.shields.io/github/languages/code-size/aaaaaaaalesha/iu8_queue_bot?style=plastic">
    <img alt="GitHub code size in bytes" src="https://img.shields.io/github/languages/code-size/aaaaaaaalesha/iu8_queue_bot?style=plastic">
  </a>
  <a href="https://img.shields.io/github/stars/aaaaaaaalesha/iu8_queue_bot?style=plastic">
    <img alt="Stars" src="https://img.shields.io/github/stars/aaaaaaaalesha/iu8_queue_bot?style=plastic" />
  </a>
  <a href="https://img.shields.io/github/watchers/aaaaaaaalesha/iu8_queue_bot?style=plastic">
    <img alt="GitHubWatchers" src="https://img.shields.io/github/watchers/aaaaaaaalesha/iu8_queue_bot?style=plastic">
  </a>
</p>

[comment]: <> (Logo)
<p align="center">
  <a href="https://t.me/iu8_queue_bot">
    <img alt="queue_bot" height="200" width="200" src="https://user-images.githubusercontent.com/55093100/147390446-d783063a-e68e-4caa-9711-731c13a9fd2d.png"/>
  </a>
</p>

[comment]: <> (Techs)
<p align="center">
  <a href="#">
    <img alt="Python" src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54">
  </a>
  <a href="#">
    <img alt="SQLite" src="https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white">
  </a>
  <a href="#">
    <img alt="GitHub Actions" src="https://img.shields.io/badge/githubactions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white">
  </a>
  <a href="#">
    <img alt="Heroku" src="https://img.shields.io/badge/heroku-%23430098.svg?style=for-the-badge&logo=heroku&logoColor=white">
  </a>
</p>

---

## Телеграм-бот для создания очередей в групповых чатах

Этот бот поможет запланировать очередь на определённую дату и время, своевременно запустить её в вашем групповом чате!

Попробуйте [@iu8_queue_bot](https://t.me/iu8_queue_bot) сами, а если возникли вопросы, смотрите, как пользоваться ботом,
ниже.

## Как пользоваться?

[comment]: <> (How to use bot)
<p align="center">
<img alt="queue_bot" src="https://raw.githubusercontent.com/aaaaaaaalesha/iu8_queue_bot/main/assets/how_to_use.gif"/>
</p>

## Запуск

Нужен Python 3.12+ (рекомендуется 3.13).

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # и укажите TELE_API_TOKEN
python -m queue_bot
```

Или в Docker:

```bash
docker build -t queue-bot .
docker run -d --env-file .env -v queue-bot-data:/data queue-bot
```

Для разработки: `pip install -e ".[dev]"`, затем `ruff check .`, `mypy` и `pytest`.

## Устройство

```
queue_bot/
├── app.py            # сборка Bot/Dispatcher, запуск и остановка
├── config.py         # настройки из переменных окружения
├── models.py         # доменные модели
├── db/
│   ├── database.py   # одно соединение aiosqlite, сериализованные транзакции
│   ├── migrations.py # схема (PRAGMA user_version) и импорт данных старой версии
│   └── repository.py # весь SQL; каждая операция с очередью — одна транзакция
├── services/
│   ├── scheduler.py  # запуск запланированных очередей (переживает перезапуск)
│   ├── updater.py    # объединяющее обновление сообщения очереди
│   ├── planning.py   # разбор времени запуска
│   └── rendering.py  # тексты сообщений
├── handlers/         # обработчики aiogram 3 (клиент, админ, события чата, ошибки)
└── keyboards/        # клавиатуры и календарь
```

Состав очереди хранится в БД (`queue_members`), а не в тексте сообщения:
каждое нажатие кнопки атомарно применяется к актуальному состоянию, поэтому
одновременные нажатия не затирают друг друга. Сообщение очереди редактируется
фоновой задачей, которая объединяет все нажатия за интервал
`QUEUE_EDIT_INTERVAL` в одно редактирование — бот не упирается в лимиты
Telegram, даже когда в очередь встают десятки людей одновременно.

## Author

#### Copyright © 2021, [Alexey Alexandrov](https://github.com/aaaaaaaalesha)

[![Telegram](https://img.shields.io/badge/aaaaaaaalesha-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/aaaaaaaalesha)
<a href="mailto:sks2311211@mail.ru">
<img alt="build status" src="https://img.shields.io/badge/-sks2311211@mail.ru-c14438?style=flat&logo=Gmail&logoColor=white&link=mailto:sks2311211@mail.ru" />
</a>

