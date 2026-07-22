from __future__ import annotations

import base64
import logging
from pathlib import Path


LOGGER = logging.getLogger(__name__)
VERSION = "Boss audio v154 · stable user-track loop"
BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "webapp" / "assets"
OUTPUT_PATH = ASSET_DIR / "main-hero-theme-full-v154.ogg"
UPLOADED_MP3_PATH = ASSET_DIR / "boss_music.mp3"
EXPECTED_CHUNKS = 5
FULL_TRACK_MIN_SIZE = 150_000


def _has_uploaded_mp3() -> bool:
    """Detect the user-uploaded raid track and skip the obsolete OGG builder."""
    if not UPLOADED_MP3_PATH.is_file() or UPLOADED_MP3_PATH.stat().st_size < 1_024:
        return False
    try:
        header = UPLOADED_MP3_PATH.read_bytes()[:12]
    except OSError:
        return False

    # Normal MP3 files start either with an ID3 tag or an MPEG frame sync.
    return header.startswith(b"ID3") or (
        len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0
    )


def _has_full_uploaded_track() -> bool:
    if not OUTPUT_PATH.is_file() or OUTPUT_PATH.stat().st_size < FULL_TRACK_MIN_SIZE:
        return False
    try:
        return OUTPUT_PATH.read_bytes()[:4] == b"OggS"
    except OSError:
        return False


def install_boss_audio_v154() -> None:
    """Provide one stable browser-friendly soundtrack for the boss raid.

    The new manually uploaded MP3 has priority. The legacy OGG chunk builder is
    retained only as a fallback for older deployments where boss_music.mp3 is
    absent.
    """
    if _has_uploaded_mp3():
        LOGGER.info(
            "%s: uploaded boss_music.mp3 detected; legacy OGG assembly skipped",
            VERSION,
        )
        return

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
