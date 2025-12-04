"""Module for serverless helpers."""

import os


def is_running_serverless() -> bool:
    """Check if the application is running in a serverless environment."""
    return os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
