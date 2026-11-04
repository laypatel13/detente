FROM python:3.12-slim
RUN pip install --no-cache-dir uv==0.12.19
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend ./backend
EXPOSE 8100
CMD [".venv/bin/uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8100"]
