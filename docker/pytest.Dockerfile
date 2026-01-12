# --- Pytest specific stage ---

FROM ghcr.io/astral-sh/uv:0.9 AS uv-base

FROM archivepodcast

USER root

COPY --from=uv-base /uv /uvx /bin/

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --extra test

# Copy application code
COPY --chown=ap:ap archivepodcast archivepodcast

WORKDIR /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
ENV AP_SIMPLE_LOGGING=1

# Pytest specific
COPY --chown=ap:ap tests tests
COPY --chown=ap:ap uv.lock uv.lock
COPY --chown=ap:ap pyproject.toml pyproject.toml
RUN mkdir -p instance
RUN chmod 700 instance
RUN chown ap:ap instance
RUN echo "hello" > instance/config.json
RUN chmod 000 instance/config.json

# User and permissions
USER ap:ap

CMD ["pytest", "--no-cov", "-o", "cache_dir=/tmp/.pytest_cache"]
