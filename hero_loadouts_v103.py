from __future__ import annotations

import html
import random
import time
from typing import Any

HEROES = {
    1: dict(name="Каблучий", title="Узник обручального кольца", description="Подчиняется жене и появляется у друзей только после разрешения.", ability="Разрешение получено", hint="Защищает себя и весь отряд на 20 секунд", cooldown=600),
    2: dict(name="Сливариус", title="Призрак общей сходки", description="Обещает прийти, но растворяется в дыму или ищет крестик на карте.", ability="Я уже выхожу", hint="Исчезает на 5 секунд и возвращается с усиленным критом", cooldown=480),
    3: dict(name="Солёний", title="Кузнец реальности", description="Создатель игры, заводской творец и генератор безумных механик.", ability="Переписать реальность", hint="Сокращает кулдауны, лечит отряд и усиливает урон", cooldown=720),
    4: dict(name="Сейфзоний", title="Безопасная зона", description="Скрытный аналитик, рядом с которым девушки чувствуют безопасность.", ability="Безопасная зона", hint="Даёт отряду щит, лечение и снижение урона", cooldown=600),
    5: dict(name="Самозваний", title="Ложный главный герой", description="Амбициозный спорщик, который требует внимания и ревнует к Сейфзонию.", ability="Я здесь главный", hint="Усиливает урон и заставляет босса обратить внимание", cooldown=540),
    6: dict(name="Скользий", title="Малый дипломат", description="Прыгучий и скользкий переговорщик, который умеет вывернуться.", ability="Дипломатический манёвр", hint="Задерживает босса, ускоряет кулдауны и даёт уклонение", cooldown=480),
    7: dict(name="Былогерий", title="Наследник былой славы", description="Бывший главный герой, который ещё способен вернуться в сюжет.", ability="Возвращение в сюжет", hint="Один раз за бой возрождается или входит в режим величия", cooldown=0, once=True),
}

ITEMS = {
    "permission_ring": dict(hero_id=1, name="Обручальное кольцо дозволения", icon="💍", rarity="ЭПИЧЕСКИЙ", price=1200, description="+12% к защите. При низком HP один раз возвращает 20% здоровья и даёт щит."),
    "lost_cross": dict(hero_id=2, name="Потерянный крестик на карте", icon="✚", rarity="РЕДКИЙ", price=600, description="+8% к дополнительному криту. Неудачи повышают шанс ещё до +12%."),
    "developer_sock": dict(hero_id=3, name="Тухлый носок разработчика", icon="🧦", rarity="ЛЕГЕНДАРНЫЙ", price=2000, description="+5% к урону владельца и −7% к урону босса по отряду."),
    "trust_scanner": dict(hero_id=4, name="Сканер доверия", icon="📡", rarity="ЭПИЧЕСКИЙ", price=1200, description="+10% к уклонению, +8% к защите и усиленная защита после тяжёлого удара."),
    "false_crown": dict(hero_id=5, name="Корона ложного протагониста", icon="👑", rarity="ЛЕГЕНДАРНЫЙ", price=2000, description="+10% к урону. Если владелец не первый, бонус постепенно растёт ещё до +10%."),
    "diplomat_boots": dict(hero_id=6, name="Скользкие ботинки переговорщика", icon="👢", rarity="ЭПИЧЕСКИЙ", price=1200, description="+12% к уклонению и +8% к восстановлению действий."),
    "faded_cloak": dict(hero_id=7, name="Потускневший плащ героя", icon="🧥", rarity="ЛЕГЕНДАРНЫЙ", price=2000, description="+8% к урону, ещё +15% при низком HP. Один раз оставляет 1 HP."),
}


def install_hero_loadouts_v103(core: Any) -> None:
    if getattr(core, "_hero_loadouts_v103_installed", False):
        return
    core._hero_loadouts_v103_installed = True
    original_connect = core.Database.connect

    async def connect(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript("""
            CREATE TABLE IF NOT EXISTS hero_items_v103(chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,item_key TEXT NOT NULL,purchased_at INTEGER NOT NULL,PRIMARY KEY(chat_id,user_id,item_key));
            CREATE TABLE IF NOT EXISTS hero_equipment_v103(chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,item_key TEXT NOT NULL,equipped_at INTEGER NOT NULL,PRIMARY KEY(chat_id,user_id));
            CREATE TABLE IF NOT EXISTS hero_runtime_v103(boss_id TEXT NOT NULL,user_id INTEGER NOT NULL,effect_key TEXT NOT NULL,value REAL NOT NULL DEFAULT 0,stacks INTEGER NOT NULL DEFAULT 0,expires_at INTEGER NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL,PRIMARY KEY(boss_id,user_id,effect_key));
            CREATE INDEX IF NOT EXISTS idx_hero_runtime_v103 ON hero_runtime_v103(boss_id,effect_key,expires_at);
            """)
            await conn.commit()
    core.Database.connect = connect

    async def skin(db: Any, user_id: int) -> int:
        cur = await db._require_connection().execute("SELECT skin_id FROM hero_skin_choices_v101 WHERE user_id=?", (int(user_id),))
        row = await cur.fetchone(); value = int(row["skin_id"]) if row else 0
        return value if value in HEROES else 0

    async def skins(db: Any, ids: list[int]) -> dict[int, int]:
        ids = sorted({int(x) for x in ids if int(x) > 0})
        if not ids: return {}
        q = ",".join("?" for _ in ids)
        cur = await db._require_connection().execute(f"SELECT user_id,skin_id FROM hero_skin_choices_v101 WHERE user_id IN ({q})", tuple(ids))
        return {int(r["user_id"]): int(r["skin_id"]) for r in await cur.fetchall() if int(r["skin_id"]) in HEROES}

    async def equipment(db: Any, chat_id: int, ids: list[int]) -> dict[int, str]:
        ids = sorted({int(x) for x in ids if int(x) > 0})
        if not ids: return {}
        q = ",".join("?" for _ in ids)
        cur = await db._require_connection().execute(f"SELECT user_id,item_key FROM hero_equipment_v103 WHERE chat_id=? AND user_id IN ({q})", (int(chat_id), *ids))
        return {int(r["user_id"]): str(r["item_key"]) for r in await cur.fetchall() if str(r["item_key"]) in ITEMS}

    async def owned(db: Any, chat_id: int, user_id: int) -> list[str]:
        cur = await db._require_connection().execute("SELECT item_key FROM hero_items_v103 WHERE chat_id=? AND user_id=? ORDER BY purchased_at", (int(chat_id), int(user_id)))
        return [str(r["item_key"]) for r in await cur.fetchall() if str(r["item_key"]) in ITEMS]

    async def item(db: Any, chat_id: int, user_id: int) -> str | None:
        cur = await db._require_connection().execute("SELECT item_key FROM hero_equipment_v103 WHERE chat_id=? AND user_id=?", (int(chat_id), int(user_id)))
        row = await cur.fetchone(); key = str(row["item_key"]) if row else ""
        return key if key in ITEMS else None

    async def effect(db: Any, boss_id: str, user_id: int, key: str) -> Any:
        cur = await db._require_connection().execute("SELECT * FROM hero_runtime_v103 WHERE boss_id=? AND user_id=? AND effect_key=?", (str(boss_id), int(user_id), key))
        return await cur.fetchone()

    async def set_effect(db: Any, boss_id: str, user_id: int, key: str, value: float = 0, stacks: int = 0, expires: int = 0) -> None:
        await db._require_connection().execute("""INSERT INTO hero_runtime_v103(boss_id,user_id,effect_key,value,stacks,expires_at,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(boss_id,user_id,effect_key) DO UPDATE SET value=excluded.value,stacks=excluded.stacks,expires_at=excluded.expires_at,updated_at=excluded.updated_at""", (str(boss_id), int(user_id), key, float(value), int(stacks), int(expires), int(time.time())))

    async def delete_effect(db: Any, boss_id: str, user_id: int, key: str) -> None:
        await db._require_connection().execute("DELETE FROM hero_runtime_v103 WHERE boss_id=? AND user_id=? AND effect_key=?", (str(boss_id), int(user_id), key))

    async def active(db: Any, boss_id: str) -> list[Any]:
        cur = await db._require_connection().execute("SELECT * FROM hero_runtime_v103 WHERE boss_id=? AND (expires_at=0 OR expires_at>?)", (str(boss_id), int(time.time())))
        return list(await cur.fetchall())

    async def add_damage(db: Any, boss_id: str, user_id: int, result: dict[str, Any], amount: int, reason: str, critical: bool = False) -> dict[str, Any]:
        if amount <= 0 or not result.get("ok") or int(result.get("damage", 0)) <= 0: return result
        conn = db._require_connection(); now = int(time.time())
        async with db.lock:
            cur = await conn.execute("SELECT hp,max_hp,phase,status FROM boss_battles WHERE boss_id=?", (str(boss_id),)); battle = await cur.fetchone()
            if battle is None or str(battle["status"]) != "active": return result
            amount = min(int(battle["hp"]), int(amount)); hp = max(0, int(battle["hp"]) - amount); phase = core.boss_phase_for_hp(hp, int(battle["max_hp"]))
            await conn.execute("UPDATE boss_battles SET hp=?,phase=? WHERE boss_id=?", (hp, phase, str(boss_id)))
            await conn.execute("UPDATE boss_fighters SET damage_done=damage_done+?,critical_hits=critical_hits+? WHERE boss_id=? AND user_id=?", (amount, 1 if critical else 0, str(boss_id), int(user_id)))
            await conn.execute("INSERT INTO boss_logs(boss_id,log_text,created_at) VALUES(?,?,?)", (str(boss_id), f"⚡ {reason}: дополнительный урон −{amount} HP.", now)); await conn.commit()
        out = dict(result); out["damage"] = int(out.get("damage", 0)) + amount; out["bonus_damage"] = amount; out["hp"] = hp; out["phase"] = phase; out["defeated"] = hp <= 0
        if critical: out["critical"] = True
        return out

    async def attack_bonus(db: Any, boss_id: str, chat_id: int, user_id: int, result: dict[str, Any]) -> dict[str, Any]:
        if not result.get("ok") or int(result.get("damage", 0)) <= 0: return result
        conn = db._require_connection(); now = int(time.time()); base = int(result["damage"]); mult = 1.0; reasons = []
        rows = await active(db, boss_id); mine = {str(r["effect_key"]): r for r in rows if int(r["user_id"]) == int(user_id)}
        if any(str(r["effect_key"]) == "sol_damage" for r in rows): mult += .15; reasons.append("Переписанная реальность")
        if "samoz_rage" in mine: mult += float(mine["samoz_rage"]["value"]); reasons.append("Самозваний требует внимания")
        if "bylo_rage" in mine: mult += .25; reasons.append("Былое величие")
        key = await item(db, chat_id, user_id)
        if key == "developer_sock": mult += .05; reasons.append("Тухлый носок")
        elif key == "false_crown":
            mult += .10; cur = await conn.execute("SELECT user_id,joined_at FROM boss_fighters WHERE boss_id=? ORDER BY damage_done DESC,joined_at", (str(boss_id),)); ranks = list(await cur.fetchall())
            if ranks and int(ranks[0]["user_id"]) != int(user_id):
                me = next((r for r in ranks if int(r["user_id"]) == int(user_id)), None); mult += min(.10, (max(0, now-int(me["joined_at"]))//20)*.02) if me else 0
            reasons.append("Корона протагониста")
        elif key == "faded_cloak":
            mult += .08; cur = await conn.execute("SELECT player_hp,player_max_hp FROM boss_fighters WHERE boss_id=? AND user_id=?", (str(boss_id), int(user_id))); f = await cur.fetchone()
            if f and int(f["player_hp"]) < int(f["player_max_hp"])*.4: mult += .15
            reasons.append("Плащ былого героя")
        if "bylo_double" in mine:
            mult += 1; reasons.append("Возвращение в сюжет")
            async with db.lock: await delete_effect(db, boss_id, user_id, "bylo_double"); await conn.commit()
        extra_crit = 0
        if key == "lost_cross":
            row = await effect(db, boss_id, user_id, "cross_stack"); stack = min(.12, float(row["value"]) if row else 0)
            if result.get("critical"): new = 0
            elif random.random() < .08 + stack: extra_crit = max(1, round(base*.6)); new = 0
            else: new = min(.12, stack+.04)
            async with db.lock: await set_effect(db, boss_id, user_id, "cross_stack", new); await conn.commit()
        sliv = mine.get("sliv_crit")
        if sliv is not None and now >= int(float(sliv["value"])):
            mult += .8; reasons.append("Сливариус вернулся")
            async with db.lock: await delete_effect(db, boss_id, user_id, "sliv_crit"); await conn.commit()
        bonus = max(0, round(base*(mult-1))) + extra_crit
        return await add_damage(db, boss_id, user_id, result, bonus, ", ".join(reasons) or "усиление", extra_crit > 0) if bonus else result

    original_hit = core.Database.boss_apply_hit
    async def hit(self: Any, boss_id: str, chat_id: int, user_id: int) -> dict[str, Any]:
        result = await attack_bonus(self, boss_id, chat_id, user_id, await original_hit(self, boss_id, chat_id, user_id))
        if result.get("ok") and await item(self, chat_id, user_id) == "diplomat_boots":
            async with self.lock: await self._require_connection().execute("UPDATE boss_fighters SET last_attack_at=MAX(0,last_attack_at-1) WHERE boss_id=? AND user_id=?", (str(boss_id), int(user_id))); await self._require_connection().commit()
        return result
    core.Database.boss_apply_hit = hit

    original_ability = core.Database.boss_apply_ability
    async def hero_ability(self: Any, boss_id: str, chat_id: int, user_id: int, hero_id: int) -> dict[str, Any]:
        h = HEROES[hero_id]; conn = self._require_connection(); now = int(time.time())
        async with self.lock:
            cur = await conn.execute("SELECT * FROM boss_battles WHERE boss_id=?", (str(boss_id),)); battle = await cur.fetchone()
            cur = await conn.execute("SELECT * FROM boss_fighters WHERE boss_id=? AND user_id=?", (str(boss_id), int(user_id))); f = await cur.fetchone()
            if battle is None or int(battle["chat_id"]) != int(chat_id): return {"ok":False,"reason":"Бой не найден."}
            if str(battle["status"]) != "active" or f is None: return {"ok":False,"reason":"Сначала войди в активный бой."}
            if hero_id != 7 and (int(f["player_hp"]) <= 0 or int(f["knocked_out_until"]) > now): return {"ok":False,"reason":"Герой сейчас не может применить способность."}
            if hero_id == 7:
                if await effect(self, boss_id, user_id, "bylo_used"): return {"ok":False,"reason":"Возвращение доступно только один раз за бой."}
            else:
                left = int(h["cooldown"]) - (now-int(f["ability_used_at"]))
                if left > 0: return {"ok":False,"reason":f"Способность доступна через {core.human_duration(left)}."}
            detail = ""
            if hero_id == 1:
                await conn.execute("UPDATE boss_fighters SET protected=1,ability_used_at=? WHERE boss_id=? AND user_id=?", (now,boss_id,user_id)); await set_effect(self,boss_id,user_id,"kab_guard",.15,expires=now+20); detail="первый удар блокируется, отряд получает защиту"
            elif hero_id == 2:
                await conn.execute("UPDATE boss_fighters SET ability_used_at=? WHERE boss_id=? AND user_id=?", (now,boss_id,user_id)); await set_effect(self,boss_id,user_id,"sliv_evade",expires=now+5); await set_effect(self,boss_id,user_id,"sliv_crit",now+5,expires=now+90); detail="исчезает на 5 секунд и готовит усиленный крит"
            elif hero_id == 3:
                await conn.execute("UPDATE boss_fighters SET last_attack_at=MAX(0,last_attack_at-2),ability_used_at=MAX(0,ability_used_at-180),heal_used_at=MAX(0,heal_used_at-27),defend_used_at=MAX(0,defend_used_at-54),player_hp=MIN(player_max_hp,player_hp+MAX(1,CAST(player_max_hp*.1 AS INTEGER))) WHERE boss_id=?", (boss_id,)); await conn.execute("UPDATE boss_fighters SET ability_used_at=? WHERE boss_id=? AND user_id=?", (now,boss_id,user_id)); await set_effect(self,boss_id,user_id,"sol_damage",.15,expires=now+20); detail="лечит отряд, сокращает кулдауны и даёт +15% урона"
            elif hero_id == 4:
                await conn.execute("UPDATE boss_fighters SET protected=1,player_hp=MIN(player_max_hp,player_hp+MAX(1,CAST(player_max_hp*.1 AS INTEGER))) WHERE boss_id=? AND player_hp>0", (boss_id,)); await conn.execute("UPDATE boss_fighters SET ability_used_at=? WHERE boss_id=? AND user_id=?", (now,boss_id,user_id)); await set_effect(self,boss_id,user_id,"safe_zone",.20,expires=now+15); detail="отряд получает щит, лечение и снижение урона"
            elif hero_id == 5:
                cur = await conn.execute("SELECT 1 FROM boss_fighters bf JOIN hero_skin_choices_v101 hs ON hs.user_id=bf.user_id WHERE bf.boss_id=? AND hs.skin_id=4 LIMIT 1", (boss_id,)); jealousy = .10 if await cur.fetchone() else 0
                await conn.execute("UPDATE boss_fighters SET ability_used_at=? WHERE boss_id=? AND user_id=?", (now,boss_id,user_id)); await set_effect(self,boss_id,user_id,"samoz_rage",.30+jealousy,expires=now+15); await set_effect(self,boss_id,user_id,"samoz_provoke",stacks=1,expires=now+60); detail="получает +30% урона" + (" и ещё +10% от ревности к Сейфзонию" if jealousy else " и провоцирует босса")
            elif hero_id == 6:
                await conn.execute("UPDATE boss_battles SET next_action_at=next_action_at+5 WHERE boss_id=?", (boss_id,)); await conn.execute("UPDATE boss_fighters SET last_attack_at=MAX(0,last_attack_at-1),ability_used_at=MAX(0,ability_used_at-90),heal_used_at=MAX(0,heal_used_at-14),defend_used_at=MAX(0,defend_used_at-27) WHERE boss_id=?", (boss_id,)); await conn.execute("UPDATE boss_fighters SET ability_used_at=? WHERE boss_id=? AND user_id=?", (now,boss_id,user_id)); await set_effect(self,boss_id,user_id,"skolz_dodge",.5,stacks=1,expires=now+120); detail="задерживает босса, ускоряет кулдауны и готовит уклонение"
            else:
                max_hp=max(1,int(f["player_max_hp"])); hp=int(f["player_hp"])
                if hp<=0 or int(f["knocked_out_until"])>now: hp=max(1,round(max_hp*.4)); await conn.execute("UPDATE boss_fighters SET player_hp=?,knocked_out_until=0,ability_used_at=? WHERE boss_id=? AND user_id=?", (hp,now,boss_id,user_id)); detail="возвращается с 40% HP и готовит двойной удар"
                else: heal=max(1,round(max_hp*.25)); await conn.execute("UPDATE boss_fighters SET player_hp=MIN(player_max_hp,player_hp+?),ability_used_at=? WHERE boss_id=? AND user_id=?", (heal,now,boss_id,user_id)); await set_effect(self,boss_id,user_id,"bylo_rage",.25,expires=now+20); detail="лечится и пробуждает былое величие"
                await set_effect(self,boss_id,user_id,"bylo_double",stacks=1,expires=now+180); await set_effect(self,boss_id,user_id,"bylo_used",stacks=1)
            cur=await conn.execute("SELECT full_name FROM players WHERE chat_id=? AND user_id=?",(chat_id,user_id)); p=await cur.fetchone(); name=html.escape(str(p["full_name"] if p else h["name"])); await conn.execute("INSERT INTO boss_logs(boss_id,log_text,created_at) VALUES(?,?,?)",(boss_id,f"✨ {name}: «{h['ability']}» — {detail}.",now)); await conn.commit()
            return {"ok":True,"action":"hero_ability","hero_id":hero_id,"ability":h["ability"],"detail":detail,"defeated":False}

    async def ability(self: Any, boss_id: str, chat_id: int, user_id: int) -> dict[str, Any]:
        hero_id = await skin(self, user_id)
        result = await hero_ability(self,boss_id,chat_id,user_id,hero_id) if hero_id else await attack_bonus(self,boss_id,chat_id,user_id,await original_ability(self,boss_id,chat_id,user_id))
        if result.get("ok") and await item(self,chat_id,user_id)=="diplomat_boots":
            async with self.lock: await self._require_connection().execute("UPDATE boss_fighters SET ability_used_at=MAX(0,ability_used_at-48) WHERE boss_id=? AND user_id=?",(boss_id,user_id)); await self._require_connection().commit()
        return result
    core.Database.boss_apply_ability = ability

    original_boss_action = core.Database.boss_perform_action
    async def boss_action(self: Any, boss_id: str) -> dict[str, Any]:
        result = await original_boss_action(self,boss_id); affected=list(result.get("affected") or [])
        if not result.get("ok") or not affected: return result
        conn=self._require_connection(); now=int(time.time()); cur=await conn.execute("SELECT chat_id FROM boss_battles WHERE boss_id=?",(boss_id,)); b=await cur.fetchone()
        if b is None: return result
        cur=await conn.execute("SELECT user_id FROM boss_fighters WHERE boss_id=?",(boss_id,)); ids=[int(r["user_id"]) for r in await cur.fetchall()]; eq=await equipment(self,int(b["chat_id"]),ids); sm=await skins(self,ids); rows=await active(self,boss_id); em={(int(r["user_id"]),str(r["effect_key"])):r for r in rows}; kab=[int(r["user_id"]) for r in rows if str(r["effect_key"])=="kab_guard"]; safe=any(str(r["effect_key"])=="safe_zone" for r in rows); sock=any(v=="developer_sock" for v in eq.values()); notes=[]; out=[]
        async with self.lock:
            for a in affected:
                uid=int(a.get("user_id",0)); dmg=int(a.get("damage",0))
                if uid<=0 or dmg<=0 or a.get("protected"): out.append(a); continue
                cur=await conn.execute("SELECT player_hp,player_max_hp FROM boss_fighters WHERE boss_id=? AND user_id=?",(boss_id,uid)); f=await cur.fetchone()
                if f is None: out.append(a); continue
                evade=False; reduction=0.0
                if (uid,"sliv_evade") in em: evade=True; await delete_effect(self,boss_id,uid,"sliv_evade"); notes.append("Сливариус исчез от удара")
                elif (uid,"skolz_dodge") in em: evade=random.random()<.5; await delete_effect(self,boss_id,uid,"skolz_dodge"); notes.append("Скользий уклонился" if evade else "Скользий не успел выскользнуть")
                key=eq.get(uid); dodge=.10 if key=="trust_scanner" else .12 if key=="diplomat_boots" else 0
                if not evade and dodge and random.random()<dodge: evade=True; notes.append("Предмет помог уклониться")
                if key=="permission_ring": reduction+=.12
                if key=="trust_scanner": reduction+=.08
                if sock: reduction+=.07
                if kab: reduction+=.15; reduction+=.25 if uid in kab and sm.get(uid)==1 else 0
                if safe: reduction+=.20
                if (uid,"scanner_guard") in em: reduction+=.50; await delete_effect(self,boss_id,uid,"scanner_guard")
                restored=dmg if evade else round(dmg*min(.90,reduction)); net=max(0,dmg-restored)
                if restored: await conn.execute("UPDATE boss_fighters SET player_hp=MIN(player_max_hp,player_hp+?),damage_taken=MAX(0,damage_taken-?),knocked_out_until=CASE WHEN player_hp+?>0 THEN 0 ELSE knocked_out_until END WHERE boss_id=? AND user_id=?",(restored,restored,restored,boss_id,uid))
                hp=min(int(f["player_max_hp"]),int(f["player_hp"])+restored)
                if key=="trust_scanner" and net>=35: await set_effect(self,boss_id,uid,"scanner_guard",.5,stacks=1,expires=now+180)
                if key=="permission_ring" and hp>0 and hp<int(f["player_max_hp"])*.25 and await effect(self,boss_id,uid,"ring_used") is None:
                    heal=max(1,round(int(f["player_max_hp"])*.2)); await conn.execute("UPDATE boss_fighters SET player_hp=MIN(player_max_hp,player_hp+?),protected=1 WHERE boss_id=? AND user_id=?",(heal,boss_id,uid)); await set_effect(self,boss_id,uid,"ring_used",stacks=1); hp=min(int(f["player_max_hp"]),hp+heal); notes.append("Кольцо создало аварийный щит")
                if key=="faded_cloak" and hp<=0 and await effect(self,boss_id,uid,"cloak_used") is None:
                    await conn.execute("UPDATE boss_fighters SET player_hp=1,knocked_out_until=0 WHERE boss_id=? AND user_id=?",(boss_id,uid)); await set_effect(self,boss_id,uid,"cloak_used",stacks=1); hp=1; notes.append("Плащ оставил герою 1 HP")
                x=dict(a); x.update(damage=net,hp=hp,knocked_out=hp<=0,mitigated=restored); out.append(x)
            if notes: await conn.execute("INSERT INTO boss_logs(boss_id,log_text,created_at) VALUES(?,?,?)",(boss_id,"🛡 "+"; ".join(notes)+".",now))
            await conn.commit()
        result=dict(result); result["affected"]=out; result["loadout_notes"]=notes; return result
    core.Database.boss_perform_action = boss_action

    original_state = core.build_boss_web_state
    async def state(boss_id: str, user_id: int) -> dict[str, Any]:
        result=await original_state(boss_id,user_id)
        if not result.get("ok"): return result
        battle=await core.db.get_boss(boss_id)
        if battle is None: return result
        chat_id=int(battle["chat_id"]); ids=[int(x.get("user_id",0)) for x in result.get("fighters") or []]; sm=await skins(core.db,ids+[user_id]); eq=await equipment(core.db,chat_id,ids+[user_id]); now=int(result.get("now",time.time()))
        for f in result.get("fighters") or []:
            uid=int(f.get("user_id",0)); hid=sm.get(uid,int(f.get("skin_id",0) or 0)); h=HEROES.get(hid); key=eq.get(uid)
            if h: f.update(hero_id=hid,hero_name=h["name"],hero_title=h["title"])
            f.update(equipped_item=key,equipped_item_name=ITEMS[key]["name"] if key else None)
        me=result.get("self"); hid=sm.get(user_id,int((me or {}).get("skin_id",0) or 0)); h=HEROES.get(hid)
        if isinstance(me,dict) and h:
            me.update(hero_id=hid,hero_name=h["name"],hero_title=h["title"],ability_name=h["ability"],ability_hint=h["hint"])
            if h.get("once"): used=await effect(core.db,boss_id,user_id,"bylo_used"); me.setdefault("cooldowns",{})["ability"]=999999 if used else 0; me["ability_once_used"]=bool(used)
            else:
                cur=await core.db._require_connection().execute("SELECT ability_used_at FROM boss_fighters WHERE boss_id=? AND user_id=?",(boss_id,user_id)); r=await cur.fetchone(); me.setdefault("cooldowns",{})["ability"]=max(0,int(h["cooldown"])-(now-int(r["ability_used_at"] if r else 0)))
        cur=await core.db._require_connection().execute("SELECT points FROM players WHERE chat_id=? AND user_id=?",(chat_id,user_id)); p=await cur.fetchone(); inv=await owned(core.db,chat_id,user_id); equipped=eq.get(user_id)
        result.update(hero_catalog=[{"id":k,**v} for k,v in HEROES.items()],shop=[{"key":k,**v,"owned":k in inv,"equipped":k==equipped} for k,v in ITEMS.items()],inventory=inv,equipped_item=equipped,balance=int(p["points"] if p else 0)); return result
    core.build_boss_web_state = state

    async def buy(db: Any, chat_id: int, user_id: int, key: str) -> tuple[bool,str]:
        if key not in ITEMS: return False,"Предмет не найден."
        conn=db._require_connection(); now=int(time.time()); price=int(ITEMS[key]["price"])
        async with db.lock:
            cur=await conn.execute("SELECT 1 FROM hero_items_v103 WHERE chat_id=? AND user_id=? AND item_key=?",(chat_id,user_id,key))
            if await cur.fetchone(): return False,"Этот предмет уже куплен."
            cur=await conn.execute("SELECT points FROM players WHERE chat_id=? AND user_id=?",(chat_id,user_id)); p=await cur.fetchone(); points=int(p["points"] if p else 0)
            if points<price: return False,f"Не хватает влияния: нужно ещё {price-points}."
            await conn.execute("UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?",(price,now,chat_id,user_id)); await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",(chat_id,user_id,-price,f"hero_item:{key}",now)); await conn.execute("INSERT INTO hero_items_v103(chat_id,user_id,item_key,purchased_at) VALUES(?,?,?,?)",(chat_id,user_id,key,now)); await conn.commit()
        return True,f"Предмет «{ITEMS[key]['name']}» добавлен в инвентарь."

    async def equip(db: Any, chat_id: int, user_id: int, key: str | None) -> tuple[bool,str]:
        conn=db._require_connection(); now=int(time.time())
        async with db.lock:
            if key is None: await conn.execute("DELETE FROM hero_equipment_v103 WHERE chat_id=? AND user_id=?",(chat_id,user_id)); await conn.commit(); return True,"Предмет снят."
            if key not in ITEMS: return False,"Предмет не найден."
            cur=await conn.execute("SELECT 1 FROM hero_items_v103 WHERE chat_id=? AND user_id=? AND item_key=?",(chat_id,user_id,key))
            if await cur.fetchone() is None: return False,"Сначала купи этот предмет."
            await conn.execute("INSERT INTO hero_equipment_v103(chat_id,user_id,item_key,equipped_at) VALUES(?,?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET item_key=excluded.item_key,equipped_at=excluded.equipped_at",(chat_id,user_id,key,now)); await conn.commit()
        return True,f"Экипирован предмет «{ITEMS[key]['name']}»."

    original_action=core.webapp_action
    async def action(request: Any):
        payload=await core._webapp_json(request); name=str(payload.get("action") or "")
        if name not in {"buy_item","equip_item","unequip_item"}: return await original_action(request)
        user,start=core._webapp_auth(request)
        if user is None: return core._webapp_error(start or "Нет авторизации.",401)
        boss_id=str(start or payload.get("boss_id") or ""); battle=await core.db.get_boss(boss_id)
        if battle is None: return core._webapp_error("Бой не найден.",404)
        chat_id=int(battle["chat_id"]); await core.db.upsert_player(chat_id,user); key=str(payload.get("item_key") or "")
        ok,msg=await buy(core.db,chat_id,int(user.id),key) if name=="buy_item" else await equip(core.db,chat_id,int(user.id),key if name=="equip_item" else None)
        if not ok: return core._webapp_error(msg)
        data=await core.build_boss_web_state(boss_id,int(user.id)); data["message"]=msg; return core.web.json_response(data)
    core.webapp_action=action
