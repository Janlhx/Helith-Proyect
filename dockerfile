FROM python:3.11-slim

# Evitar prompts interactivos durante el build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copiar archivos de dependencias primero (mejor cache de layers)
COPY pyproject.toml .

# Instalar dependencias
RUN uv sync --no-dev

# Copiar el resto del código
COPY . .

# Puerto para Flask keep-alive
EXPOSE 8080

# Comando de inicio
CMD ["uv", "run", "python", "main.py"]