"""Per-language lexicons. Each module exposes PATTERNS, REASONS and IMITATED_BRANDS."""

from importlib import import_module
from types import ModuleType

SUPPORTED_LANGS = ("en",)


def load(lang: str) -> ModuleType:
    if lang not in SUPPORTED_LANGS:
        raise ValueError(f"Unsupported language {lang!r}; supported: {SUPPORTED_LANGS}")
    return import_module(f"{__name__}.{lang}")
