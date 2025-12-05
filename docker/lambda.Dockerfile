# --- Minimal FFmpeg build stage ---
# Use the same base as Lambda to ensure GLIBC compatibility
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

# --- Lambda runtime stage ---
# Use AWS Lambda Python 3.14 base image
FROM public.ecr.aws/lambda/python:3.14

# Copy FFmpeg binaries from builder
COPY --from=ffmpeg-builder /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg

# Copy required shared libraries from builder to /usr/lib64 (standard Lambda location)
COPY --from=ffmpeg-builder /usr/local/lib/libmp3lame.so* /usr/lib64/
COPY --from=ffmpeg-builder /usr/local/lib/libavcodec.so* /usr/lib64/
COPY --from=ffmpeg-builder /usr/local/lib/libavformat.so* /usr/lib64/
COPY --from=ffmpeg-builder /usr/local/lib/libavutil.so* /usr/lib64/
COPY --from=ffmpeg-builder /usr/local/lib/libswresample.so* /usr/lib64/
COPY --from=ffmpeg-builder /usr/local/lib/libavfilter.so* /usr/lib64/

# Update library cache (using full path for Lambda base image)
RUN /sbin/ldconfig

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

# Set the Lambda handler
# This expects a lambda_handler.py file with a handler() function
# Or you can modify to point to your actual handler
CMD ["archivepodcast.lambda_handler.handler"]
