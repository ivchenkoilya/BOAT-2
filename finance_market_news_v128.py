from __future__ import annotations

import json
import math
import secrets
from typing import Any

from finance_investments_v127_core import MARKET_TICK_SECONDS, STOCKS, _now

POSITIVE_WORDS = (
    "поддерж", "субсид", "развит", "рост", "льгот", "производств", "инвест",
    "расшир", "грант", "помощ", "снижен", "отмен", "стимул",
)
NEGATIVE_WORDS = (
    "запрет", "огранич", "повыш", "акциз", "штраф", "контрол", "провер",
    "санкц", "кризис", "дефицит", "налог", "сокращ", "скандал",
)

COMPANY_COPY: dict[str, dict[str, tuple[str, str, str]]] = {
    "EGO": {
        "up": (
            "EGO Corp укрепила позиции после решения властей",
            "Компания ожидает роста доверия и спроса на продукты влияния.",
            "EGO Corp положительно оценила государственное решение «{source}». Руководство считает, что новые условия укрепят репутационный рынок и позволят компании расширить присутствие. Инвесторы увеличили спрос на акции, ожидая улучшения показателей в следующих отчётных периодах.",
        ),
        "down": (
            "EGO Corp предупредила о рисках для рынка влияния",
            "Новые правила могут снизить спрос и увеличить расходы компании.",
            "EGO Corp выступила с осторожным заявлением после решения «{source}». Компания ожидает роста административных расходов и снижения активности части клиентов. Инвесторы начали сокращать позиции, пока руководство оценивает долгосрочные последствия.",
        ),
    },
    "HERO": {
        "up": (
            "Hero Energy объявила об ускорении развития",
            "Компания направит дополнительные ресурсы на расширение энергетической сети.",
            "Hero Energy сообщила, что решение «{source}» создаёт благоприятные условия для развития инфраструктуры. Компания готовит расширение сети и рассчитывает на рост спроса. Рынок воспринял заявление положительно.",
        ),
        "down": (
            "Hero Energy пересмотрела планы расширения",
            "Компания опасается роста затрат и замедления инфраструктурных проектов.",
            "После решения «{source}» Hero Energy начала пересматривать инвестиционную программу. Руководство предупредило о возможном росте затрат и переносе части проектов. Акции оказались под давлением продавцов.",
        ),
    },
    "NPC": {
        "up": (
            "NPC Industries получила поддержку массового сегмента",
            "Социальные меры увеличили спрос на продукцию компании.",
            "NPC Industries заявила, что решение «{source}» поддержит массовый рынок и повысит покупательскую активность. Компания ожидает расширения аудитории и роста оборота. Инвесторы положительно оценили перспективы доступного сегмента.",
        ),
        "down": (
            "NPC Industries зафиксировала снижение массового спроса",
            "Компания готовится к более слабому потребительскому периоду.",
            "NPC Industries сообщила, что решение «{source}» может снизить активность массового сегмента. Руководство готовит программу сокращения расходов, а инвесторы ожидают более слабых результатов в ближайшем периоде.",
        ),
    },
    "CORV": {
        "up": (
            "CORVUS увеличивает производство снюса",
            "Производитель ожидает роста продаж и расширения внутреннего рынка.",
            "Производитель снюса CORVUS положительно оценил решение «{source}». Компания планирует увеличить объёмы производства, укрепить поставки сырья и расширить новую линейку продукции. Инвесторы рассчитывают на рост продаж, однако акция остаётся высокорисковой.",
        ),
        "down": (
            "CORVUS предупредила о росте издержек",
            "Новые ограничения могут повлиять на производство и продажи снюса.",
            "Производитель снюса CORVUS отреагировал на решение «{source}». Руководство предупредило о возможном росте расходов, усложнении поставок и снижении спроса. Компания рассматривает пересмотр производственного плана, а инвесторы начали фиксировать прибыль.",
        ),
    },
    "CENTER": {
        "up": (
            "Вокруг Центра Вселенной вырос спекулятивный ажиотаж",
            "Политическая неопределённость усилила спрос на самый рискованный актив.",
            "После события «{source}» внимание спекулянтов переключилось на акции Центра Вселенной. Объём краткосрочных сделок вырос, а цена резко ускорилась. Аналитики предупреждают, что движение основано на эмоциях и может быстро развернуться.",
        ),
        "down": (
            "Инвесторы уходят из акций Центра Вселенной",
            "Снижение неопределённости ослабило интерес к спекулятивному активу.",
            "Событие «{source}» снизило напряжённость на рынке. Инвесторы начали закрывать рискованные позиции в Центре Вселенной и возвращаться к более стабильным компаниям. Волатильность остаётся высокой.",
        ),
    },
}

RANDOM_NEWS: dict[str, dict[str, list[tuple[str, str, str]]]] = {
    "EGO": {
        "up": [
            ("EGO Corp объявила рекордный сезон", "Компания сообщила о самом сильном росте влияния за последнее время.", "EGO Corp подвела итоги сезона и заявила о рекордных показателях. Интерес к продуктам компании оказался выше ожиданий, а доверие инвесторов укрепилось. Руководство назвало период началом новой эры доминирования и пообещало продолжить расширение."),
            ("EGO Corp запускает премиальную программу", "Новая система статуса вызвала повышенный интерес рынка.", "EGO Corp представила премиальную программу для самых влиятельных участников. Компания ожидает роста среднего дохода на клиента и расширения элитного сегмента. Инвесторы встретили запуск повышенным спросом на акции."),
        ],
        "down": [
            ("Инвесторы усомнились в обещаниях EGO Corp", "Рынок требует подтверждения амбициозных планов реальными результатами.", "После серии громких заявлений часть инвесторов сочла планы EGO Corp завышенными. На рынке началась фиксация прибыли. Компании потребуется сильный отчёт, чтобы восстановить уверенность покупателей."),
        ],
    },
    "HERO": {
        "up": [("Hero Energy запускает программу ускоренного роста", "Компания расширяет энергетическую инфраструктуру.", "Hero Energy представила программу развития сети и сообщила о готовности к повышенной нагрузке. Руководство рассчитывает на устойчивый рост спроса в следующих рыночных циклах.")],
        "down": [("Hero Energy сообщила о задержке модернизации", "Часть инфраструктурных работ переносится.", "Hero Energy предупредила о задержке нескольких проектов модернизации. Компания связывает перенос сроков с ростом расходов и временным дефицитом ресурсов.")],
    },
    "NPC": {
        "up": [("NPC Industries получила поддержку массового рынка", "Продажи доступной продукции выросли.", "NPC Industries сообщила о заметном росте спроса в массовом сегменте. Компания расширяет выпуск доступной продукции и ожидает улучшения результатов в следующем отчёте.")],
        "down": [("NPC Industries столкнулась с оттоком покупателей", "Массовый сегмент сократил расходы.", "NPC Industries зафиксировала снижение активности покупателей. Руководство готовит временную программу экономии и пересматривает прогноз продаж.")],
    },
    "CORV": {
        "up": [
            ("CORVUS представила новую линейку снюса", "Компания ожидает сильный старт продаж.", "Производитель снюса CORVUS представил новую линейку продукции и сообщил о высоком интересе со стороны рынка. Компания увеличивает объёмы производства и готовит расширение поставок."),
            ("CORVUS объявила о рекордных продажах", "Спрос на продукцию производителя превысил прогноз.", "CORVUS подвела итоги периода и сообщила о рекордных продажах снюса. Руководство планирует направить часть результата на увеличение производства и укрепление поставок сырья."),
        ],
        "down": [
            ("Проверка качества ударила по CORVUS", "Компания временно приостановила часть поставок.", "CORVUS сообщила о дополнительной проверке качества одной из партий продукции. Часть поставок временно приостановлена, а инвесторы оценивают возможные расходы компании."),
            ("CORVUS столкнулась с дефицитом сырья", "Производственный план может быть сокращён.", "Производитель снюса CORVUS предупредил о перебоях с поставками сырья. Компания рассматривает временное сокращение выпуска и поиск новых поставщиков."),
        ],
    },
    "CENTER": {
        "up": [("Центр Вселенной оказался в центре рыночного ажиотажа", "Спекулятивный спрос резко вырос.", "Участники рынка начали активно покупать акции Центра Вселенной после волны слухов. Фундаментальных подтверждений роста пока нет, поэтому риск резкого отката остаётся очень высоким.")],
        "down": [("Спекулянты фиксируют прибыль в Центре Вселенной", "После резкого движения началась массовая продажа.", "Инвесторы начали закрывать краткосрочные позиции в Центре Вселенной. Цена оказалась под давлением, а волатильность остаётся экстремальной.")],
    },
}


def _text_score(text: str) -> int:
    lower = text.casefold()
    positive = sum(1 for word in POSITIVE_WORDS if word in lower)
    negative = sum(1 for word in NEGATIVE_WORDS if word in lower)
    return positive - negative


def _clamp_effect(value: int) -> int:
    return max(-800, min(800, int(value)))


def _general_effects(title: str, text: str) -> dict[str, int]:
    combined = f"{title} {text}".casefold()
    score = _text_score(combined)
    direction = 1 if score >= 0 else -1
    effects: dict[str, int] = {}

    if any(word in combined for word in ("снюс", "никотин", "табак", "акциз", "курен", "сырь")):
        effects["CORV"] = direction * (260 if score else -180)
    if any(word in combined for word in ("энерг", "инфраструкт", "электр", "модерниз")):
        effects["HERO"] = direction * 220
    if any(word in combined for word in ("массов", "социал", "пособ", "выплат", "поддержк населения", "бедн")):
        effects["NPC"] = direction * 210
    if any(word in combined for word in ("репутац", "статус", "элит", "влияни", "награ", "имидж")):
        effects["EGO"] = direction * 190
    if any(word in combined for word in ("кризис", "чрезвыч", "скандал", "паник", "конфликт", "санкц")):
        effects["CENTER"] = 260
        effects.setdefault("EGO", -100)
    if any(word in combined for word in ("стабильн", "контроль рынка", "прозрачност")):
        effects["CENTER"] = -180
        effects.setdefault("EGO", 80)

    if not effects:
        effects = {"EGO": 45 * direction, "HERO": 35 * direction, "NPC": 25 * direction, "CENTER": -25 * direction}
    return {symbol: _clamp_effect(effect) for symbol, effect in effects.items()}


def law_effects(row: Any) -> dict[str, int]:
    law_type = str(row["law_type"])
    title = str(row["title"])
    text = str(row["text"])
    try:
        payload = json.loads(str(row["payload_json"] or "{}"))
    except Exception:
        payload = {}

    if law_type == "tax_policy":
        if not payload.get("enabled", True):
            return {"EGO": 170, "HERO": 130, "CORV": 190, "NPC": -40, "CENTER": -60}
        rates = [int(payload.get(f"rate_{index}", 0) or 0) for index in range(1, 5)]
        average = sum(rates) / max(1, len(rates))
        pressure = max(80, min(420, round(average * 38)))
        return {"EGO": -pressure, "HERO": -round(pressure * .65), "CORV": -round(pressure * .9), "NPC": round(pressure * .3), "CENTER": round(pressure * .45)}
    if law_type == "budget":
        effects = _general_effects(title, text)
        effects["NPC"] = effects.get("NPC", 0) + 120
        effects["HERO"] = effects.get("HERO", 0) + 45
        return effects
    if law_type == "appointment":
        office = str(payload.get("office_key") or "")
        if office == "finance":
            return {"EGO": 110, "HERO": 80, "NPC": 35, "CENTER": -120}
        return {"EGO": 65, "CORV": -90, "CENTER": -55}
    if law_type == "sanction":
        return {"EGO": -80, "HERO": -45, "CORV": -70, "CENTER": 190}
    return _general_effects(title, text)


def company_news(symbol: str, source: str, effect_bp: int) -> tuple[str, str, str]:
    direction = "up" if effect_bp >= 0 else "down"
    title, summary, body = COMPANY_COPY[symbol][direction]
    return title, summary, body.format(source=source)


def random_company_news(symbol: str, selector: int, direction: int) -> tuple[str, str, str]:
    key = "up" if direction > 0 else "down"
    choices = RANDOM_NEWS[symbol][key]
    return choices[selector % len(choices)]


async def _insert_news(
    conn: Any,
    *,
    chat_id: int,
    symbol: str,
    source_key: str,
    source_type: str,
    category: str,
    title: str,
    summary: str,
    body: str,
    effect_bp: int,
    event_at: int,
    source_at: int,
) -> None:
    await conn.execute(
        """
        INSERT OR IGNORE INTO finance_market_news_v128(
            news_id,chat_id,symbol,source_key,source_type,category,title,summary,body,
            effect_bp,event_at,source_at,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            secrets.token_urlsafe(10), int(chat_id), str(symbol), str(source_key), str(source_type),
            str(category), str(title), str(summary), str(body), int(effect_bp), int(event_at),
            int(source_at), _now(),
        ),
    )


async def sync_government_news(core: Any, chat_id: int) -> None:
    conn = core.db._require_connection()
    impact_at = (_now() // MARKET_TICK_SECONDS) * MARKET_TICK_SECONDS
    try:
        cursor = await conn.execute(
            "SELECT * FROM government_laws_v127 WHERE chat_id=? AND active=1 ORDER BY enacted_at DESC LIMIT 100",
            (int(chat_id),),
        )
        laws = list(await cursor.fetchall())
        cursor = await conn.execute(
            "SELECT * FROM government_bills_v127 WHERE chat_id=? AND status IN ('vetoed','rejected') AND resolved_at>0 ORDER BY resolved_at DESC LIMIT 60",
            (int(chat_id),),
        )
        bills = list(await cursor.fetchall())
        cursor = await conn.execute(
            "SELECT * FROM government_treasury_log_v127 WHERE chat_id=? ORDER BY log_id DESC LIMIT 100",
            (int(chat_id),),
        )
        treasury = list(await cursor.fetchall())
    except Exception:
        return

    async with core.db.lock:
        for row in laws:
            source = f"Закон №{int(row['number'])} «{str(row['title'])}»"
            for symbol, effect in law_effects(row).items():
                title, summary, body = company_news(symbol, source, effect)
                await _insert_news(
                    conn, chat_id=chat_id, symbol=symbol, source_key=f"law:{row['law_id']}",
                    source_type="government_law", category="Правительство", title=title,
                    summary=summary, body=body, effect_bp=effect, event_at=impact_at,
                    source_at=int(row["enacted_at"]),
                )

        for row in bills:
            status = str(row["status"])
            source = f"{('Вето на' if status == 'vetoed' else 'Отклонение')} законопроекта №{int(row['number'])} «{str(row['title'])}»"
            base = _general_effects(str(row["title"]), str(row["description"]))
            for symbol, value in base.items():
                effect = _clamp_effect(-round(value * .45))
                title, summary, body = company_news(symbol, source, effect)
                await _insert_news(
                    conn, chat_id=chat_id, symbol=symbol, source_key=f"bill:{row['bill_id']}:{status}",
                    source_type="government_decision", category="Решение власти", title=title,
                    summary=summary, body=body, effect_bp=effect, event_at=impact_at,
                    source_at=int(row["resolved_at"]),
                )

        for row in treasury:
            source_type = str(row["source_type"])
            source = str(row["reason"] or "Действие правительства")
            delta = int(row["delta"] or 0)
            scale = max(30, min(220, round(math.log10(abs(delta) + 10) * 35)))
            if source_type == "tax":
                effects = {"EGO": -scale, "HERO": -round(scale * .65), "CORV": -round(scale * .9), "NPC": round(scale * .35), "CENTER": round(scale * .5)}
            elif source_type == "budget":
                effects = _general_effects(source, source)
                effects["NPC"] = effects.get("NPC", 0) + scale
            elif source_type == "tax_debt":
                effects = {"EGO": 35, "CENTER": -30}
            else:
                continue
            for symbol, effect in effects.items():
                title, summary, body = company_news(symbol, source, effect)
                await _insert_news(
                    conn, chat_id=chat_id, symbol=symbol, source_key=f"treasury:{row['log_id']}",
                    source_type="government_action", category="Действие правительства",
                    title=title, summary=summary, body=body, effect_bp=effect,
                    event_at=impact_at, source_at=int(row["created_at"]),
                )
        await conn.commit()


async def news_for_range(conn: Any, chat_id: int, symbol: str, start_at: int, end_at: int) -> list[dict[str, Any]]:
    cursor = await conn.execute(
        """
        SELECT * FROM finance_market_news_v128
        WHERE chat_id=? AND symbol=? AND event_at BETWEEN ? AND ?
        ORDER BY event_at ASC,created_at ASC
        """,
        (int(chat_id), str(symbol), int(start_at), int(end_at)),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def latest_news(conn: Any, chat_id: int, symbol: str = "", limit: int = 20) -> list[dict[str, Any]]:
    if symbol:
        cursor = await conn.execute(
            "SELECT * FROM finance_market_news_v128 WHERE chat_id=? AND symbol=? ORDER BY source_at DESC,created_at DESC LIMIT ?",
            (int(chat_id), str(symbol), int(limit)),
        )
    else:
        cursor = await conn.execute(
            "SELECT * FROM finance_market_news_v128 WHERE chat_id=? ORDER BY source_at DESC,created_at DESC LIMIT ?",
            (int(chat_id), int(limit)),
        )
    return [dict(row) for row in await cursor.fetchall()]
