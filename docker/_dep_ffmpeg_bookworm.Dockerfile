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
