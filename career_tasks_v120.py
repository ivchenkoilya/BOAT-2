from __future__ import annotations

from typing import Any

import career_rewards_v120 as rewards
from career_model_v120 import deterministic_range, meta_get, now, table_exists


def install_career_tasks_v120(core: Any) -> None:
    if getattr(core, "_career_tasks_v120_installed", False):
        return
    core._career_tasks_v120_installed = True

    original_score_award = rewards.score_award

    def score_award_without_task_duplicate(row: Any):
        if str(row["reason"] or "").casefold() == "completed_action_task":
            return None
        return original_score_award(row)

    rewards.score_award = score_award_without_task_duplicate

    async def process_action_tasks(core_arg: Any) -> None:
        conn = core_arg.db._require_connection()
        if not await table_exists(conn, "action_tasks"):
            return
        started_at = await meta_get(core_arg, "career_started_at", now())
        cursor = await conn.execute(
            "SELECT task_id,chat_id,owner_id,task_key FROM action_tasks "
            "WHERE status='completed' AND created_at>=? ORDER BY created_at ASC LIMIT 2000",
            (int(started_at),),
        )
        for row in await cursor.fetchall():
            task_id = str(row["task_id"])
            task_key = str(row["task_key"] or "")
            if task_key.startswith("social:"):
                amount = deterministic_range(f"secret-task:{task_id}", 3_000, 5_000)
                reason = "Сложное или тайное задание"
                source_type = "secret_task"
            else:
                amount = 1_500
                reason = "Задание"
                source_type = "task"
            await rewards.award(
                core_arg,
                int(row["chat_id"]),
                int(row["owner_id"]),
                amount,
                source_type,
                task_id,
                reason,
            )

    original_process_all = rewards.process_all

    async def process_all_with_tasks(core_arg: Any) -> None:
        await original_process_all(core_arg)
        await process_action_tasks(core_arg)

    rewards.process_all = process_all_with_tasks
    core.process_career_tasks_v120 = lambda: process_action_tasks(core)
