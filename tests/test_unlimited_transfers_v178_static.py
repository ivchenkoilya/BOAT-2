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
        self.assertIn('method == "POST" and path == "/government-v150/api/contribute"', source)
        self.assertIn("UPDATE players SET points=points-?,updated_at=?", source)
        self.assertIn("WHERE chat_id=? AND user_id=? AND points>=?", source)
        self.assertIn("fund_bridge.credit_fund_locked", source)
        self.assertIn("Недостаточно влияния. Твой баланс", source)
        self.assertNotIn(
            'source.replace("if(!Number.isFinite(amount)||amount<100){"',
            source,
        )

    def test_unlimited_contribution_is_atomic_and_uses_canonical_fund(self) -> None:
        source = read("unlimited_transfers_v178.py")
        lock_at = source.index("async with core.db.lock")
        debit_at = source.index("UPDATE players SET points=points-?")
        credit_at = source.index("fund_bridge.credit_fund_locked")
        commit_at = source.index("await conn.commit()", credit_at)
        rollback_at = source.index("await conn.rollback()", commit_at)
        self.assertLess(lock_at, debit_at)
        self.assertLess(debit_at, credit_at)
        self.assertLess(credit_at, commit_at)
        self.assertLess(commit_at, rollback_at)
        self.assertIn("await fund_bridge.migrate_funds(core)", source)
        self.assertIn("voluntary_contribution_v178", source)

    def test_layer_is_installed_after_reality177_safety(self) -> None:
        source = read("talent_entry_v164.py")
        safety = source.index("install_government_reality_v177_safety(core)")
        unlimited = source.index("install_unlimited_transfers_v178(core)")
        self.assertLess(safety, unlimited)


if __name__ == "__main__":
    unittest.main()
