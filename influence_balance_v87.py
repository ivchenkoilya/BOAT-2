from __future__ import annotations

from typing import Any

import talent_system
import talent_ux


VERSION = "Reality 87 · Усиленное влияние"
INFLUENCE_COOLDOWN_SECONDS = 6 * 60 * 60
GENERAL_INFLUENCE_PER_LEVEL = 0.05
LEGACY_GENERAL_INFLUENCE_PER_LEVEL = 0.02


def install_influence_balance_v87(core: Any) -> None:
    """Ускоряет «Увеличить влияние» и усиливает общий талант влияния."""
    if getattr(core, "_influence_balance_v87_installed", False):
        return
    core._influence_balance_v87_installed = True
    core.BOT_VERSION = VERSION

    # Команда/кнопка «Увеличить влияние» теперь доступна раз в шесть часов.
    # Все обработчики берут значение из глобальной константы во время вызова.
    core.INFLUENCE_COOLDOWN_SECONDS = INFLUENCE_COOLDOWN_SECONDS

    # «Заметная личность» раньше давала 2% общего влияния за уровень.
    # Добавляем ещё 3 п.п., чтобы итог стал 5% за уровень (15% на максимуме).
    original_calculate_buffs = talent_system.calculate_buffs

    def calculate_buffs_v87(levels: dict[str, int]) -> dict[str, float]:
        buffs = original_calculate_buffs(levels)
        extra = max(0, int(levels.get("influence1", 0))) * (
            GENERAL_INFLUENCE_PER_LEVEL - LEGACY_GENERAL_INFLUENCE_PER_LEVEL
        )
        buffs["influence"] = float(buffs.get("influence", 0.0)) + extra
        return buffs

    talent_system.calculate_buffs = calculate_buffs_v87

    # Обновляем подписи в Mini App Древа без дублирования отдельной HTML-версии.
    talent_ux.SCRIPT = talent_ux.SCRIPT.replace(
        "'influence1','Заметная личность','crown',3,1,null,'+2% влияния','Общий прирост влияния.'",
        "'influence1','Заметная личность','crown',3,1,null,'+5% влияния','Общий прирост влияния.'",
    ).replace(
        "'influence1','Заметная личность','crown',3,1,'+2% влияния','Увеличивает положительные награды влияния.'",
        "'influence1','Заметная личность','crown',3,1,'+5% влияния','Увеличивает положительные награды влияния.'",
    ).replace(
        "Награда 100 → 102 за каждый уровень.",
        "Награда 100 → 105 за каждый уровень.",
    ).replace(
        "Если действие давало 100 очков, один уровень даст около 102.",
        "Если действие давало 100 очков, один уровень даст около 105.",
    )

    # В inline-меню описание раньше было захардкожено как «12 часов».
    original_inline_menu_specs = core.inline_menu_specs

    def inline_menu_specs_v87(user: Any) -> list[dict[str, Any]]:
        items = original_inline_menu_specs(user)
        for item in items:
            if str(item.get("action") or "") == "score:influence":
                item["description"] = (
                    "Случайные очки начислятся сразу · кулдаун 6 часов"
                )
        return items

    core.inline_menu_specs = inline_menu_specs_v87

    # Дополняем актуальную карточку «О боте» новым балансом.
    original_about = core.about_bot_text

    def about_bot_text_v87() -> str:
        text = original_about()
        addition = (
            "\n\n👑 <b>УВЕЛИЧИТЬ ВЛИЯНИЕ</b>\n"
            "• кулдаун уменьшен с 12 до 6 часов;\n"
            "• талант «Заметная личность» даёт +5% общего влияния за уровень;\n"
            "• максимальный бонус этого таланта — +15%."
        )
        return text + addition

    core.about_bot_text = about_bot_text_v87
