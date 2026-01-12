FROM archivepodcast:ffmpeg AS ffmpeg-builder

# --- Python dependencies stage ---
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS python-builder

# Install system packages required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

# Copy application code and project metadata
COPY archivepodcast archivepodcast

# Install the project to ensure the command archivepodcast works
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=README.md,target=README.md \
    uv sync --frozen

# --- Final runtime stage ---
FROM python:3.14-slim-trixie

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Setup a non-root user
RUN groupadd --system --gid 999 ap \
 && useradd --system --gid 999 --uid 999 --create-home ap

# Copy FFmpeg from builder
COPY --from=ffmpeg-builder /build/ffmpeg/ffmpeg /usr/local/bin/ffmpeg

# Copy Python virtual environment from builder
COPY --chown=ap:ap --from=python-builder /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
ENV AP_SIMPLE_LOGGING=1

USER ap:ap

EXPOSE 5100

CMD [ "waitress-serve", "--listen", "0.0.0.0:5100", "--trusted-proxy", "*", "--trusted-proxy-headers", "x-forwarded-for x-forwarded-proto x-forwarded-port", "--log-untrusted-proxy-headers", "--clear-untrusted-proxy-headers", "--threads", "4", "--call", "archivepodcast:create_app" ]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:5100/api/health || exit 1
