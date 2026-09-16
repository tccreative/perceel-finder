"""Optional: download listing photos as small compressed WebP thumbnails."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

from .core import Http

THUMB_W = 480
QUALITY = 62


def thumb_name(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16] + ".webp"


def fetch_thumbs(http: Http, items: list[dict], out_dir: Path, limit_per_listing: int = 1,
                 log=print) -> int:
    from PIL import Image

    out_dir.mkdir(parents=True, exist_ok=True)
    saved = 0
    for it in items:
        local = []
        for url in (it.get("images") or [])[:limit_per_listing]:
            name = thumb_name(url)
            dest = out_dir / name
            if dest.exists():
                local.append(f"thumbs/{name}")
                continue
            r = http.get(url, tries=2, timeout=30)
            if r is None:
                continue
            try:
                img = Image.open(io.BytesIO(r.content))
                img = img.convert("RGB")
                if img.width > THUMB_W:
                    img = img.resize((THUMB_W, round(img.height * THUMB_W / img.width)),
                                     Image.LANCZOS)
                img.save(dest, "WEBP", quality=QUALITY, method=6)
                saved += 1
                local.append(f"thumbs/{name}")
            except Exception as exc:  # noqa: BLE001
                log(f"    ! image {url[:60]} -> {exc}")
        if local:
            it["thumbs"] = local
    return saved
