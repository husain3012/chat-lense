FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/chromium
RUN uv run --no-sync playwright install --with-deps chromium --only-shell \
    && apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-noto-core fonts-noto-cjk fonts-noto-color-emoji \
    && chmod -R a+rX /opt/chromium && rm -rf /var/lib/apt/lists/*
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
RUN useradd --create-home chatlens
USER chatlens
EXPOSE 8000
CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8000"]
