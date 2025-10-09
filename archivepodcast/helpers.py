"""Helper utilities for archivepodcast."""

from typing import TYPE_CHECKING

from colorama import Back, Fore, Style
import random
from lxml import etree

from .logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client  # pragma: no cover
else:
    S3Client = object


fg_colours = [
    Fore.BLACK,
    Fore.RED,
    Fore.GREEN,
    Fore.YELLOW,
    Fore.BLUE,
    Fore.MAGENTA,
    Fore.CYAN,
    Fore.WHITE,
]
bg_colours = [
    Back.BLACK,
    Back.RED,
    Back.GREEN,
    Back.YELLOW,
    Back.BLUE,
    Back.MAGENTA,
    Back.CYAN,
    Back.WHITE,
]


def list_all_s3_objects(s3_client: S3Client, bucket: str) -> list:
    """List all objects in an S3 bucket using pagination.

    Args:
        s3_client: Boto3 S3 client instance
        bucket: Name of the S3 bucket

    Returns:
        List of all objects in the bucket
    """
    paginator = s3_client.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=bucket)

    all_objects: list = []
    for page in page_iterator:
        if "Contents" in page:
            all_objects.extend(page["Contents"])

    return all_objects


def tree_no_episodes(tree: etree._ElementTree | None) -> bool:
    """Check if the XML tree has no episodes."""
    if tree is None:
        return True
    return len(tree.xpath("//item")) == 0


def colour_id() -> str:
    """Fun coloured player names."""
    player_id = random.randbytes(6).hex()

    new_player_id = ""
    split_player_id = [""]

    # Split the player id string into chunks of 3
    for idx, i in enumerate(player_id):
        split_player_id[len(split_player_id) - 1] = split_player_id[len(split_player_id) - 1] + i
        if (idx + 1) % 3 == 0:
            split_player_id.append("")

    # Colour each chunk based on the sum of its characters
    # Uses modulus of the length of the colour array
    # So each string chunk will be coloured the same way
    for i in split_player_id:
        fun_number = sum(bytearray(i, "ascii"))
        fg_pick = fg_colours[(fun_number + fun_number) % len(fg_colours)]
        bg_pick = bg_colours[(fun_number) % len(bg_colours)]

        if fg_colours.index(fg_pick) == bg_colours.index(bg_pick):
            bg_pick = bg_colours[bg_colours.index(bg_pick) + 1]

        new_player_id = new_player_id + (Style.BRIGHT + fg_pick + bg_pick + i + Style.RESET_ALL)

    return new_player_id
