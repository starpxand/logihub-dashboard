import base64
from pathlib import Path

import pandas as pd
import pytest

from logihub_dashboard import figures
from logihub_dashboard.data import DataError, by_period, cost_structure, filter_orders, kpis, parse_upload, prepare

CSV = Path(__file__).resolve().parents[1] / "data" / "logistics_orders.csv"


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return prepare(pd.read_csv(CSV))


def as_upload(text: str) -> str:
    return "data:text/csv;base64," + base64.b64encode(text.encode("utf-8")).decode()


def test_parse_upload_roundtrip():
    frame = parse_upload(as_upload(CSV.read_text(encoding="utf-8")), "logistics_orders.csv")
    assert len(frame) > 5000
    assert pd.api.types.is_datetime64_any_dtype(frame["order_date"])


def test_parse_upload_rejects_wrong_extension():
    with pytest.raises(DataError):
        parse_upload(as_upload("a,b\n1,2"), "orders.xlsx")


def test_parse_upload_reports_missing_columns():
    with pytest.raises(DataError, match="нет столбцов"):
        parse_upload(as_upload("order_id,revenue\nLH-1,100"), "bad.csv")


def test_kpis_match_release_history(df):
    for release, expected in {"v1.0": 72, "v1.5": 81, "v2.0": 87}.items():
        assert round(kpis(df[df["release"] == release])["otif"]) == expected


def test_profit_equals_revenue_minus_cost(df):
    k = kpis(df)
    assert k["profit"] == pytest.approx(k["revenue"] - k["cost"], rel=1e-9)


@pytest.mark.parametrize("freq, periods", [("Y", 3), ("Q", 11), ("M", 32)])
def test_by_period_granularity(df, freq, periods):
    assert len(by_period(df, freq)) == periods


def test_filters_narrow_selection(df):
    view = filter_orders(df, "2026-01-01", "2026-03-31", ["Медикаменты"], ["Приморский край"])
    assert not view.empty
    assert set(view["cargo_type"]) == {"Медикаменты"}
    assert view["order_date"].between("2026-01-01", "2026-03-31").all()


def test_cost_structure_sums_to_total(df):
    done = df[df["status"] != "Отменён"]
    assert cost_structure(df)["amount"].sum() == pytest.approx(done["total_cost"].sum())


def test_figures_build_without_errors(df):
    for fig in (figures.revenue_cost_timeseries(df, "Q"), figures.cost_pie(df), figures.profit_histogram(df),
                figures.profit_scatter(df, "weight_kg"), figures.otif_trend(df, "M"), figures.region_bars(df),
                figures.revenue_cost_timeseries(df.iloc[0:0], "M")):
        assert fig.to_dict()["data"] is not None


def test_previous_window_same_length(df):
    from logihub_dashboard.data import previous_window
    ps, pe = previous_window(df, "2026-07-01", "2026-08-31")
    assert (pe - ps).days + 1 == 62 and pe == pd.Timestamp("2026-06-30")
    assert previous_window(df, df["order_date"].min(), "2026-08-31") is None


def test_insights_name_best_and_worst_period(df):
    from logihub_dashboard.data import insights
    items = insights(df, "Q")
    kinds = [k for k, _ in items]
    assert "good" in kinds and "bad" in kinds
    assert any("OTIF" in t for _, t in items)
    assert not any("," in t.split("–")[1].split(":")[0] for k, t in items if k != "info"), "метка периода не должна портиться"


def test_otif_axis_tick_step_matches_grouping(df):
    assert figures.otif_trend(df, "Y").layout.xaxis.dtick == "M12"
    assert figures.otif_trend(df, "Q").layout.xaxis.dtick == "M3"
