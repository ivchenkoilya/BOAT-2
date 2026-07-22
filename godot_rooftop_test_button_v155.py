from __future__ import annotations

import logging
from pathlib import Path


LOGGER = logging.getLogger(__name__)
CENTER_PATH = Path(__file__).resolve().parent / "games" / "index.html"
BUTTON_MARKER = 'id="godotTestPlay"'
TEST_CARD = '''      <article class="game"><div><span class="icon">🧪</span><span class="badge">GODOT-ТЕСТ</span></div><h2>Бег по крышам 3D</h2><p>Исправленная Web-сборка Godot. Рабочая старая версия остаётся отдельно.</p><div class="chips"><span class="chip">Тест Telegram</span><span class="chip">Без начисления</span></div><button class="play" id="godotTestPlay">ЗАПУСТИТЬ GODOT-ТЕСТ</button></article>
'''


def install_godot_test_button() -> None:
    """Add a temporary test card without replacing the stable rooftop game."""
    if not CENTER_PATH.is_file():
        LOGGER.warning("Games center not found: %s", CENTER_PATH)
        return

    text = CENTER_PATH.read_text(encoding="utf-8")
    if BUTTON_MARKER in text:
        return

    bunker_card = '      <article class="game bunker">'
    if bunker_card not in text:
        LOGGER.warning("Could not find bunker card insertion point")
        return
    text = text.replace(bunker_card, TEST_CARD + bunker_card, 1)

    handler_line = "$('roofPlay').onclick=()=>go('rooftop');$('heistPlay').onclick=()=>go('heist');$('hunterPlay').onclick=()=>go('night-hunter');"
    replacement = handler_line + "$('godotTestPlay').onclick=()=>go('rooftop-godot-test');"
    if handler_line not in text:
        LOGGER.warning("Could not find games button handler insertion point")
        return
    text = text.replace(handler_line, replacement, 1)
    CENTER_PATH.write_text(text, encoding="utf-8")
    LOGGER.info("Godot rooftop test button added to games center")
