FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    DATABASE_PATH=/data/queue_bot.db

WORKDIR /app
RUN pip install --no-cache-dir "poetry>=2.2,<3"
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --only main --no-root
COPY queue_bot ./queue_bot

VOLUME ["/data"]
CMD ["python", "-m", "queue_bot"]
