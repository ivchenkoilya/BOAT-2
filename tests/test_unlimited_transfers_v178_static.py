from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class UnlimitedTransfersV178Tests(unittest.TestCase):
    def test_daily_transfer_limit_is_disabled_for_both_handlers(self) -> None:
        source = read("unlimited_transfers_v178.py")
        self.assertIn("finance_transfer.TRANSFER_DAILY_LIMIT = UNLIMITED_SENTINEL", source)
        self.assertIn("finance.TRANSFER_DAILY_LIMIT = UNLIMITED_SENTINEL", source)

    def test_government_contribution_is_limited_only_by_balance(self) -> None:
        source = read("unlimited_transfers_v178.py")
        self.assertIn("contributions.MAX_CONTRIBUTION = UNLIMITED_SENTINEL", source)
        self.assertIn("Number(data.available_balance)", source)
        self.assertIn("if(!Number.isFinite(amount)||amount<100){", source)
        self.assertNotIn(
            'source.replace("if(!Number.isFinite(amount)||amount<100){"',
            source,
        )

    def test_layer_is_installed_after_reality177_safety(self) -> None:
        source = read("talent_entry_v164.py")
        safety = source.index("install_government_reality_v177_safety(core)")
        unlimited = source.index("install_unlimited_transfers_v178(core)")
        self.assertLess(safety, unlimited)


if __name__ == "__main__":
    unittest.main()
