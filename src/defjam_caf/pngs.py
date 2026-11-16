"""Bounded verification metadata and immutable hot keys; no retained decoded images."""

import base64
from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import io
from threading import RLock

from PIL import Image
from .container import SaveError

MAX_ATLAS_BYTES = 16 * 1024**2
MAX_PORTRAIT_BYTES = 4 * 1024**2
MAX_ENTRIES = 256
MAX_HOT_BYTES = 64 * 1024**2
_cache = OrderedDict()
_hot = OrderedDict()
_hot_bytes = 0
_lock = RLock()


@dataclass(frozen=True)
class PNGInfo:
    size: int
    width: int
    height: int
    visible: bool
    digest: str


def _remember_hot(key, result):
    global _hot_bytes
    if key not in _hot:
        _hot_bytes += len(key[1])
    _hot[key] = result
    _hot.move_to_end(key)
    while _hot_bytes > MAX_HOT_BYTES or len(_hot) > MAX_ENTRIES:
        expired, _ = _hot.popitem(last=False)
        _hot_bytes -= len(expired[1])


def encoded_digest(value):
    try:
        return hashlib.sha256(value.encode("ascii")).hexdigest()
    except UnicodeError as exc:
        raise SaveError("Invalid PNG encoding.", detail=str(exc)) from exc


def inspect_png(value, kind):
    atlas = kind == "atlas"
    limit = MAX_ATLAS_BYTES if atlas else MAX_PORTRAIT_BYTES
    label = "Atlas" if atlas else "Portrait"
    if type(value) is not str or len(value) > 4 * ((limit + 2) // 3):
        raise SaveError(label + " PNG is too large")
    hot_key = (kind, value)
    with _lock:
        if hot_key in _hot:
            _hot.move_to_end(hot_key)
            return _hot[hot_key]
    digest = encoded_digest(value)
    key = (kind, digest)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            _remember_hot(hot_key, _cache[key])
            return _cache[key]
    try:
        raw = base64.b64decode(value, validate=True)
        if len(raw) > limit:
            raise SaveError(label + " PNG is too large")
        with Image.open(io.BytesIO(raw)) as image:
            width, height = image.size
            if atlas:
                if image.format != "PNG" or width != height or width not in (256, 512, 1024, 2048):
                    raise SaveError("Import a square 256, 512, 1024 or 2048 PNG atlas")
            elif image.format != "PNG" or not (32 <= width <= 2048 and 32 <= height <= 2048):
                raise SaveError("Portrait must be a 32–2048px PNG")
            image.verify()
        visible = True
        if not atlas:
            with Image.open(io.BytesIO(raw)) as image:
                visible = image.convert("RGBA").getchannel("A").getbbox() is not None
    except SaveError:
        raise
    except (ValueError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise SaveError("Invalid " + label.lower() + " PNG", detail=str(exc)) from exc
    result = PNGInfo(len(raw), width, height, visible, digest)
    with _lock:
        _cache[key] = result
        _cache.move_to_end(key)
        while len(_cache) > MAX_ENTRIES:
            _cache.popitem(last=False)
        _remember_hot(hot_key, result)
    return result


def clear_cache():
    global _hot_bytes
    with _lock:
        _cache.clear()
        _hot.clear()
        _hot_bytes = 0
