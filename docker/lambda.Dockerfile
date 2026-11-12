FROM archivepodcast:ffmpeg AS ffmpeg-builder

FROM public.ecr.aws/lambda/python:3.14 AS python-source

FROM ghcr.io/astral-sh/uv:0.12 AS uv-base

# --- Python dependencies stage ---
FROM public.ecr.aws/amazonlinux/amazonlinux:2023 AS python-builder

# Install system packages required for building Python packages
RUN dnf install -y \
    gcc \
    gcc-c++ \
    make \
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
    uv sync --frozen --no-install-project --no-dev --extra web

# Copy application code and project metadata
COPY src src

# Install the project to ensure the command archivepodcast works
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=README.md,target=README.md \
    uv sync --frozen --no-dev --extra web

# --- Lambda container image stage ---
# Instance config is loaded from SSM at invoke time, see lambda_handler.py
FROM python-source AS lambda

COPY --from=ffmpeg-builder /build/ffmpeg/ffmpeg /usr/local/bin/ffmpeg
COPY --from=python-builder /app/.venv/lib/python3.14/site-packages/ ${LAMBDA_TASK_ROOT}/
# Project is installed editable, so copy the source too
COPY --from=python-builder /app/src/archivepodcast ${LAMBDA_TASK_ROOT}/archivepodcast

CMD [ "archivepodcast.lambda_handler.handler" ]
