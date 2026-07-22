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


def install_boss_audio_v154() -> None:
    """Assemble the verified user-track loop into one browser-friendly OGG.

    Previous code fetched and decoded fragments in the Telegram WebView. Building
    one static asset at server start removes playback gaps, repeated downloads and
    fragile Blob URLs. The audio element then loops continuously for the whole raid.
    """
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
