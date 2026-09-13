"""Генератор тестового набора данных для дашборда «ЛогиХаб».

Формирует CSV-файл с заказами на перевозку (вариант 15 «Процесс управления
логистикой»). Распределения подобраны так, чтобы воспроизводить исторический
KPI продукта OTIF по релизам: v1.0 – 72 %, v1.5 – 81 %, v2.0 – 87 %.

Запуск:
    python data/generate_data.py --seed 45 --out data/logistics_orders.csv
"""
from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

REGIONS = {
    "Хабаровский край": ("Хабаровск", 1.00),
    "Приморский край": ("Владивосток", 0.85),
    "Амурская область": ("Благовещенск", 0.55),
    "Сахалинская область": ("Южно-Сахалинск", 0.35),
    "Еврейская АО": ("Биробиджан", 0.30),
}
HUB = "Комсомольск-на-Амуре"

CARGO_TYPES = {  # категория: (средний вес кг, коэффициент тарифа, доля)
    "Электроника": (850, 1.25, 0.16),
    "Продукты питания": (4200, 1.10, 0.24),
    "Стройматериалы": (9500, 0.95, 0.22),
    "Одежда и обувь": (1300, 1.05, 0.14),
    "Мебель": (2600, 1.10, 0.12),
    "Медикаменты": (600, 1.30, 0.12),
}

TRANSPORT = {  # тип: (грузоподъёмность кг, средняя скорость км/ч, тариф руб/км)
    "Газель": (1500, 60, 32),
    "Фура": (20000, 55, 75),
    "Рефрижератор": (12000, 52, 88),
    "Контейнер (ж/д)": (24000, 40, 55),
}

CLIENTS = [
    "ООО «АмурСтрой»", "ООО «ДальФуд»", "АО «ВостокМед»", "ИП Ковалёв",
    "ООО «ТехноДВ»", "ООО «МебельГрад»", "ООО «ПримТорг»", "АО «СахалинСнаб»",
    "ООО «Модный Дом»", "ООО «ХабЭлектро»", "ООО «АптекаПлюс»", "ООО «ДВ Логистик»",
]

# Релизы продукта и целевые значения OTIF в периоде действия релиза
RELEASES = [
    (date(2024, 1, 1), "v1.0", 0.72),
    (date(2025, 2, 1), "v1.5", 0.81),
    (date(2026, 2, 1), "v2.0", 0.87),
]

DISTANCE = {"Хабаровский край": 400, "Приморский край": 1050, "Амурская область": 1350,
            "Сахалинская область": 1600, "Еврейская АО": 560}


def release_for(day: date) -> tuple[str, float]:
    current = RELEASES[0]
    for rel in RELEASES:
        if day >= rel[0]:
            current = rel
    return current[1], current[2]


def pick_weighted(mapping: dict, index: int):
    keys = list(mapping)
    weights = [mapping[k][index] for k in keys]
    return random.choices(keys, weights=weights, k=1)[0]


def choose_transport(cargo: str, weight: float) -> str:
    if cargo in ("Продукты питания", "Медикаменты") and random.random() < 0.7:
        return "Рефрижератор"
    if weight <= 1500:
        return "Газель"
    if weight > 12000 and random.random() < 0.5:
        return "Контейнер (ж/д)"
    return "Фура"


def generate(start: date, end: date) -> list[dict]:
    rows: list[dict] = []
    order_no = 10000
    day = start
    while day <= end:
        months_from_start = (day.year - start.year) * 12 + day.month - start.month
        base = 5 + months_from_start * 0.18            # рост числа заказов
        season = 1.25 if day.month in (11, 12) else 0.85 if day.month in (1, 5) else 1.0
        weekday = 0.45 if day.weekday() >= 5 else 1.0
        count = max(0, int(random.gauss(base * season * weekday, 1.6)))
        release, otif_target = release_for(day)
        for _ in range(count):
            order_no += 1
            region = pick_weighted(REGIONS, 1)
            cargo = pick_weighted(CARGO_TYPES, 2)
            avg_w, tariff, _ = CARGO_TYPES[cargo]
            weight = round(max(80.0, random.lognormvariate(0, 0.55) * avg_w), 1)
            transport = choose_transport(cargo, weight)
            distance = round(DISTANCE[region] * random.uniform(0.75, 1.25))
            speed = TRANSPORT[transport][1]
            plan_days = max(1, round(distance / (speed * 10)) + 1)

            # Факт по OTIF: вероятности согласованы с целевым значением релиза
            on_time = random.random() < (otif_target + (1 - otif_target) * 0.45)
            in_full = random.random() < min(0.995, otif_target / (otif_target + (1 - otif_target) * 0.45))
            delay = 0 if on_time else random.choice([1, 1, 2, 2, 3, 4])
            status = "Доставлен"
            if day > end - timedelta(days=plan_days + delay):
                status = "В пути" if on_time else "Задержан"
            if random.random() < 0.025:
                status, on_time, in_full, delay = "Отменён", False, False, 0

            revenue = round(distance * TRANSPORT[transport][2] * tariff * random.uniform(0.92, 1.12)
                            + weight * 0.8 + 3000, 2)
            fuel = round(distance * {"Газель": 14, "Фура": 38, "Рефрижератор": 42,
                                     "Контейнер (ж/д)": 22}[transport] * random.uniform(0.9, 1.1), 2)
            driver = round((plan_days + delay) * random.uniform(3200, 4200), 2)
            warehouse = round(weight * random.uniform(0.35, 0.6) + 400, 2)
            tolls = round(distance * random.uniform(1.8, 3.2), 2) if transport != "Контейнер (ж/д)" else 0.0
            penalty = round(revenue * 0.05 * delay, 2)
            other = round(random.uniform(300, 1500) + penalty, 2)
            if status == "Отменён":
                revenue, fuel, driver, tolls = 0.0, 0.0, 0.0, 0.0
            total_cost = round(fuel + driver + warehouse + tolls + other, 2)
            rows.append({
                "order_id": f"LH-{order_no}",
                "order_date": day.isoformat(),
                "planned_delivery": (day + timedelta(days=plan_days)).isoformat(),
                "actual_delivery": "" if status in ("В пути", "Отменён") else
                (day + timedelta(days=plan_days + delay)).isoformat(),
                "release": release,
                "client": random.choice(CLIENTS),
                "region": region,
                "destination": REGIONS[region][0],
                "origin": HUB,
                "cargo_type": cargo,
                "transport_type": transport,
                "distance_km": distance,
                "weight_kg": weight,
                "revenue": revenue,
                "cost_fuel": fuel,
                "cost_driver": driver,
                "cost_warehouse": warehouse,
                "cost_tolls": tolls,
                "cost_other": other,
                "total_cost": total_cost,
                "profit": round(revenue - total_cost, 2),
                "status": status,
                "on_time": int(on_time),
                "in_full": int(in_full),
                "otif": int(on_time and in_full),
            })
        day += timedelta(days=1)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=45)
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2026-08-31")
    parser.add_argument("--out", default=str(Path(__file__).with_name("logistics_orders.csv")))
    args = parser.parse_args()

    random.seed(args.seed)
    rows = generate(date.fromisoformat(args.start), date.fromisoformat(args.end))
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Сформировано заказов: {len(rows)} -> {args.out}")


if __name__ == "__main__":
    main()
