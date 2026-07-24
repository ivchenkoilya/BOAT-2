from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from government_reality_v179_common import BUILDINGS
from government_reality_v180_common import (
    BUILDING_DISTRICTS,
    DISTRICTS,
    PLOTS,
    SCHEMA_SQL,
)


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class Reality180MapTests(unittest.TestCase):
    def test_schema_contains_only_map_placement_data(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.executescript(SCHEMA_SQL)
        names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        self.assertIn("government_map_plots_v180", names)
        self.assertNotIn("treasury", SCHEMA_SQL.lower())
        self.assertNotIn("balance", SCHEMA_SQL.lower())
        self.assertIn("UNIQUE(project_id)", SCHEMA_SQL)
        self.assertIn("UNIQUE(building_id)", SCHEMA_SQL)

    def test_all_buildings_have_districts_and_thirty_unique_plots(self) -> None:
        self.assertEqual(set(BUILDINGS), set(BUILDING_DISTRICTS))
        self.assertEqual(len(DISTRICTS), 5)
        self.assertEqual(len(PLOTS), 30)
        self.assertEqual(len({item["plot_id"] for item in PLOTS}), 30)
        self.assertTrue(all(item["district"] in DISTRICTS for item in PLOTS))
        self.assertTrue(all(0 <= int(item["x"]) <= 100 and 0 <= int(item["y"]) <= 100 for item in PLOTS))

    def test_map_reads_canonical_reality179_objects(self) -> None:
        source = read("government_reality_v180_map.py")
        self.assertIn("government_construction_projects_v179", source)
        self.assertIn("government_buildings_v179", source)
        self.assertIn("government_construction_contributions_v179", source)
        self.assertIn("government_state_v127", source)
        self.assertIn("government_programs_v176", source)
        self.assertNotIn("UPDATE players SET", source)
        self.assertNotIn("treasury=treasury+", source)

    def test_existing_projects_and_buildings_are_auto_placed(self) -> None:
        source = read("government_reality_v180_map.py")
        self.assertIn("async def sync_map", source)
        self.assertIn("WHERE building_id=? OR (?<>'' AND project_id=?)", source)
        self.assertIn("status NOT IN ('cancelled')", source)
        self.assertIn("_available_plot", source)

    def test_map_ui_supports_pinch_and_has_no_polling_observer(self) -> None:
        source = read("governmentapp_v127/reality-v180-map.js")
        self.assertIn("data-screen=\"map180\"", source)
        self.assertIn("data-tab='map180'", source.replace('"', "'"))
        self.assertIn("pointerDistance", source)
        self.assertIn("pointers.size>=2", source)
        self.assertIn("centerCamera", source)
        self.assertIn("Масштаб — двумя пальцами", source)
        self.assertNotIn("MutationObserver", source)
        self.assertNotIn("setInterval", source)

    def test_map_shows_statuses_programs_and_existing_debt_action(self) -> None:
        source = read("governmentapp_v127/reality-v180-map.js")
        self.assertIn("active_programs", source)
        self.assertIn("underfunded", source)
        self.assertIn("data-r179-debt", source)
        self.assertIn("data-map-open-construction", source)

    def test_reality180_is_installed_after_reality179(self) -> None:
        source = read("talent_entry_v164.py")
        self.assertLess(
            source.index("install_government_reality_v179_safety(core)"),
            source.index("install_government_reality_v180(core)"),
        )


if __name__ == "__main__":
    unittest.main()
