FROM ghcr.io/astral-sh/uv:debian

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

COPY pyproject.toml uv.lock .python-version* ./

# --frozen ensures uv doesn't modify the lockfile
RUN uv sync --frozen

COPY src/ ./src/
COPY db/ ./db/
COPY compute.py .

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "compute.py"]