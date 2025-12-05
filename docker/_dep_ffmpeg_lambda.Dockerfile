FROM public.ecr.aws/lambda/python:3.14 AS ffmpeg-builder

# Install build dependencies
RUN dnf install -y \
    gcc \
    gcc-c++ \
    make \
    yasm \
    nasm \
    wget \
    tar \
    gzip \
    pkg-config \
    autoconf \
    automake \
    libtool \
    && dnf clean all

WORKDIR /build

# Build LAME (libmp3lame) from source
RUN wget https://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz && \
    tar xzf lame-3.100.tar.gz && \
    cd lame-3.100 && \
    ./configure --prefix=/usr/local --enable-shared --disable-static && \
    make -j$(nproc) && \
    make install

# Download and build FFmpeg
RUN wget https://ffmpeg.org/releases/ffmpeg-7.1.tar.gz && \
    tar xzf ffmpeg-7.1.tar.gz

WORKDIR /build/ffmpeg-7.1

# Configure FFmpeg with minimal audio-only support
RUN PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./configure \
    --prefix=/usr/local \
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
