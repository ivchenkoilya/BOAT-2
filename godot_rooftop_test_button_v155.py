from __future__ import annotations

import logging
from pathlib import Path


LOGGER = logging.getLogger(__name__)
CENTER_PATH = Path(__file__).resolve().parent / "games" / "index.html"
BUTTON_MARKER = 'id="godotTestPlay"'
TEST_CARD = '''      <article class="game"><div><span class="icon">🧪</span><span class="badge">GODOT-ТЕСТ</span></div><h2>Бег по крышам 3D</h2><p>Исправленная Web-сборка Godot. Рабочая старая версия остаётся отдельно.</p><div class="chips"><span class="chip">Тест Telegram</span><span class="chip">Без начисления</span></div><button class="play" id="godotTestPlay">ЗАПУСТИТЬ GODOT-ТЕСТ</button></article>
'''
STANDARD_HANDLERS = "$('roofPlay').onclick=()=>go('rooftop');$('heistPlay').onclick=()=>go('heist');$('hunterPlay').onclick=()=>go('night-hunter');"
OLD_HANDLER = "$('godotTestPlay').onclick=()=>go('rooftop-godot-test');"
NEW_HANDLER = "$('godotTestPlay').onclick=()=>{location.href='/godot-rooftop-test/?'+params.toString()};"


def install_godot_test_button() -> None:
    """Add or repair the separate Godot test card in the games center."""
    if not CENTER_PATH.is_file():
        LOGGER.warning("Games center not found: %s", CENTER_PATH)
        return

    text = CENTER_PATH.read_text(encoding="utf-8")
    original = text

    if BUTTON_MARKER not in text:
        bunker_card = '      <article class="game bunker">'
        if bunker_card not in text:
            LOGGER.warning("Could not find bunker card insertion point")
            return
        text = text.replace(bunker_card, TEST_CARD + bunker_card, 1)

    # Repair pages patched by the previous version, including copies persisted
    # between deployments. The new top-level route does not depend on the old
    # game-folder allowlist and therefore cannot fall through to a 404 page.
    text = text.replace(OLD_HANDLER, NEW_HANDLER)
    if NEW_HANDLER not in text:
        if STANDARD_HANDLERS not in text:
            LOGGER.warning("Could not find games button handler insertion point")
            return
        text = text.replace(STANDARD_HANDLERS, STANDARD_HANDLERS + NEW_HANDLER, 1)

    if text != original:
        CENTER_PATH.write_text(text, encoding="utf-8")
        LOGGER.info("Godot rooftop test card and link installed")
