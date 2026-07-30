from __future__ import annotations

"""Runtime loader for the Reality 184 server layer.

The implementation is split into text-safe Base85 fragments so it can be
transported through the repository contents API without truncation. The
payload is verified before execution; a missing or changed fragment prevents
startup instead of silently loading an incomplete economy layer.
"""

import base64
import hashlib
import zlib
from pathlib import Path


_PARTS_DIR = Path(__file__).resolve().parent / "hero_v184_payload"
_EXPECTED_PARTS = 8
_EXPECTED_PAYLOAD_SHA256 = "fab8a267aaee700e6a91d4c6467c5a7dea367d9c0de1f391f31466aa924ad2d1"
_EXPECTED_SOURCE_SHA256 = "e6c6c6a1e9437115748246a722b9d0a700a4d59e67d12e2a5a6a24c188662a90"


def _load_source() -> str:
    parts = sorted(_PARTS_DIR.glob("part_*.b85"))
    if len(parts) != _EXPECTED_PARTS:
        raise RuntimeError(
            f"Reality 184: expected {_EXPECTED_PARTS} payload parts, found {len(parts)}"
        )
    payload = "".join(path.read_text(encoding="ascii") for path in parts)
    payload_hash = hashlib.sha256(payload.encode("ascii")).hexdigest()
    if payload_hash != _EXPECTED_PAYLOAD_SHA256:
        raise RuntimeError("Reality 184: server payload checksum mismatch")
    try:
        source_bytes = zlib.decompress(base64.b85decode(payload.encode("ascii")))
    except Exception as error:
        raise RuntimeError("Reality 184: server payload cannot be decoded") from error
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if source_hash != _EXPECTED_SOURCE_SHA256:
        raise RuntimeError("Reality 184: decoded source checksum mismatch")
    return source_bytes.decode("utf-8")


_SOURCE_NAME = str(Path(__file__).with_name("hero_expansion_v184_source.py"))
exec(compile(_load_source(), _SOURCE_NAME, "exec"), globals(), globals())
