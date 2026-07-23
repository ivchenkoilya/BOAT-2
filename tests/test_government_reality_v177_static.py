from __future__ import annotations

import ast
import re
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def assigned_string(source: str, name: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    value = ast.literal_eval(node.value)
                    if isinstance(value, str):
                        return value
    raise AssertionError(f"String assignment {name} not found")


class Reality177StaticTests(unittest.TestCase):
    def test_schema_creates_all_reality177_tables(self) -> None:
        source = read("government_reality_v177_common.py")
        schema = assigned_string(source, "SCHEMA_SQL")
        connection = sqlite3.connect(":memory:")
        connection.executescript(schema)
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%v177'"
            )
        }
        expected = {
            "government_fund_migrations_v177",
            "government_program_requests_v177",
            "government_program_publications_v177",
            "government_program_effects_v177",
            "government_official_rating_votes_v177",
            "government_official_rating_log_v177",
            "government_official_terms_v177",
            "government_property_meta_v177",
            "government_voluntary_auctions_v177",
            "government_voluntary_bids_v177",
            "government_property_action_requests_v177",
        }
        self.assertTrue(expected.issubset(names))

    def test_old_program_minimum_prices_are_four_times_higher(self) -> None:
        source = read("government_reality_v177_common.py")
        expected = {
            "anti_crisis": 20_000,
            "festival": 40_000,
            "social_help": 12_000,
            "oversight_operation": 12_000,
            "market_intervention": 20_000,
            "election_campaign": 20_000,
        }
        for key, value in expected.items():
            block = re.search(rf'"{key}"\s*:\s*\{{(?P<body>.*?)\n\s*\}},', source, re.S)
            self.assertIsNotNone(block, key)
            digits = f"{value:_}".replace("_", r"[_ ]?")
            self.assertRegex(block.group("body"), rf'"min_cost"\s*:\s*{digits}')
        self.assertIn('"cost_mode": "reserve_10pct_x4"', source)
        self.assertIn("return base * 4", source)

    def test_all_new_programs_have_server_definitions(self) -> None:
        source = read("government_reality_v177_common.py")
        for key in (
            "infrastructure",
            "education_grants",
            "emergency_social",
            "cyber_defense",
            "anti_corruption_audit",
            "economy_support",
            "information_campaign",
            "emergency_mode",
            "science_project",
            "housing_subsidy",
        ):
            self.assertIn(f'"{key}": {{', source)

    def test_program_idempotency_and_chat_outbox_exist(self) -> None:
        source = read("government_reality_v177_programs.py")
        self.assertIn("government_program_requests_v177", source)
        self.assertIn("government_program_publications_v177", source)
        self.assertIn("_publish_once", source)
        self.assertIn("ГОСУДАРСТВЕННАЯ ПРОГРАММА ЗАПУЩЕНА", source)
        self.assertLess(
            source.index("await conn.commit()", source.index("government_program_publications_v177")),
            source.rindex("await _publish_once"),
        )

    def test_fund_migration_is_marked_and_old_balance_is_zeroed(self) -> None:
        source = read("government_reality_v177_funds.py")
        self.assertIn("government_fund_migrations_v177", source)
        self.assertIn("UPDATE government_fund_balances_v150 SET amount=0", source)
        self.assertIn("government_structure_funds_v164", source)
        self.assertIn(
            "PRIMARY KEY(chat_id,legacy_key)",
            read("government_reality_v177_common.py"),
        )

    def test_rating_uses_canonical_trust_and_guards_public_vote(self) -> None:
        source = read("government_reality_v177_ratings.py")
        self.assertIn("max(0, min(100", source)
        self.assertIn("Нельзя оценивать собственную работу", source)
        self.assertIn("RATING_VOTE_COOLDOWN", source)
        self.assertIn("UPDATE government_offices_v127 SET trust", source)

    def test_property_economy_formulas_and_guards(self) -> None:
        actions = read("government_reality_v177_property_actions.py")
        auctions = read("government_reality_v177_property_auctions.py")
        self.assertIn("* 70 // 100", actions)
        self.assertIn("* 20 // 100", actions)
        self.assertIn("* 5 // 100", actions)
        self.assertIn("Имущество участвует в открытом расследовании", actions)
        self.assertIn("price * 5 // 100", auctions)
        self.assertIn("seller_payout = price - commission", auctions)
        self.assertIn("current_bidder_id", auctions)

    def test_extended_api_exposes_all_property_actions(self) -> None:
        source = read("government_reality_v177_api.py")
        for action in (
            "property_buy",
            "property_sell",
            "property_auction_start",
            "property_auction_bid",
            "property_upgrade",
            "property_insure",
            "property_primary",
            "property_debt_pay",
            "property_investigation_open",
            "property_investigation_action",
            "official_rate",
            "program_start",
        ):
            self.assertIn(f'action == "{action}"', source)

    def test_webview_script_has_separate_sections_without_unbounded_observers(self) -> None:
        source = read("governmentapp_v127/reality-v177.js")
        self.assertIn('data-screen="ratings177"', source)
        self.assertIn('data-screen="property177"', source)
        self.assertIn("/government-v177/api/extended-action", source)
        self.assertIn("ПРОДАТЬ ИМУЩЕСТВО", source)
        self.assertNotIn("MutationObserver", source)
        self.assertNotIn("setInterval", source)

    def test_entrypoint_installs_reality177_after_reality176(self) -> None:
        source = read("talent_entry_v164.py")
        old = source.index("install_government_programs_property_v176(core)")
        new = source.index("install_government_reality_v177(core)")
        api = source.index("install_government_reality_v177_api(core)")
        self.assertLess(old, new)
        self.assertLess(new, api)


if __name__ == "__main__":
    unittest.main()
