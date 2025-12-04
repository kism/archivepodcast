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
    --enable-small \
    --disable-autodetect \
    --disable-debug \
    --disable-doc \
    --disable-network \
    \
    # Enable core components you want
    --enable-ffmpeg \
    --enable-ffprobe \
    \
    # Enable protocols (needed to read files)
    --enable-protocol=file \
    \
    # Enable audio demuxers
    --enable-demuxer=wav \
    --enable-demuxer=mp3 \
    --enable-demuxer=ogg \
    --enable-demuxer=flac \
    --enable-demuxer=opus \
    \
    # Enable audio encoders
    --enable-encoder=pcm_s16le \
    --enable-encoder=libmp3lame \
    --enable-encoder=flac \
    --enable-encoder=opus \
    \
    # Enable audio decoders
    --enable-decoder=pcm_s16le \
    --enable-decoder=mp3 \
    --enable-decoder=vorbis \
    --enable-decoder=flac \
    --enable-decoder=opus \
    \
    # Enable audio muxers
    --enable-muxer=wav \
    --enable-muxer=mp3 \
    --enable-muxer=ogg \
    --enable-muxer=opus \
    --enable-muxer=flac \
    \
    # External libs
    --enable-libmp3lame \
    --enable-libopus \
    --enable-libvorbis \
    \
    # Need to keep some core components for ffmpeg to work
    --enable-swresample \
    --enable-avfilter \
    --disable-swscale \
    --disable-avdevice \
    --disable-postproc \
    \
    # Enable minimal filters that ffmpeg requires
    --enable-filter=aformat \
    --enable-filter=anull \
    --enable-filter=atrim \
    --enable-filter=aresample \
    --enable-filter=format \
    --enable-filter=hflip \
    --enable-filter=null \
    --enable-filter=transpose \
    --enable-filter=trim \
    --enable-filter=vflip \
    \
    --disable-iconv

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
    uv sync --frozen --no-install-project --extra test

COPY archivepodcast archivepodcast

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
ADD tests tests
ADD uv.lock uv.lock
ADD pyproject.toml pyproject.toml

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
ENV AP_SIMPLE_LOGGING=1

CMD ["pytest"]
