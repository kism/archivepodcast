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
    libmp3lame-dev \
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
    \
    # Enable audio encoders
    --enable-encoder=pcm_s16le \
    --enable-encoder=libmp3lame \
    \
    # Enable audio decoders
    --enable-decoder=pcm_s16le \
    --enable-decoder=mp3 \
    \
    # Enable audio muxers
    --enable-muxer=wav \
    --enable-muxer=mp3 \
    \
    # External libs
    --enable-libmp3lame \
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

# --- Lambda runtime stage ---
# Use AWS Lambda Python 3.14 base image
FROM public.ecr.aws/lambda/python:3.14

# Copy FFmpeg binaries from builder
COPY --from=ffmpeg-builder /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg-builder /usr/local/bin/ffprobe /usr/local/bin/ffprobe

# Copy FFmpeg shared libraries from builder
COPY --from=ffmpeg-builder /usr/lib/x86_64-linux-gnu/libmp3lame*.so* /usr/lib64/

# Install system dependencies required for building Python packages
RUN dnf install -y \
    gcc \
    gcc-c++ \
    make \
    libxml2-devel \
    libxslt-devel \
    file-libs \
    && dnf clean all

# Install UV for faster package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy application code
COPY archivepodcast ${LAMBDA_TASK_ROOT}/archivepodcast

# Set environment variables
ENV AP_SIMPLE_LOGGING=1
ENV PYTHONUNBUFFERED=1
ENV AP_SELF_TEST=1

# Set the Lambda handler
# This expects a lambda_handler.py file with a handler() function
# Or you can modify to point to your actual handler
CMD ["archivepodcast.lambda_handler.handler"]
