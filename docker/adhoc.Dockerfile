# --- Minimal FFmpeg build stage ---
FROM alpine:3.22 AS ffmpeg-builder

# Basic build deps
RUN apk add --no-cache \
    build-base \
    yasm \
    git \
    wget \
    tar \
    pkgconfig \
    automake \
    autoconf \
    libtool

# Optional audio codec libs
# Remove what you don't need
RUN apk add --no-cache \
    libvorbis-dev \
    opus-dev \
    flac-dev \
    lame-dev \
    libogg-dev

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
    --enable-filter=format \
    --enable-filter=hflip \
    --enable-filter=null \
    --enable-filter=transpose \
    --enable-filter=trim \
    --enable-filter=vflip \
    \
    --disable-iconv

RUN make -j$(nproc) && make install


# --- Final application stage ---
FROM ghcr.io/astral-sh/uv:python3.14-alpine

COPY --from=ffmpeg-builder /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg

# Required for psutil
RUN apk add gcc python3-dev musl-dev linux-headers libxml2-dev libxslt-dev lame-libs libmagic

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-default-groups

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD archivepodcast archivepodcast

# We don't need this anymore
RUN rm -rf /usr/local/bin/uv*

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

ENV AP_SIMPLE_LOGGING=1

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

EXPOSE 5100

CMD [ "python" "-m", "archivepodcast" ]
