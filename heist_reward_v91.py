from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from aiohttp import web

import game_center_v75 as base


_FINISH_LOCK_V91 = asyncio.Lock()


def install_heist_reward_v91(core: Any) -> None:
    """Начисляет за ограбление всю сохранённую добычу, а не разницу с рекордом."""
    if getattr(core, "_heist_reward_v91_installed", False):
        return
    core._heist_reward_v91_installed = True

    async def payload(request: web.Request) -> dict[str, Any]:
        try:
            value = await request.json()
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    def parse_chat_id(
        start_param: str | None,
        data: dict[str, Any],
        request: web.Request,
    ) -> int | None:
        raw = str(start_param or "")
        if raw.startswith(base.GAME_PREFIX):
            raw = raw[len(base.GAME_PREFIX):]
        else:
            raw = str(data.get("chat_id") or request.query.get("chat_id") or "")
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    async def auth(request: web.Request) -> tuple[Any, int, dict[str, Any]]:
        user, start_param = core._webapp_auth(request)
        if user is None:
            raise PermissionError(start_param or "Нет авторизации Telegram.")
        data = await payload(request)
        chat_id = parse_chat_id(start_param, data, request)
        if chat_id is None:
            raise ValueError("Не найдена беседа для начисления влияния.")
        if await core.db.get_player(chat_id, user.id) is None:
            raise PermissionError("Сначала открой игру из меню бота в нужной беседе.")
        return user, chat_id, data

    def error_response(error: Exception) -> web.Response:
        status = 403 if isinstance(error, PermissionError) else 400
        return core.web.json_response({"ok": False, "reason": str(error)}, status=status)

    async def finish_api_v91(request: web.Request) -> web.Response:
        session_id = ""
        reward_applied = False
        try:
            user, chat_id, data = await auth(request)
            session_id = str(data.get("session_id") or "")
            if not session_id:
                raise ValueError("Потеряна игровая сессия.")

            reported_score = base._int(data.get("score"), 0, 0, 1_000_000)
            stats = data.get("stats") if isinstance(data.get("stats"), dict) else {}
            now = int(time.time())
            conn = core.db._require_connection()

            async with _FINISH_LOCK_V91:
                async with core.db.lock:
                    cursor = await conn.execute(
                        "SELECT * FROM game_runs_v75 WHERE session_id = ? LIMIT 1",
                        (session_id,),
                    )
                    run = await cursor.fetchone()
                    if run is None:
                        raise ValueError("Игровая сессия не найдена.")
                    if int(run["chat_id"]) != chat_id or int(run["user_id"]) != user.id:
                        raise PermissionError("Эта игровая сессия принадлежит другому игроку.")

                    if str(run["status"]) == "finished":
                        player = await core.db.get_player(chat_id, user.id)
                        base_reward = int(run["base_reward"])
                        actual_reward = int(run["actual_reward"])
                        return core.web.json_response(
                            {
                                "ok": True,
                                "already_finished": True,
                                "score": int(run["score"]),
                                "base_run_reward": base_reward,
                                "payable_base": base_reward,
                                "tree_bonus": max(0, actual_reward - base_reward),
                                "actual_reward": actual_reward,
                                "balance": int(player.points) if player else 0,
                                "reward_rule": "full_saved_loot",
                                "message": "Этот результат уже был сохранён и повторно не начисляется.",
                            }
                        )
                    if str(run["status"]) != "active":
                        raise ValueError("Эта игровая сессия уже закрыта.")

                    elapsed = now - int(run["started_at"])
                    if elapsed < 8:
                        raise ValueError("Забег завершён слишком быстро и не засчитан.")
                    if elapsed > 300:
                        raise ValueError("Игровая сессия устарела.")

                    game_key = str(run["game_key"])
                    if game_key not in base.GAME_INFO:
                        raise ValueError("Повреждён тип игры.")

                    cursor = await conn.execute(
                        """
                        SELECT best_score, best_base_reward
                        FROM game_daily_v75
                        WHERE chat_id = ? AND user_id = ? AND game_key = ? AND date_key = ?
                        """,
                        (chat_id, user.id, game_key, base._date_key()),
                    )
                    daily = await cursor.fetchone()
                    previous_score = int(daily["best_score"]) if daily else 0
                    previous_reward = int(daily["best_base_reward"]) if daily else 0

                    if game_key == "heist":
                        secured = base._int(stats.get("secured"), reported_score, 0, 1_500)
                        opened = base._int(stats.get("opened"), 0, 0, 20)
                        total_safes = base._int(stats.get("total_safes"), 15, 1, 20)
                        # Верхняя граница защищает сервер от подмены клиента, но не
                        # режет честную добычу: даже легендарный сейф с джекпотом и
                        # мастерским бонусом укладывается в 220 влияния на сейф.
                        plausible_limit = min(1_500, max(50, min(opened, total_safes) * 220 + 40))
                        score = min(reported_score, secured, plausible_limit)
                        run_reward = score
                        payable = run_reward
                    else:
                        limit = min(300, elapsed * 8 + 40)
                        score = min(reported_score, limit, 300)
                        run_reward = base._base_reward(game_key, score)
                        payable = max(0, run_reward - previous_reward)

                    await conn.execute(
                        "UPDATE game_runs_v75 SET status = 'resolving' WHERE session_id = ?",
                        (session_id,),
                    )
                    await conn.commit()

                actual = 0
                tree_bonus = 0
                player = await core.db.get_player(chat_id, user.id)
                if payable > 0:
                    before, player = await core.db.add_points_with_balance(
                        chat_id,
                        user.id,
                        payable,
                        f"game_influence_hunt_{game_key}",
                    )
                    actual = int(player.points) - int(before)
                    tree_bonus = max(0, actual - payable)
                    reward_applied = True

                async with core.db.lock:
                    await conn.execute(
                        """
                        UPDATE game_daily_v75
                        SET best_score = MAX(best_score, ?),
                            best_base_reward = MAX(best_base_reward, ?),
                            total_paid = total_paid + ?, updated_at = ?
                        WHERE chat_id = ? AND user_id = ? AND game_key = ? AND date_key = ?
                        """,
                        (
                            score,
                            run_reward,
                            actual,
                            now,
                            chat_id,
                            user.id,
                            game_key,
                            base._date_key(),
                        ),
                    )
                    await conn.execute(
                        """
                        UPDATE game_runs_v75
                        SET status = 'finished', finished_at = ?, score = ?,
                            base_reward = ?, actual_reward = ?, meta_json = ?
                        WHERE session_id = ?
                        """,
                        (
                            now,
                            score,
                            payable,
                            actual,
                            json.dumps(stats, ensure_ascii=False)[:4000],
                            session_id,
                        ),
                    )
                    await conn.commit()

                if player is None:
                    player = await core.db.get_player(chat_id, user.id)
                full_heist = game_key == "heist"
                return core.web.json_response(
                    {
                        "ok": True,
                        "game": game_key,
                        "score": score,
                        "previous_best_score": previous_score,
                        "base_run_reward": run_reward,
                        "previous_best_reward": previous_reward,
                        "payable_base": payable,
                        "tree_bonus": tree_bonus,
                        "actual_reward": actual,
                        "balance": int(player.points) if player else 0,
                        "new_best": score > previous_score,
                        "reward_rule": "full_saved_loot" if full_heist else "daily_best_difference",
                        "message": (
                            "Вся сохранённая добыча начислена в баланс."
                            if full_heist
                            else (
                                "Новый лучший результат и влияние начислены."
                                if payable > 0
                                else "Награда дня не улучшилась, поэтому влияние повторно не начислено."
                            )
                        ),
                    }
                )
        except (PermissionError, ValueError) as error:
            return error_response(error)
        except Exception:
            if session_id and not reward_applied:
                try:
                    conn = core.db._require_connection()
                    async with core.db.lock:
                        await conn.execute(
                            """
                            UPDATE game_runs_v75
                            SET status = 'active'
                            WHERE session_id = ? AND status = 'resolving'
                            """,
                            (session_id,),
                        )
                        await conn.commit()
                except Exception:
                    pass
            return core.web.json_response(
                {"ok": False, "reason": "Не удалось сохранить результат. Попробуй ещё раз."},
                status=500,
            )

    class HeistRewardRouter(web.UrlDispatcher):
        def add_post(self, path: str, handler: Any, **kwargs: Any):
            if path == "/games/api/finish":
                handler = finish_api_v91
            return super().add_post(path, handler, **kwargs)

    original_start_server = core.start_webapp_server

    async def start_server_with_heist_reward(bot: Any):
        previous_application = core.web.Application

        def application_factory(*args: Any, **kwargs: Any):
            kwargs.setdefault("router", HeistRewardRouter())
            return previous_application(*args, **kwargs)

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_with_heist_reward
