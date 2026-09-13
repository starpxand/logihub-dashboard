"""Загрузка, проверка и агрегирование выгрузки заказов «ЛогиХаб»."""
from __future__ import annotations

import base64
import io

import pandas as pd

REQUIRED_COLUMNS = {
    "order_id", "order_date", "release", "client", "region", "cargo_type", "transport_type",
    "distance_km", "weight_kg", "revenue", "cost_fuel", "cost_driver", "cost_warehouse",
    "cost_tolls", "cost_other", "total_cost", "profit", "status", "on_time", "in_full", "otif",
}

COST_COLUMNS = {
    "cost_fuel": "Топливо",
    "cost_driver": "Оплата водителей",
    "cost_warehouse": "Складские операции",
    "cost_tolls": "Платные дороги",
    "cost_other": "Прочие и штрафы",
}

PERIODS = {"M": "Месяц", "Q": "Квартал", "Y": "Год"}
OTIF_TARGET = 90.0


class DataError(ValueError):
    """Ошибка формата загружаемого файла."""


def parse_upload(contents: str, filename: str) -> pd.DataFrame:
    """Декодирует содержимое dcc.Upload (data URI) и возвращает проверенный DataFrame."""
    if not filename.lower().endswith(".csv"):
        raise DataError("Поддерживаются только файлы CSV")
    try:
        _, payload = contents.split(",", 1)
        raw = base64.b64decode(payload)
        text = raw.decode("utf-8-sig")
    except (ValueError, UnicodeDecodeError) as exc:
        raise DataError("Не удалось прочитать файл: ожидается CSV в кодировке UTF-8") from exc
    return prepare(pd.read_csv(io.StringIO(text)))


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Проверяет обязательные столбцы и приводит типы."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise DataError("В файле нет столбцов: " + ", ".join(sorted(missing)))
    df = df.copy()
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df = df.dropna(subset=["order_date"])
    numeric = ["distance_km", "weight_kg", "revenue", "total_cost", "profit", "on_time", "in_full", "otif",
               *COST_COLUMNS]
    df[numeric] = df[numeric].apply(pd.to_numeric, errors="coerce").fillna(0)
    return df.sort_values("order_date").reset_index(drop=True)


def filter_orders(df: pd.DataFrame, start=None, end=None, cargo=None, regions=None) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if start:
        mask &= df["order_date"] >= pd.to_datetime(start)
    if end:
        mask &= df["order_date"] <= pd.to_datetime(end)
    if cargo:
        mask &= df["cargo_type"].isin(cargo)
    if regions:
        mask &= df["region"].isin(regions)
    return df[mask]


def completed(df: pd.DataFrame) -> pd.DataFrame:
    """Заказы, участвующие в расчёте KPI (без отменённых)."""
    return df[df["status"] != "Отменён"]


def kpis(df: pd.DataFrame) -> dict:
    done = completed(df)
    n = len(done)
    revenue = float(done["revenue"].sum())
    profit = float(done["profit"].sum())
    return {
        "orders": n,
        "revenue": revenue,
        "cost": float(done["total_cost"].sum()),
        "profit": profit,
        "margin": profit / revenue * 100 if revenue else 0.0,
        "otif": done["otif"].mean() * 100 if n else 0.0,
        "on_time": done["on_time"].mean() * 100 if n else 0.0,
        "in_full": done["in_full"].mean() * 100 if n else 0.0,
        "cancel_rate": (df["status"] == "Отменён").mean() * 100 if len(df) else 0.0,
    }


def period_label(ts: pd.Timestamp, freq: str) -> str:
    if freq == "Y":
        return f"{ts.year}"
    if freq == "Q":
        return f"{ts.year} Q{(ts.month - 1) // 3 + 1}"
    return ts.strftime("%m.%Y")


def by_period(df: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    """Финансовые показатели и OTIF по периодам (месяц/квартал/год)."""
    done = completed(df)
    if done.empty:
        return pd.DataFrame(columns=["period", "label", "orders", "revenue", "total_cost", "profit", "margin", "otif"])
    rule = {"M": "MS", "Q": "QS", "Y": "YS"}[freq]
    grouped = done.set_index("order_date").resample(rule).agg(
        orders=("order_id", "count"), revenue=("revenue", "sum"), total_cost=("total_cost", "sum"),
        profit=("profit", "sum"), otif=("otif", "mean"))
    grouped = grouped[grouped["orders"] > 0].reset_index().rename(columns={"order_date": "period"})
    grouped["margin"] = grouped["profit"] / grouped["revenue"].where(grouped["revenue"] != 0) * 100
    grouped["otif"] = grouped["otif"] * 100
    grouped["label"] = grouped["period"].apply(lambda t: period_label(t, freq))
    return grouped


def cost_structure(df: pd.DataFrame) -> pd.DataFrame:
    done = completed(df)
    s = done[list(COST_COLUMNS)].sum().rename(index=COST_COLUMNS)
    return s.reset_index().rename(columns={"index": "category", 0: "amount"})
