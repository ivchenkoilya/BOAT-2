from __future__ import annotations

from typing import Any


EXTRA_TODAY_TYPES: list[dict[str, str]] = [
    {
        "key": "sly",
        "emoji": "😈",
        "title": "Подлый",
        "description": (
            "Хитрый, скользкий и расчётливый. Улыбается в лицо, а потом "
            "выбирает самый удобный момент, чтобы подставить, уколоть или "
            "присвоить чужой успех. Почти никогда не действует напрямую — "
            "предпочитает чужими руками."
        ),
    },
    {
        "key": "raven",
        "emoji": "🐦‍⬛",
        "title": "Вороний",
        "description": (
            "Умный, мрачный, наблюдательный и немного зловещий. Замечает то, "
            "что остальные пропускают, собирает чужие секреты и появляется "
            "именно тогда, когда становится интересно. Никто не понимает, "
            "он просто смотрит или уже что-то задумал."
        ),
    },
]


def install_today_types(core: Any) -> None:
    """Добавляет новые типажи в раздел «Кто ты сегодня?» без дублей."""
    existing_keys = {
        str(item.get("key", ""))
        for item in getattr(core, "TODAY_TYPES", [])
        if isinstance(item, dict)
    }
    for item in EXTRA_TODAY_TYPES:
        if item["key"] not in existing_keys:
            core.TODAY_TYPES.append(dict(item))
            existing_keys.add(item["key"])
