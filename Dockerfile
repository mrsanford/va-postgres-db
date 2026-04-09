FROM ghcr.io/astral-sh/uv:debian

WORKDIR /app

COPY pyproject.toml uv.lock .python-version* ./

# --frozen ensures uv doesn't modify the lockfile
# --no-dev excludes development dependencies for a smaller image
RUN uv sync --frozen --no-dev

COPY src/ ./src/
COPY data/ ./data/
COPY db/ ./db/
COPY compute.py .

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "compute.py"]