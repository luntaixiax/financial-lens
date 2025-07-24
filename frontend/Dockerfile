FROM python:3.10-slim-bookworm

WORKDIR /app

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/ 

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc curl ca-certificates \
    && apt-get autoremove

COPY . .

RUN uv sync --locked --all-extras --dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8501