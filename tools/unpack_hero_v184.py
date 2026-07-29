from __future__ import annotations

"""Decode the reviewable Reality 184 source from its repository payload."""

import base64
import hashlib
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS_DIR = ROOT / "hero_v184_payload"
OUTPUT = ROOT / "hero_expansion_v184_source.py"
PAYLOAD_SHA256 = "fab8a267aaee700e6a91d4c6467c5a7dea367d9c0de1f391f31466aa924ad2d1"
SOURCE_SHA256 = "e6c6c6a1e9437115748246a722b9d0a700a4d59e67d12e2a5a6a24c188662a90"

parts = sorted(PARTS_DIR.glob("part_*.b85"))
if len(parts) != 8:
    raise SystemExit(f"Expected 8 payload fragments, found {len(parts)}")
payload = "".join(path.read_text(encoding="ascii") for path in parts).encode("ascii")
if hashlib.sha256(payload).hexdigest() != PAYLOAD_SHA256:
    raise SystemExit("Payload checksum mismatch")
source = zlib.decompress(base64.b85decode(payload))
if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
    raise SystemExit("Decoded source checksum mismatch")
OUTPUT.write_bytes(source)
print(f"Written {OUTPUT} ({len(source)} bytes)")
