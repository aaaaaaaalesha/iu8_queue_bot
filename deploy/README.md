# Деплой

Деплой запускается вручную: *Actions → deploy → Run workflow*, ветка `main`.
Workflow:

1. прогоняет проверки из `main.yaml`: ruff, mypy, pytest;
2. собирает Docker-образ для `linux/amd64` и `linux/arm64` и публикует его в
   GitHub Container Registry: `ghcr.io/aaaaaaaalesha/iu8_queue_bot:<sha>` и `:latest`;
3. заходит на сервер по SSH, записывает `.env` с токеном, копирует
   `docker-compose.yml` и перезапускает бота на новом образе;
4. через 15 секунд проверяет, что контейнер работает и не перезапускался.
   Если нет, выводит логи и помечает деплой упавшим.

Бот работает через long polling, поэтому входящие порты, домен и HTTPS не нужны.
Достаточно любого сервера с Linux (Ubuntu или Debian), Docker и доступом по SSH.
База SQLite лежит в Docker-томе `queue-bot_bot-data` и переживает передеплои.

Требования к серверу минимальные: 1 vCPU, 512 MB–1 GB RAM и пара гигабайт диска.
Сервер должен работать постоянно: без засыпания и с постоянным диском, иначе
очереди и запланированные запуски будут теряться.

## Первоначальная настройка (один раз)

### 1. Сервер

Создайте сервер с Ubuntu 24.04 (x86-64 или ARM) и добавьте свой SSH-ключ.
Открывать порты, кроме SSH, не нужно.

Зайдите на сервер и подготовьте его: установится Docker и создастся `/opt/queue-bot`.

```bash
ssh ubuntu@<IP сервера>
curl -fsSL https://raw.githubusercontent.com/aaaaaaaalesha/iu8_queue_bot/main/deploy/setup-server.sh | bash
exit
```

### 2. Ключ для деплоя

Отдельная пара ключей, которой пользуется только GitHub Actions. Создайте её на своём компьютере:

```bash
ssh-keygen -t ed25519 -N "" -C "github-deploy" -f ./queue_bot_deploy
ssh-copy-id -i ./queue_bot_deploy.pub ubuntu@<IP сервера>
# Отпечаток хоста для защиты от подмены сервера:
ssh-keyscan -t ed25519 <IP сервера> > ./queue_bot_known_hosts
```

Сверьте отпечаток из `queue_bot_known_hosts` с тем, что показывал `ssh` при первом входе на сервер.

### 3. Секреты в GitHub

*Settings → Environments → New environment* → `production`. В *Deployment branches*
лучше выбрать *Selected branches* → `main`, чтобы секреты были доступны только
деплою из `main`. Затем в *Environment secrets* добавьте:

| Секрет | Значение |
|---|---|
| `TELE_API_TOKEN` | токен бота от @BotFather |
| `DEPLOY_HOST` | IP или домен сервера |
| `DEPLOY_USER` | пользователь на сервере, например `ubuntu` |
| `DEPLOY_SSH_KEY` | содержимое приватного ключа `queue_bot_deploy` целиком |
| `DEPLOY_KNOWN_HOSTS` | содержимое `queue_bot_known_hosts` |

Токен никуда не нужно пересылать. Его видит только workflow деплоя: GitHub маскирует
секреты в логах, а на сервер токен попадает через stdin в `/opt/queue-bot/.env`
с правами `600`. То же можно сделать через `gh` без записи в историю shell:

```bash
gh secret set TELE_API_TOKEN --env production          # значение вводится интерактивно
gh secret set DEPLOY_SSH_KEY --env production < ./queue_bot_deploy
gh secret set DEPLOY_KNOWN_HOSTS --env production < ./queue_bot_known_hosts
gh secret set DEPLOY_HOST --env production --body "<IP сервера>"
gh secret set DEPLOY_USER --env production --body "ubuntu"
```

После этого локальные файлы `queue_bot_deploy*` можно удалить.

### 4. Остановите старый экземпляр бота

Telegram отдаёт обновления только одному процессу с long polling. Если бот ещё
запущен в другом месте, остановите его, иначе экземпляры
будут мешать друг другу (`TelegramConflictError`).

### 5. Деплой

*Actions → deploy → Run workflow*, ветка `main`. Этим же способом выкатываются
все следующие версии.

## Эксплуатация

```bash
ssh ubuntu@<IP сервера>
cd /opt/queue-bot
docker compose logs -f bot        # логи
docker compose restart bot        # перезапуск
docker compose ps                 # состояние

# Резервная копия базы:
docker compose exec bot python -c \
  "import sqlite3; sqlite3.connect('/data/queue_bot.db').backup(sqlite3.connect('/data/backup.db'))"
docker compose cp bot:/data/backup.db ./queue_bot-$(date +%F).db
```

Откат на предыдущую версию: *Actions → deploy* → нужный успешный запуск → *Re-run all jobs*.
Каждый деплой использует образ с тегом конкретного коммита.

Сменить токен: обновите секрет `TELE_API_TOKEN` и запустите деплой.

## Автоматический деплой

Чтобы выкатывать бота при каждом влитии в `main`, добавьте в `on:` файла
`.github/workflows/deploy.yaml`:

```yaml
  push:
    branches: [ main ]
```
