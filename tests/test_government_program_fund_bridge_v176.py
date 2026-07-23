from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_FILE = ROOT / "government_programs_property_v176_funds.py"

for name in (
    "government_treasury_contributions_v150",
    "government_treasury_management_v164",
    "government_v127",
    "government_programs_property_v176_programs",
    "government_programs_property_v176_state",
):
    sys.modules.setdefault(name, types.ModuleType(name))

sys.modules["government_programs_property_v176_programs"]._program_cost = lambda *args, **kwargs: 0
sys.modules["government_programs_property_v176_programs"].run_program = lambda *args, **kwargs: None
sys.modules["government_programs_property_v176_programs"].apply_anti_crisis = lambda *args, **kwargs: None
sys.modules["government_programs_property_v176_programs"].process_expired_effects = lambda *args, **kwargs: None
sys.modules["government_programs_property_v176_programs"].expanded_oversight_report = lambda *args, **kwargs: None

common = types.ModuleType("government_programs_property_v176_common")
common.PROGRAMS = {
    "anti_crisis": {"fund_key": "reserve"},
    "festival": {"fund_key": "event_fund"},
    "social_help": {"fund_key": "social_fund"},
    "oversight_operation": {"fund_key": "oversight"},
    "market_intervention": {"fund_key": "finance_ministry"},
    "election_campaign": {"fund_key": "election_commission"},
}
common._program_cost = lambda *args, **kwargs: 0
common.ensure_schema = lambda *args, **kwargs: None
sys.modules["government_programs_property_v176_common"] = common

spec = importlib.util.spec_from_file_location("government_programs_property_v176_funds", MODULE_FILE)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class ProgramFundBridgeTests(unittest.TestCase):
    def test_every_program_maps_to_visible_reality150_fund(self):
        self.assertEqual(
            module.LEGACY_FUND_BY_PROGRAM,
            {
                "anti_crisis": "reserve",
                "festival": "development",
                "social_help": "social",
                "oversight_operation": "security",
                "market_intervention": "general",
                "election_campaign": "elections",
            },
        )

    def test_available_balance_combines_both_fund_systems(self):
        self.assertEqual(module._available_balance(20_000, 100_000, 30_000), 50_000)
        self.assertEqual(module._available_balance(0, 100_000, 200_000), 100_000)

    def test_required_transfer_moves_only_missing_amount(self):
        self.assertEqual(module._required_transfer(40_000, 20_000, 100_000, 30_000), 20_000)
        self.assertEqual(module._required_transfer(10_000, 20_000, 100_000, 30_000), 0)

    def test_required_transfer_rejects_unbacked_balance(self):
        with self.assertRaises(ValueError):
            module._required_transfer(60_000, 20_000, 100_000, 30_000)


if __name__ == "__main__":
    unittest.main()
