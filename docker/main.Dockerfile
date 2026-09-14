FROM archivepodcast:ffmpeg AS ffmpeg-builder

# --- Python dependencies stage ---
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS python-builder

# Install system packages required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --extra web

# Copy application code and project metadata
COPY src src

# Install the project to ensure the command archivepodcast works
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=README.md,target=README.md \
    uv sync --frozen --no-dev --extra web

# --- Final runtime stage ---
FROM python:3.14-slim-trixie

WORKDIR /app

# Setup a non-root user
# Instance dir owned by ap, so the image runs without a mount and named volumes inherit the owner
RUN groupadd --system --gid 999 ap \
 && useradd --system --gid 999 --uid 999 --create-home ap \
 && install -d -o ap -g ap /app/instance

# Copy FFmpeg from builder
COPY --from=ffmpeg-builder /build/ffmpeg/ffmpeg /usr/local/bin/ffmpeg

# Copy Python virtual environment from builder
COPY --chown=ap:ap --from=python-builder /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
ENV AP_SIMPLE_LOGGING=1

USER ap:ap

EXPOSE 5100

CMD [ "uvicorn", "--factory", "archivepodcast.run_webapp:create_app", "--host", "0.0.0.0", "--port", "5100", "--proxy-headers", "--forwarded-allow-ips", "*" ]

# Stdlib instead of curl, the slim image has no curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --start-interval=2s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5100/api/health', timeout=4)"]
