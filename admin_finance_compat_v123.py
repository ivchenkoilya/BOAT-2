from __future__ import annotations

from typing import Any


def install_admin_finance_compat_v123(core: Any) -> None:
    if getattr(core, "_admin_finance_compat_v123_installed", False):
        return
    core._admin_finance_compat_v123_installed = True

    original_connect = core.Database.connect

    async def connect_with_admin_finance_compat(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        cursor = await conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='finance_loans_v112' LIMIT 1"
        )
        if await cursor.fetchone() is None:
            return
        async with self.lock:
            cursor = await conn.execute("PRAGMA table_info(finance_loans_v112)")
            columns = {str(row["name"]) for row in await cursor.fetchall()}
            if "remaining_due" not in columns:
                await conn.execute(
                    "ALTER TABLE finance_loans_v112 ADD COLUMN remaining_due INTEGER NOT NULL DEFAULT 0"
                )
            await conn.execute(
                "UPDATE finance_loans_v112 SET remaining_due=MAX(0,total_due-repaid)"
            )
            await conn.executescript(
                """
                CREATE TRIGGER IF NOT EXISTS finance_remaining_insert_v123
                AFTER INSERT ON finance_loans_v112
                BEGIN
                    UPDATE finance_loans_v112
                    SET remaining_due=MAX(0,NEW.total_due-NEW.repaid)
                    WHERE loan_id=NEW.loan_id;
                END;

                CREATE TRIGGER IF NOT EXISTS finance_remaining_update_v123
                AFTER UPDATE OF total_due,repaid,status ON finance_loans_v112
                BEGIN
                    UPDATE finance_loans_v112
                    SET remaining_due=MAX(0,NEW.total_due-NEW.repaid)
                    WHERE loan_id=NEW.loan_id;
                END;
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_admin_finance_compat
