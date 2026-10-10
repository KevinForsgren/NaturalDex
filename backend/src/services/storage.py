#!/usr/bin/env python3
"""
Private local storage for submitted discovery photos.

Photos are written under a backend-relative upload directory (never into SQL and
never into a public web path). ``storage_key`` stored on ``discovery_photos`` is
the path relative to the upload root, so photo bytes can be gathered for the
vision provider without trusting a client-supplied URL.
"""

import hashlib
import uuid
from pathlib import Path

from config.settings import get_settings

# <backend dir> (this file: backend/src/services/storage.py -> parents[2]).
BACKEND_DIR = Path(__file__).resolve().parents[2]

_ALLOWED_CONTENT_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/heic": ".heic"}


def upload_root() -> Path:
    """Return the resolved private upload directory, creating it if needed."""
    settings = get_settings()
    raw = settings.UPLOAD_DIR
    if raw.startswith("./") or raw.startswith(".\\"):
        rel = raw[2:]
        root = BACKEND_DIR / rel
    else:
        root = Path(raw)
    root.mkdir(parents=True, exist_ok=True)
    return root


def content_type_allowed(content_type: str) -> bool:
    return content_type in _ALLOWED_CONTENT_TYPES


def extension_for(content_type: str) -> str:
    return _ALLOWED_CONTENT_TYPES.get(content_type, ".img")


def save_photo_bytes(data: bytes, content_type: str) -> str:
    """Persist photo bytes under the private upload root and return a storage_key."""
    root = upload_root()
    digest = hashlib.sha256(data).hexdigest()[:24]
    uid = uuid.uuid4().hex[:12]
    key = f"discovery/{uid}-{digest}{extension_for(content_type)}"
    target = root / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return key


def read_photo_bytes(storage_key: str) -> bytes:
    """Read photo bytes for a storage_key. Raises FileNotFoundError when absent."""
    root = upload_root()
    path = root / storage_key
    # ensure the key stays inside the upload root
    if not path.resolve().is_relative_to(root.resolve()):
        raise FileNotFoundError(storage_key)
    return path.read_bytes()


def remove_photo(storage_key: str) -> None:
    """Delete a stored photo by storage_key (best effort)."""
    root = upload_root()
    path = root / storage_key
    try:
        if path.resolve().is_relative_to(root.resolve()):
            path.unlink(missing_ok=True)
    except OSError:
        pass