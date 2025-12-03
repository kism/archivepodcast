"""Helpers for downloader module."""

import asyncio
import random


async def delay_download(attempt: int) -> None:
    """Sleep for an exponential backoff period based on the attempt number."""
    await asyncio.sleep(random.uniform(0.1, 1) + (0.5 * attempt))
