from __future__ import annotations

import hashlib
from typing import Any

import government_theft_quest_v163_core as quest


def _route_text(amount: int, parts: list[int], suffix: str) -> str:
    return (
        f"Казна −{quest.gov._fmt(amount)} → пакеты "
        + " + ".join(quest.gov._fmt(value) for value in parts)
        + f" → {suffix}"
    )


def better_finance_task(theft_id: str, amount: int, hard: bool = False) -> dict[str, Any]:
    rng = quest._rng(theft_id, "finance-puzzle-hard" if hard else "finance-puzzle")
    count = 4 if hard else 3
    base = max(1, amount // count)
    correct_parts = [base for _ in range(count)]
    correct_parts[-1] += amount - sum(correct_parts)
    wrong_more = list(correct_parts)
    wrong_more[-1] += 17
    wrong_less = list(correct_parts)
    wrong_less[0] = max(1, wrong_less[0] - 11)
    options = [
        _route_text(amount, correct_parts, "закрытый счёт R-7"),
        _route_text(amount, wrong_more, "закрытый счёт R-7"),
        _route_text(amount, wrong_less, "закрытый счёт R-7"),
    ]
    if hard:
        mixed = list(correct_parts)
        mixed[0] += 9
        mixed[-1] = max(1, mixed[-1] - 4)
        options.append(_route_text(amount, mixed, "закрытый счёт R-7"))
    correct = options[0]
    rng.shuffle(options)
    return {
        "kind": "finance_route",
        "question": "Какой маршрут сохраняет точную контрольную сумму?",
        "description": (
            "Все маршруты выглядят одинаково. Сложи размеры пакетов: "
            "только один вариант в точности равен сумме хищения."
        ),
        "options": [{"id": str(index), "text": text} for index, text in enumerate(options)],
        "answer": str(options.index(correct)),
        "hard": hard,
    }


def better_audit_task(theft_id: str, amount: int, started_at: int, hard: bool = False) -> dict[str, Any]:
    rng = quest._rng(theft_id, "audit-puzzle-hard" if hard else "audit-puzzle")
    count = 5 if hard else 4
    anomaly_index = rng.randrange(count)
    records: list[dict[str, Any]] = []
    labels = ("резервная проводка", "бюджетный пакет", "контрольная копия", "реестр выплаты", "служебная запись")
    for index in range(count):
        timestamp = started_at - 140 + index * 29
        value = max(1, amount // count + index * 2)
        signature = hashlib.sha1(f"{theft_id}:{timestamp}:{value}:valid".encode()).hexdigest()[:8].upper()
        if index == anomaly_index:
            # Единственная запись создана уже после хищения и подписана другим ключом.
            timestamp = started_at + 48
            value += 17
            signature = hashlib.sha1(f"{theft_id}:{timestamp}:{value}:foreign".encode()).hexdigest()[:8].upper()
        records.append(
            {
                "id": str(index),
                "time": timestamp,
                "amount": value,
                "signature": signature,
                "note": labels[index],
            }
        )
    return {
        "kind": "audit_record",
        "question": "Какая запись появилась после момента хищения?",
        "description": (
            "Сверь время уголовного дела с журналом. Подлинные контрольные записи "
            "созданы до вывода средств; одна запись была добавлена спустя 48 секунд."
        ),
        "records": records,
        "answer": str(anomaly_index),
        "hard": hard,
    }


def install_theft_quest_puzzles_v163(_core: Any) -> None:
    quest._finance_task = better_finance_task
    quest._audit_task = better_audit_task
