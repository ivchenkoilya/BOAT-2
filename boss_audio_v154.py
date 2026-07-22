from __future__ import annotations

import base64
import hashlib
import logging
from pathlib import Path


LOGGER = logging.getLogger(__name__)
VERSION = "Boss audio v154 · full user track"
BASE_DIR = Path(__file__).resolve().parent
CHUNK_DIR = BASE_DIR / "webapp" / "assets" / "boss-theme-full-v154"
OUTPUT_PATH = BASE_DIR / "webapp" / "assets" / "main-hero-theme-full-v154.ogg"
EXPECTED_CHUNKS = 75
EXPECTED_SIZE = 832_904
EXPECTED_SHA256 = "c7501b92fe0f1544453558268c2db3ce57742337515a7e4d465c2f2b77c2f1ea"


def _is_valid_audio(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size != EXPECTED_SIZE:
        return False
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest == EXPECTED_SHA256


def install_boss_audio_v154() -> None:
    """Rebuild the full boss soundtrack from repository-safe text chunks.

    The generated OGG is served as one normal static file. The browser therefore
    downloads a single 3:08 track instead of dozens of fragments, while GitHub
    can keep the source losslessly as UTF-8 text.
    """
    if _is_valid_audio(OUTPUT_PATH):
        return

    try:
        paths = sorted(CHUNK_DIR.glob("*.b64"))
        if len(paths) != EXPECTED_CHUNKS:
            raise RuntimeError(
                f"Expected {EXPECTED_CHUNKS} audio chunks, found {len(paths)}"
            )

        encoded = "".join(path.read_text(encoding="ascii").strip() for path in paths)
        audio = base64.b64decode(encoded, validate=True)
        if len(audio) != EXPECTED_SIZE:
            raise RuntimeError(
                f"Unexpected soundtrack size: {len(audio)} instead of {EXPECTED_SIZE}"
            )

        digest = hashlib.sha256(audio).hexdigest()
        if digest != EXPECTED_SHA256:
            raise RuntimeError(f"Soundtrack checksum mismatch: {digest}")

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = OUTPUT_PATH.with_suffix(".ogg.tmp")
        temporary.write_bytes(audio)
        temporary.replace(OUTPUT_PATH)
        LOGGER.info("%s activated: %s", VERSION, OUTPUT_PATH)
    except Exception:
        # The raid remains available even if an incomplete deployment omitted an
        # audio chunk. The JavaScript will simply continue without background music.
        LOGGER.exception("Failed to assemble the full boss soundtrack")
