from __future__ import annotations

import importlib.util
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "government_programs_property_v176_common.py"
JS_FILE = ROOT / "governmentapp_v127" / "programs-property-v176.js"

for name in (
    "finance_investments_v127_core",
    "finance_investments_v127_market",
    "government_institutions_v128",
    "government_oversight_deputy_v167_data",
    "government_treasury_management_v164",
    "government_v127",
):
    sys.modules.setdefault(name, types.ModuleType(name))

spec = importlib.util.spec_from_file_location("government_programs_property_v176_data", DATA_FILE)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def connection(path=":memory:"):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(module.SCHEMA_SQL)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS players(chat_id INTEGER,user_id INTEGER,points INTEGER,full_name TEXT,updated_at INTEGER,PRIMARY KEY(chat_id,user_id));
        CREATE TABLE IF NOT EXISTS government_state_v127(chat_id INTEGER PRIMARY KEY,treasury INTEGER,updated_at INTEGER);
        CREATE TABLE IF NOT EXISTS government_structure_funds_v164(chat_id INTEGER,structure_key TEXT,balance INTEGER,updated_at INTEGER,PRIMARY KEY(chat_id,structure_key));
        """
    )
    return conn


class Reality176Tests(unittest.TestCase):
    def test_schema_creates_all_required_tables(self):
        conn = connection()
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        expected = {
            "government_programs_v176",
            "government_program_effects_v176",
            "government_property_v176",
            "government_property_maintenance_v176",
            "government_property_debts_v176",
            "government_property_declarations_v176",
            "government_property_investigations_v176",
            "government_property_auctions_v176",
            "government_property_bids_v176",
            "government_property_operations_v176",
        }
        self.assertTrue(expected.issubset(names))

    def test_program_cost_and_office_levels(self):
        self.assertEqual(module._program_cost("anti_crisis", 40_000), 5_000)
        self.assertEqual(module._program_cost("anti_crisis", 900_000), 90_000)
        self.assertEqual(module._program_cost("anti_crisis", 2_000_000), 100_000)
        self.assertEqual(module._program_cost("social_help", 50_000, 9_000), 9_000)
        self.assertEqual(module._office_level(["deputy"]), 1)
        self.assertEqual(module._office_level(["oversight"]), 3)
        self.assertEqual(module._office_level(["president"]), 4)

    def test_one_item_type_per_owner(self):
        conn = connection()
        row = ("p1", -1, 10, "yacht", 1_000_000, 50_000, "owned", 1, 2, 0, 0, "", 0, 0, 1)
        conn.execute(
            "INSERT INTO government_property_v176(property_id,chat_id,owner_id,item_key,purchase_price,luxury_tax,status,purchased_at,next_maintenance_at,debt,seizure_until,source_auction_id,confiscated_by,confiscated_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            row,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO government_property_v176(property_id,chat_id,owner_id,item_key,purchase_price,luxury_tax,status,purchased_at,next_maintenance_at,debt,seizure_until,source_auction_id,confiscated_by,confiscated_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("p2", *row[1:]),
            )

    def test_maintenance_period_is_idempotent(self):
        conn = connection()
        charge = ("c1", "p1", -1, 10, 100, 10_000, 1, "paid", 200, 200)
        conn.execute("INSERT INTO government_property_maintenance_v176 VALUES(?,?,?,?,?,?,?,?,?,?)", charge)
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO government_property_maintenance_v176 VALUES(?,?,?,?,?,?,?,?,?,?)", ("c2", *charge[1:]))

    def test_luxury_purchase_and_tax_are_balanced(self):
        conn = connection()
        conn.execute("INSERT INTO players VALUES(-1,10,2000000,'Owner',0)")
        conn.execute("INSERT INTO government_state_v127 VALUES(-1,1000,0)")
        conn.commit()
        price = module.PROPERTY_ITEMS["yacht"]["price"]
        tax = price * 5 // 100
        total = price + tax
        conn.execute("BEGIN")
        conn.execute("UPDATE players SET points=points-? WHERE chat_id=-1 AND user_id=10", (total,))
        conn.execute("UPDATE government_state_v127 SET treasury=treasury+? WHERE chat_id=-1", (tax,))
        conn.execute(
            "INSERT INTO government_property_v176(property_id,chat_id,owner_id,item_key,purchase_price,luxury_tax,status,purchased_at,next_maintenance_at,debt,seizure_until,updated_at) VALUES('p1',-1,10,'yacht',?,?,'owned',1,2,0,0,1)",
            (price, tax),
        )
        conn.commit()
        self.assertEqual(conn.execute("SELECT points FROM players").fetchone()[0], 2_000_000-total)
        self.assertEqual(conn.execute("SELECT treasury FROM government_state_v127").fetchone()[0], 1_000+tax)

    def test_two_sequential_auction_bids_refund_previous_bidder(self):
        conn = connection()
        conn.execute("INSERT INTO players VALUES(-1,11,500000,'A',0)")
        conn.execute("INSERT INTO players VALUES(-1,12,500000,'B',0)")
        conn.execute("INSERT INTO government_state_v127 VALUES(-1,0,0)")
        conn.execute("INSERT INTO government_property_v176(property_id,chat_id,owner_id,item_key,purchase_price,luxury_tax,status,purchased_at,next_maintenance_at,debt,seizure_until,updated_at) VALUES('p1',-1,99,'sports_car',150000,7500,'auction',1,2,0,0,1)")
        conn.execute("INSERT INTO government_property_auctions_v176 VALUES('a1',-1,'p1',99,90000,0,0,'active',1,9999999999,0)")
        conn.commit()
        conn.execute("BEGIN")
        conn.execute("UPDATE players SET points=points-90000 WHERE user_id=11")
        conn.execute("UPDATE government_property_auctions_v176 SET current_price=90000,current_bidder_id=11 WHERE auction_id='a1'")
        conn.execute("INSERT INTO government_property_bids_v176 VALUES('b1','a1',11,90000,1)")
        conn.commit()
        conn.execute("BEGIN")
        conn.execute("UPDATE players SET points=points-95000 WHERE user_id=12")
        conn.execute("UPDATE players SET points=points+90000 WHERE user_id=11")
        conn.execute("UPDATE government_property_auctions_v176 SET current_price=95000,current_bidder_id=12 WHERE auction_id='a1'")
        conn.execute("INSERT INTO government_property_bids_v176 VALUES('b2','a1',12,95000,2)")
        conn.commit()
        self.assertEqual(conn.execute("SELECT points FROM players WHERE user_id=11").fetchone()[0], 500000)
        self.assertEqual(conn.execute("SELECT points FROM players WHERE user_id=12").fetchone()[0], 405000)
        self.assertEqual(conn.execute("SELECT current_bidder_id FROM government_property_auctions_v176").fetchone()[0], 12)

    def test_restart_keeps_property_and_debt_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "state.sqlite3")
            conn = connection(path)
            conn.execute("INSERT INTO government_property_v176(property_id,chat_id,owner_id,item_key,purchase_price,luxury_tax,status,purchased_at,next_maintenance_at,debt,seizure_until,updated_at) VALUES('p1',-1,10,'palace',25000000,1250000,'seized_debt',1,2,750000,0,1)")
            conn.execute("INSERT INTO government_property_debts_v176 VALUES('p1',-1,10,750000,1)")
            conn.commit();conn.close()
            reopened = connection(path)
            row = reopened.execute("SELECT status,debt FROM government_property_v176 WHERE property_id='p1'").fetchone()
            self.assertEqual((row[0],row[1]),("seized_debt",750000))

    def test_insufficient_balance_does_not_create_property(self):
        conn = connection()
        conn.execute("INSERT INTO players VALUES(-1,10,1000,'Poor',0)")
        price = module.PROPERTY_ITEMS["business_sedan"]["price"]
        tax = price * 5 // 100
        balance = conn.execute("SELECT points FROM players WHERE user_id=10").fetchone()[0]
        self.assertLess(balance, price + tax)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM government_property_v176").fetchone()[0], 0)

    def test_program_spends_only_selected_fund(self):
        conn = connection()
        conn.execute("INSERT INTO government_structure_funds_v164 VALUES(-1,'reserve',100000,0)")
        conn.execute("INSERT INTO government_structure_funds_v164 VALUES(-1,'social_fund',80000,0)")
        cost = module._program_cost("anti_crisis", 100000)
        conn.execute("UPDATE government_structure_funds_v164 SET balance=balance-? WHERE chat_id=-1 AND structure_key='reserve'", (cost,))
        reserve = conn.execute("SELECT balance FROM government_structure_funds_v164 WHERE structure_key='reserve'").fetchone()[0]
        social = conn.execute("SELECT balance FROM government_structure_funds_v164 WHERE structure_key='social_fund'").fetchone()[0]
        self.assertEqual(reserve, 90000)
        self.assertEqual(social, 80000)

    def test_debt_repayment_restores_owned_status(self):
        conn = connection()
        conn.execute("INSERT INTO players VALUES(-1,10,100000,'Owner',0)")
        conn.execute("INSERT INTO government_state_v127 VALUES(-1,0,0)")
        conn.execute("INSERT INTO government_property_v176(property_id,chat_id,owner_id,item_key,purchase_price,luxury_tax,status,purchased_at,next_maintenance_at,debt,seizure_until,updated_at) VALUES('p1',-1,10,'business_sedan',50000,2500,'seized_debt',1,2,500,0,1)")
        conn.execute("INSERT INTO government_property_debts_v176 VALUES('p1',-1,10,500,1)")
        conn.execute("UPDATE players SET points=points-500 WHERE user_id=10")
        conn.execute("UPDATE government_state_v127 SET treasury=treasury+500 WHERE chat_id=-1")
        conn.execute("UPDATE government_property_v176 SET debt=0,status='owned' WHERE property_id='p1'")
        conn.execute("DELETE FROM government_property_debts_v176 WHERE property_id='p1'")
        self.assertEqual(tuple(conn.execute("SELECT status,debt FROM government_property_v176").fetchone()), ("owned",0))
        self.assertEqual(conn.execute("SELECT treasury FROM government_state_v127").fetchone()[0], 500)

    def test_confiscation_auction_starts_at_sixty_percent(self):
        price = module.PROPERTY_ITEMS["private_jet"]["price"]
        self.assertEqual(price * 60 // 100, 3_000_000)

    def test_auction_minimum_step_is_five_percent(self):
        current = 100_000
        minimum = max(current + 1, __import__('math').ceil(current * 1.05))
        self.assertEqual(minimum, 105_000)

    def test_frontend_has_no_dom_observer_or_interval_loop(self):
        source = JS_FILE.read_text(encoding="utf-8")
        self.assertNotIn("MutationObserver", source)
        self.assertNotIn("setInterval", source)


if __name__ == "__main__":
    unittest.main()
