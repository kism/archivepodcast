# --- Minimal FFmpeg build stage ---
FROM debian:bookworm-slim AS ffmpeg-builder

# Basic build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    yasm \
    git \
    wget \
    tar \
    pkg-config \
    automake \
    autoconf \
    libtool \
    ca-certificates \
    libvorbis-dev \
    libopus-dev \
    libflac-dev \
    libmp3lame-dev \
    libogg-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Download FFmpeg
RUN wget https://ffmpeg.org/releases/ffmpeg-7.0.tar.gz && \
    tar xzf ffmpeg-7.0.tar.gz && \
    mv ffmpeg-7.0 ffmpeg

WORKDIR /build/ffmpeg

# Configure FFmpeg with audio-only support
RUN ./configure \
    --disable-everything \
    --disable-everything \
    --enable-small \
    --disable-autodetect \
    --disable-debug \
    --disable-doc \
    --disable-network \
    --disable-hwaccels \
    --disable-devices \
    --disable-iconv \
    --enable-ffmpeg \
    --enable-protocol=file \
    --enable-demuxer=wav \
    --enable-demuxer=mp3 \
    --enable-decoder=pcm_s16le \
    --enable-decoder=pcm_s16be \
    --enable-decoder=mp3 \
    --enable-decoder=mp3float \
    --enable-encoder=libmp3lame \
    --enable-muxer=mp3 \
    --enable-libmp3lame \
    --enable-swresample \
    --enable-avfilter \
    --enable-filter=aformat \
    --enable-filter=anull \
    --enable-filter=aresample

RUN make -j$(nproc) && make install


# --- Python dependencies stage ---
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS python-builder

# Required for building Python dependencies
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
COPY pyproject.toml README.md ./

# Install the project to ensure the command archivepodcast works
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen

# --- Final runtime stage ---
FROM python:3.14-slim-bookworm

# Copy FFmpeg from builder
COPY --from=ffmpeg-builder /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg-builder /usr/local/bin/ffprobe /usr/local/bin/ffprobe

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    lame \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python virtual environment from builder
COPY --from=python-builder /app/.venv /app/.venv
COPY --from=python-builder /app/archivepodcast /app/archivepodcast

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
ENV AP_SIMPLE_LOGGING=1

EXPOSE 5100

CMD [ "waitress-serve", "--listen", "0.0.0.0:5100", "--trusted-proxy", "*", "--trusted-proxy-headers", "x-forwarded-for x-forwarded-proto x-forwarded-port", "--log-untrusted-proxy-headers", "--clear-untrusted-proxy-headers", "--threads", "4", "--call", "archivepodcast:create_app" ]
