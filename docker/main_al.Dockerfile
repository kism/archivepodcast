FROM archivepodcast:ffmpeg AS ffmpeg-builder

FROM public.ecr.aws/lambda/python:3.14 AS python-source

FROM ghcr.io/astral-sh/uv:0.9 AS uv-base

# --- Python dependencies stage ---
FROM public.ecr.aws/amazonlinux/amazonlinux:2023 AS python-builder

# Install system packages required for building Python packages
RUN dnf install -y \
    gcc \
    gcc-c++ \
    make \
    libxml2-devel \
    libxslt-devel \
    file-libs \
    && dnf clean all

# Copy Python binaries from Python base image
COPY --from=python-source /var/lang /var/lang
ENV PATH="/var/lang/bin:$PATH"

# Install UV for faster package management
COPY --from=uv-base /uv /uvx /bin/

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
COPY pyproject.toml README.md ./

# Install the project to ensure the command archivepodcast works
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen

# --- Final runtime stage ---
FROM public.ecr.aws/amazonlinux/amazonlinux:2023-minimal

WORKDIR /app

# Install runtime dependencies
RUN dnf install -y \
    file-libs \
    libxml2 \
    libxslt \
    && dnf clean all

# Copy FFmpeg from builder
COPY --from=ffmpeg-builder /build/ffmpeg/ffmpeg /usr/local/bin/ffmpeg

# Copy Python binaries from Python base image
COPY --from=python-source /var/lang /var/lang
ENV PATH="/var/lang/bin:$PATH"

# Copy Python virtual environment from builder
COPY --from=python-builder /app/.venv /app/.venv
COPY --from=python-builder /app/archivepodcast /app/archivepodcast

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
ENV AP_SIMPLE_LOGGING=1

EXPOSE 5100

USER 1001:1001

CMD [ "waitress-serve", "--listen", "0.0.0.0:5100", "--trusted-proxy", "*", "--trusted-proxy-headers", "x-forwarded-for x-forwarded-proto x-forwarded-port", "--log-untrusted-proxy-headers", "--clear-untrusted-proxy-headers", "--threads", "4", "--call", "archivepodcast:create_app" ]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:5100/api/health || exit 1
