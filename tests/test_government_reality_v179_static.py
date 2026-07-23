from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from government_reality_v179_common import BUILDINGS, SCHEMA_SQL, clamp_trust


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class Reality179StaticTests(unittest.TestCase):
    def test_schema_creates_all_construction_and_trust_tables(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.executescript(SCHEMA_SQL)
        names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        expected = {
            "government_contribution_requests_v179",
            "government_construction_projects_v179",
            "government_construction_funding_v179",
            "government_construction_contributions_v179",
            "government_buildings_v179",
            "government_building_effects_v179",
            "government_building_income_v179",
            "government_building_maintenance_v179",
            "government_building_debts_v179",
            "government_construction_scores_v179",
            "government_construction_log_v179",
            "government_trust_events_v179",
            "government_trust_state_v179",
        }
        self.assertTrue(expected.issubset(names))

    def test_catalog_contains_ten_real_buildings(self) -> None:
        self.assertEqual(len(BUILDINGS), 10)
        self.assertEqual(BUILDINGS["factory"]["cost"], 1_000_000)
        self.assertEqual(BUILDINGS["school"]["cost"], 600_000)
        self.assertEqual(BUILDINGS["power_plant"]["cost"], 2_000_000)
        self.assertEqual(BUILDINGS["science"]["duration"], 48 * 3600)
        self.assertTrue(all(item["maintenance_bp"] > 0 for item in BUILDINGS.values()))

    def test_construction_runtime_imports_source_titles(self) -> None:
        runtime = read("government_reality_v179_construction_runtime.py")
        import_line = next(
            line for line in runtime.splitlines()
            if line.startswith("from government_reality_v179_common import")
        )
        self.assertIn("SOURCE_TITLES", import_line)
        self.assertIn('"title": SOURCE_TITLES[source]', runtime)

    def test_idempotency_constraints_exist(self) -> None:
        self.assertIn("request_id TEXT PRIMARY KEY", SCHEMA_SQL)
        self.assertIn("request_id TEXT NOT NULL UNIQUE", SCHEMA_SQL)
        self.assertIn("PRIMARY KEY(building_id,period_at)", SCHEMA_SQL)
        self.assertIn("event_key TEXT PRIMARY KEY", SCHEMA_SQL)
        self.assertIn("project_id TEXT NOT NULL UNIQUE", SCHEMA_SQL)

    def test_general_treasury_is_not_a_structure_mapping(self) -> None:
        source = read("government_reality_v179_treasury.py")
        self.assertIn('"state_treasury"', source)
        self.assertIn("treasury=treasury+?", source)
        self.assertIn('if fund_key == "state_treasury"', source)
        self.assertNotIn('"state_treasury": "finance_ministry"', source)

    def test_finance_ministry_and_state_treasury_are_separate(self) -> None:
        source = read("government_reality_v179_treasury.py")
        self.assertIn('"general": "finance_ministry"', source)
        self.assertIn('"title": "Общая казна"', source)
        self.assertIn('"title": "Министерство финансов"', source)

    def test_contributions_have_no_fixed_one_million_cap(self) -> None:
        treasury = read("government_reality_v179_treasury.py")
        safety = read("government_reality_v179_safety.py")
        self.assertIn("MAX_SQLITE_INTEGER", treasury)
        self.assertIn("points>=?", treasury)
        self.assertIn("Недостаточно влияния. Твой баланс", treasury)
        self.assertIn("Number(data.available_balance)", safety)
        self.assertNotIn("Размер вклада должен быть от 100 до 1 000 000", treasury)

    def test_treasury_contribution_uses_request_id(self) -> None:
        treasury = read("government_reality_v179_treasury.py")
        safety = read("government_reality_v179_safety.py")
        self.assertIn("government_contribution_requests_v179 WHERE request_id=?", treasury)
        self.assertIn("request_id:contributionRequestId()", safety)
        self.assertIn("crypto?.randomUUID", safety)
        self.assertIn("source.replace", safety)
        self.assertIn("window.addEventListener('pageshow',scheduleEnsure)", safety)

    def test_construction_funding_is_bound_to_project(self) -> None:
        source = read("government_reality_v179_construction_actions.py")
        self.assertIn("project_id,chat_id,user_id,amount,score,request_id", source)
        self.assertIn("funded_amount=funded_amount+?", source)
        self.assertIn("_start_if_ready_locked", source)
        self.assertIn("points=points-?", source)

    def test_projects_start_and_complete_once(self) -> None:
        core = read("government_reality_v179_construction_core.py")
        runtime = read("government_reality_v179_construction_runtime.py")
        self.assertIn("WHERE project_id=? AND status='awaiting_funding' AND funded_amount>=total_cost", core)
        self.assertIn("WHERE project_id=? AND status='building'", runtime)
        self.assertIn("project_id TEXT NOT NULL UNIQUE", SCHEMA_SQL)

    def test_income_and_maintenance_are_period_idempotent(self) -> None:
        runtime = read("government_reality_v179_construction_runtime.py")
        self.assertIn("INSERT OR IGNORE INTO government_building_income_v179", runtime)
        self.assertIn("government_building_maintenance_v179 WHERE building_id=? AND period_at=?", runtime)
        self.assertIn("underfunded", runtime)
        self.assertIn("active=0", runtime)

    def test_trust_is_canonical_and_bounded(self) -> None:
        source = read("government_reality_v179_trust.py")
        self.assertEqual(clamp_trust(-20), 0)
        self.assertEqual(clamp_trust(55), 55)
        self.assertEqual(clamp_trust(120), 100)
        self.assertIn("UPDATE government_offices_v127 SET trust=?", source)
        self.assertIn("government_official_rating_log_v177", source)
        self.assertIn("government_trust_events_v179 WHERE event_key=?", source)

    def test_overall_trust_weights_are_present(self) -> None:
        source = read("government_reality_v179_trust.py")
        for fragment in ('(30, ("president",))', '(10, ("chair",))', '(15, ("deputy",))', '(15, ("finance",))'):
            self.assertIn(fragment, source)
        self.assertIn("available_weight", source)
        self.assertIn("last_recalc_at", source)

    def test_mobile_ui_has_separate_construction_tab(self) -> None:
        source = read("governmentapp_v127/reality-v179.js")
        self.assertIn("construction179", source)
        self.assertIn("Строительство", source)
        self.assertIn("ВЛОЖИТЬСЯ В СТРОИТЕЛЬСТВО", source)
        self.assertNotIn("MutationObserver", source)
        self.assertNotIn("setInterval", source)

    def test_reality179_is_installed_after_reality178(self) -> None:
        source = read("talent_entry_v164.py")
        reality178 = source.index("install_unlimited_transfers_v178(core)")
        reality179 = source.index("install_government_reality_v179(core)")
        safety179 = source.index("install_government_reality_v179_safety(core)")
        self.assertLess(reality178, reality179)
        self.assertLess(reality179, safety179)


if __name__ == "__main__":
    unittest.main()
