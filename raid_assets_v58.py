from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any


def install_raid_assets(core: Any) -> None:
    """Извлекает изображение защиты из старого data URI в настоящий WebP-файл.

    Статический маршрут Mini App уже раздаёт WEBAPP_DIR/assets, поэтому отдельный
    файл надёжнее огромного CSS background и корректно кэшируется как изображение.
    """
    if getattr(core, "_raid_assets_v58_installed", False):
        return
    core._raid_assets_v58_installed = True

    source = Path(core.WEBAPP_DIR) / "action-card-defense-v21.css"
    target = Path(core.WEBAPP_DIR) / "assets" / "action_defense_v58.webp"
    try:
        css = source.read_text(encoding="utf-8")
        match = re.search(r"data:image/webp;base64,([A-Za-z0-9+/=]+)", css)
        if match is None:
            raise RuntimeError("В CSS не найдено изображение защиты")
        payload = base64.b64decode(match.group(1), validate=True)
        if not payload.startswith(b"RIFF") or b"WEBP" not in payload[:16]:
            raise RuntimeError("Извлечённый файл защиты не является WebP")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    except Exception:
        core.logging.exception("Не удалось подготовить изображение защиты рейда")
