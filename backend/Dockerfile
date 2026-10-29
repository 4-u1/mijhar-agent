FROM python:3.12-slim
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY mijhar ./mijhar
RUN uv sync --frozen --no-dev
ENV MIJHAR_DATA_DIR=/data PATH="/app/.venv/bin:$PATH"
VOLUME /data
EXPOSE 8000
# $PORT is set by Render/Railway; falls back to 8000 locally
CMD ["sh", "-c", "uvicorn mijhar.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
