FROM python:3.11-slim

# Prevent interactive prompts during build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (better layer caching)
COPY pyproject.toml .

# Install all dependencies (including gunicorn)
RUN uv sync --no-dev

# Copy the rest of the code
COPY . .

# Port for Flask / Gunicorn
EXPOSE 8080

# Gunicorn: 1 worker (Discord bot can't be multi-process), 4 threads for concurrency
# PORT is provided by Render automatically at runtime
CMD ["uv", "run", "gunicorn", "main:app", \
     "--workers", "1", \
     "--threads", "4", \
     "--bind", "0.0.0.0:8080", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--log-level", "info"]