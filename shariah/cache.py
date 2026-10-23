"""Tiny disk cache: every network/LLM result is saved to data_cache/ so the demo
can run offline from the committed cache if the venue wifi dies."""
import json
import pathlib
import re

CACHE_DIR = pathlib.Path(__file__).resolve().parent.parent / "data_cache"


def _path(key: str) -> pathlib.Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", key)
    return CACHE_DIR / f"{safe}.json"


def cached(key: str, produce, refresh: bool = False):
    """Return the cached value for `key`, or call produce() and cache it."""
    p = _path(key)
    if p.exists() and not refresh:
        return json.loads(p.read_text(encoding="utf-8"))
    value = produce()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=1, default=str), encoding="utf-8")
    return value


def has(key: str) -> bool:
    return _path(key).exists()
