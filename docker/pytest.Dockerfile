# --- Minimal FFmpeg build stage ---

FROM ghcr.io/astral-sh/uv:0.9 AS uv-base

FROM archivepodcast

COPY --from=uv-base /uv /uvx /bin/

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --extra test

# Copy application code and project metadata
COPY archivepodcast archivepodcast
COPY pyproject.toml README.md ./

# Install the project to ensure the command archivepodcast works
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --extra test

WORKDIR /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
ENV AP_SIMPLE_LOGGING=1

USER 1001:1001

# Pytest specific
COPY tests tests
COPY uv.lock uv.lock
COPY pyproject.toml pyproject.toml
RUN mkdir instance
RUN echo "hello" > instance/config.json
RUN chmod 000 instance/config.json
CMD ["pytest"]
