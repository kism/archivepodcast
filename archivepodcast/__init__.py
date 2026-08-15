"""FastAPI web application for archiving and serving podcasts."""

from typing import TYPE_CHECKING

from .run_adhoc import run_ap_adhoc

if TYPE_CHECKING:
    from .run_webapp import create_app

__all__ = ["create_app", "run_ap_adhoc"]


def __getattr__(name: str) -> object:
    # ponytail: create_app needs fastapi, which adhoc/lambda mode shouldn't require importing
    if name == "create_app":
        from .run_webapp import create_app  # ruff: ignore[import-outside-top-level]

        return create_app
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
