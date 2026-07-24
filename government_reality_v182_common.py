from __future__ import annotations

from typing import Any

VERSION = "Reality 182 · Карта государства 3.0"
LAYOUT_VERSION = 182

MOBILE_WORLD = {"width": 720, "height": 1120}
WIDE_WORLD = {"width": 1200, "height": 760}

MOBILE_DISTRICTS: dict[str, dict[str, Any]] = {
    "government": {"x": 38, "y": 34, "width": 644, "height": 275, "emoji": "🏛", "title": "Правительственный центр", "accent": "gold"},
    "culture": {"x": 38, "y": 334, "width": 306, "height": 385, "emoji": "🔬", "title": "Научно-культурный район", "accent": "violet"},
    "security": {"x": 372, "y": 334, "width": 310, "height": 385, "emoji": "🚓", "title": "Район безопасности", "accent": "red"},
    "industrial": {"x": 38, "y": 744, "width": 306, "height": 338, "emoji": "🏭", "title": "Промышленный район", "accent": "orange"},
    "social": {"x": 372, "y": 744, "width": 310, "height": 338, "emoji": "🏥", "title": "Социальный район", "accent": "green"},
}

WIDE_DISTRICTS: dict[str, dict[str, Any]] = {
    "culture": {"x": 25, "y": 28, "width": 270, "height": 335, "emoji": "🔬", "title": "Научно-культурный район", "accent": "violet"},
    "government": {"x": 315, "y": 24, "width": 550, "height": 350, "emoji": "🏛", "title": "Правительственный центр", "accent": "gold"},
    "industrial": {"x": 25, "y": 395, "width": 395, "height": 335, "emoji": "🏭", "title": "Промышленный район", "accent": "orange"},
    "social": {"x": 440, "y": 395, "width": 420, "height": 335, "emoji": "🏥", "title": "Социальный район", "accent": "green"},
    "security": {"x": 885, "y": 170, "width": 285, "height": 560, "emoji": "🚓", "title": "Район безопасности", "accent": "red"},
}

MOBILE_PLOTS: dict[str, tuple[int, int]] = {
    "gov-1": (125, 125), "gov-2": (590, 125),
    "gov-3": (120, 242), "gov-4": (590, 242),
    "gov-5": (270, 258), "gov-6": (450, 258),
    "cul-1": (105, 445), "cul-2": (270, 445),
    "cul-3": (105, 565), "cul-4": (270, 565),
    "cul-5": (105, 675), "cul-6": (270, 675),
    "sec-1": (455, 452), "sec-2": (590, 565), "sec-3": (455, 675),
    "ind-1": (105, 835), "ind-2": (270, 835),
    "ind-3": (105, 945), "ind-4": (270, 945),
    "ind-5": (105, 1040), "ind-6": (270, 1040),
    "soc-1": (435, 825), "soc-2": (530, 825), "soc-3": (625, 825),
    "soc-4": (435, 925), "soc-5": (530, 925), "soc-6": (625, 925),
    "soc-7": (435, 1025), "soc-8": (530, 1025), "soc-9": (625, 1025),
}

WIDE_PLOTS: dict[str, tuple[int, int]] = {
    "cul-1": (85, 112), "cul-2": (210, 105), "cul-3": (82, 225), "cul-4": (213, 220), "cul-5": (92, 322), "cul-6": (222, 315),
    "gov-1": (365, 105), "gov-2": (815, 105), "gov-3": (365, 285), "gov-4": (815, 285), "gov-5": (500, 323), "gov-6": (682, 323),
    "ind-1": (90, 475), "ind-2": (255, 475), "ind-3": (90, 600), "ind-4": (255, 600), "ind-5": (170, 700), "ind-6": (350, 685),
    "soc-1": (495, 465), "soc-2": (635, 465), "soc-3": (785, 465), "soc-4": (495, 575), "soc-5": (635, 575), "soc-6": (785, 575), "soc-7": (495, 690), "soc-8": (635, 690), "soc-9": (785, 690),
    "sec-1": (955, 350), "sec-2": (1080, 510), "sec-3": (955, 670),
}

MOBILE_LANDMARKS: dict[str, tuple[int, int]] = {
    "presidency": (360, 92), "finance": (220, 185), "duma": (500, 185), "court": (360, 220), "oversight": (530, 405),
}

WIDE_LANDMARKS: dict[str, tuple[int, int]] = {
    "presidency": (590, 82), "finance": (455, 190), "duma": (720, 185), "court": (590, 235), "oversight": (1040, 245),
}

MOBILE_ROADS = (
    "M 360 18 L 360 1102",
    "M 20 321 C 190 315, 510 315, 700 321",
    "M 20 730 C 220 725, 500 725, 700 730",
    "M 350 320 C 280 390, 250 520, 345 720",
    "M 370 320 C 445 405, 475 535, 375 720",
    "M 43 866 C 145 820, 245 820, 335 865",
    "M 385 867 C 475 820, 585 820, 674 870",
)

WIDE_ROADS = (
    "M 18 382 C 260 370, 440 390, 875 385 C 1020 382, 1110 350, 1180 310",
    "M 305 18 C 310 150, 305 260, 315 740",
    "M 870 25 C 866 205, 875 445, 872 742",
    "M 30 382 C 175 270, 245 230, 318 192",
    "M 862 382 C 955 410, 1040 475, 1165 555",
    "M 423 390 C 445 500, 438 620, 425 740",
)


def layout_payload() -> dict[str, Any]:
    return {
        "mobile": {
            "world": dict(MOBILE_WORLD),
            "districts": {key: dict(value) for key, value in MOBILE_DISTRICTS.items()},
            "plots": {key: {"x": xy[0], "y": xy[1]} for key, xy in MOBILE_PLOTS.items()},
            "landmarks": {key: {"x": xy[0], "y": xy[1]} for key, xy in MOBILE_LANDMARKS.items()},
            "roads": list(MOBILE_ROADS),
        },
        "wide": {
            "world": dict(WIDE_WORLD),
            "districts": {key: dict(value) for key, value in WIDE_DISTRICTS.items()},
            "plots": {key: {"x": xy[0], "y": xy[1]} for key, xy in WIDE_PLOTS.items()},
            "landmarks": {key: {"x": xy[0], "y": xy[1]} for key, xy in WIDE_LANDMARKS.items()},
            "roads": list(WIDE_ROADS),
        },
    }
