FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    DATABASE_PATH=/data/queue_bot.db

WORKDIR /app
COPY pyproject.toml poetry.lock README.md ./
RUN pip install --no-cache-dir "poetry>=2.2,<3" \
    && poetry install --only main --no-root \
    && pip uninstall -y poetry \
    && rm -rf /root/.cache

COPY queue_bot ./queue_bot

# The bot doesn't need root. /data is created here so that a named volume
# mounted over it inherits the ownership.
RUN useradd --system --uid 10001 --home-dir /app bot \
    && mkdir -p /data && chown bot:bot /data
USER bot

VOLUME ["/data"]
CMD ["python", "-m", "queue_bot"]
