FROM debian:bookworm-slim

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    yasm \
    nasm \
    wget \
    tar \
    gzip \
    pkg-config \
    automake \
    autoconf \
    libtool \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Build LAME (libmp3lame) statically from source
RUN wget https://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz && \
    tar xzf lame-3.100.tar.gz && \
    cd lame-3.100 && \
    ./configure --prefix=/build/static --enable-static --disable-shared --disable-frontend && \
    make -j$(nproc) && \
    make install

# Download ffmpeg source code
RUN wget https://ffmpeg.org/releases/ffmpeg-7.1.tar.gz && \
    tar xzf ffmpeg-7.1.tar.gz && \
    mv ffmpeg-7.1 ffmpeg

WORKDIR /build/ffmpeg

# Configure static FFmpeg with minimal audio-only support
RUN PKG_CONFIG_PATH=/build/static/lib/pkgconfig \
    ./configure \
    --prefix=/build/static \
    --disable-shared \
    --enable-static \
    --pkg-config-flags="--static" \
    --extra-cflags="-I/build/static/include" \
    --extra-ldflags="-L/build/static/lib" \
    --extra-libs="-lpthread -lm" \
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

RUN make -j$(nproc)
