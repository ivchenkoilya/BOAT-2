from __future__ import annotations

import base64
import logging
from pathlib import Path


LOGGER = logging.getLogger(__name__)
VERSION = "Boss audio v154 · stable user-track loop"
BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "webapp" / "assets"
OUTPUT_PATH = ASSET_DIR / "main-hero-theme-full-v154.ogg"
EXPECTED_CHUNKS = 5
FULL_TRACK_MIN_SIZE = 150_000


def _has_full_uploaded_track() -> bool:
    if not OUTPUT_PATH.is_file() or OUTPUT_PATH.stat().st_size < FULL_TRACK_MIN_SIZE:
        return False
    try:
        return OUTPUT_PATH.read_bytes()[:4] == b"OggS"
    except OSError:
        return False


def install_boss_audio_v154() -> None:
    """Provide one stable browser-friendly OGG for the boss raid.

    A manually uploaded full-quality track has priority and is never overwritten.
    Until it is present, the verified user-track fragment is assembled into one
    static OGG and loops continuously for the whole raid.
    """
    if _has_full_uploaded_track():
        LOGGER.info("%s: full uploaded soundtrack detected", VERSION)
        return

    try:
        paths = sorted(ASSET_DIR.glob("boss-theme-loop-*.b64"))
        if len(paths) != EXPECTED_CHUNKS:
            raise RuntimeError(
                f"Expected {EXPECTED_CHUNKS} soundtrack chunks, found {len(paths)}"
            )

        encoded = "".join(path.read_text(encoding="ascii").strip() for path in paths)
        audio = base64.b64decode(encoded, validate=True)
        if len(audio) < 40_000 or not audio.startswith(b"OggS"):
            raise RuntimeError("The assembled soundtrack is not a valid OGG stream")

        if OUTPUT_PATH.is_file() and OUTPUT_PATH.read_bytes() == audio:
            return

        temporary = OUTPUT_PATH.with_suffix(".ogg.tmp")
        temporary.write_bytes(audio)
        temporary.replace(OUTPUT_PATH)
        LOGGER.info("%s activated: %s", VERSION, OUTPUT_PATH)
    except Exception:
        # The raid stays playable even after an incomplete deployment. JavaScript
        # simply continues without music if the generated asset is unavailable.
        LOGGER.exception("Failed to assemble the stable boss soundtrack")
