# Use AWS Lambda Python 3.14 base image
FROM public.ecr.aws/lambda/python:3.14

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
