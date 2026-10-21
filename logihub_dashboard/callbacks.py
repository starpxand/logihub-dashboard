"""Колбэки интерактивности дашборда."""
from __future__ import annotations

import io

import dash_bootstrap_components as dbc
import pandas as pd
from dash import ALL, Input, Output, State, ctx, html, no_update

from . import figures
from .data import (OTIF_TARGET, DataError, by_period, filter_orders, insights, kpis, parse_upload, prepare,
                   previous_window)


def _money(value: float) -> str:
    if abs(value) >= 1e6:
        return f"{value / 1e6:,.1f} млн ₽".replace(",", " ").replace(".", ",")
    return f"{value:,.0f} ₽".replace(",", " ")


def _pct(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace(".", ",") + " %"


def delta(now: float, before: float | None, kind: str) -> html.Span:
    """Изменение к прошлому периоду той же длины: kind «pp» – процентные пункты, «rel» – проценты."""
    if before is None:
        return html.Span("нет прошлого периода для сравнения", className="lh-delta lh-delta--none")
    d = now - before if kind == "pp" else ((now - before) / abs(before) * 100 if before else 0.0)
    unit = " п.п." if kind == "pp" else " %"
    arrow, tone = ("▲", "up") if d > 0.05 else ("▼", "down") if d < -0.05 else ("■", "flat")
    return html.Span([html.B(f"{arrow} {abs(d):.1f}".replace(".", ",") + unit), " к прошлому периоду"],
                     className=f"lh-delta lh-delta--{tone}")


def spark(values) -> html.Div:
    """Мини-тренд: последние 12 значений столбиками."""
    vals = [float(v) for v in list(values)[-12:]]
    if len(vals) < 2:
        return html.Div(className="lh-spark")
    lo, hi = min(vals), max(vals)
    return html.Div(className="lh-spark", title="тренд по периодам выборки", children=[
        html.I(style={"height": f"{18 + (v - lo) / (hi - lo or 1) * 82:.0f}%"}) for v in vals])


def indicator(title: str, value: str, percent: float, target: str, color: str, change=None, trend=None) -> dbc.Card:
    return dbc.Card(className="lh-kpi", children=dbc.CardBody([
        html.Div(title, className="lh-kpi-title"),
        html.Div([html.Div(value, className="lh-kpi-value"), trend], className="lh-kpi-row"),
        change,
        dbc.Progress(value=max(0, min(percent, 100)), color=color, className="lh-progress"),
        html.Div(target, className="lh-kpi-target"),
    ]))


def register(app) -> None:
    @app.callback(
        Output("store-data", "data"), Output("upload-status", "children"),
        Output("date-range", "min_date_allowed"), Output("date-range", "max_date_allowed"),
        Output("date-range", "start_date"), Output("date-range", "end_date"),
        Input("upload-data", "contents"), State("upload-data", "filename"),
        prevent_initial_call=True,
    )
    def load_file(contents, filename):
        try:
            df = parse_upload(contents, filename)
        except DataError as exc:
            return no_update, dbc.Alert(str(exc), color="danger", className="lh-alert"), *[no_update] * 4
        start, end = df["order_date"].min().date(), df["order_date"].max().date()
        status = dbc.Alert([html.B(filename), f" – загружено {len(df):,} заказов за {start:%d.%m.%Y}–{end:%d.%m.%Y}"
                            .replace(",", " ")], color="success", className="lh-alert")
        return df.to_json(orient="split", date_format="iso"), status, start, end, start, end

    @app.callback(
        Output("date-range", "start_date", allow_duplicate=True), Output("date-range", "end_date", allow_duplicate=True),
        Output("cargo", "value"), Output("regions", "value"),
        Input({"type": "quick", "range": ALL}, "n_clicks"), Input("reset-filters", "n_clicks"),
        State("date-range", "min_date_allowed"), State("date-range", "max_date_allowed"),
        prevent_initial_call=True,
    )
    def quick_range(_quick, _reset, lo, hi):
        """Быстрый выбор периода от последней даты в файле; «Сбросить» – весь период и все категории и регионы."""
        if not lo or not hi or not ctx.triggered_id:
            return no_update, no_update, no_update, no_update
        lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
        if ctx.triggered_id == "reset-filters":
            return lo.date(), hi.date(), [], []
        months = {"all": None, "12M": 12, "Q": 3, "M": 1}[ctx.triggered_id["range"]]
        start = lo if months is None else max(lo, hi - pd.DateOffset(months=months) + pd.Timedelta(days=1))
        return start.date(), hi.date(), no_update, no_update

    @app.callback(
        Output("regions", "value", allow_duplicate=True), Output("graph-regions", "clickData"),
        Input("graph-regions", "clickData"), State("regions", "value"),
        prevent_initial_call=True,
    )
    def region_click(click, current):
        """Перекрёстная фильтрация: щелчок по столбцу региона добавляет его в фильтр или убирает."""
        if not click:
            return no_update, no_update
        region = click["points"][0]["y"]
        current = list(current or [])
        # clickData сбрасывается – иначе повторный щелчок по тому же столбцу не дойдёт до колбэка
        return ([r for r in current if r != region] if region in current else [*current, region]), None

    @app.callback(
        Output("kpi-indicators", "children"), Output("graph-timeseries", "figure"), Output("graph-costs", "figure"),
        Output("graph-profit-hist", "figure"), Output("graph-scatter", "figure"), Output("graph-otif", "figure"),
        Output("graph-regions", "figure"), Output("table-kpi", "data"), Output("dataset-info", "children"),
        Output("insights", "children"),
        Input("store-data", "data"), Input("period", "value"), Input("date-range", "start_date"),
        Input("date-range", "end_date"), Input("cargo", "value"), Input("regions", "value"),
        Input("scatter-x", "value"),
    )
    def update(data, freq, start, end, cargo, regions, scatter_x):
        if not data:
            placeholder = figures.empty()
            hint = html.Div("Загрузите файл с данными, чтобы увидеть показатели", className="lh-empty")
            return hint, *[placeholder] * 6, [], "Данные не загружены", []
        df = prepare(pd.read_json(io.StringIO(data), orient="split"))
        view = filter_orders(df, start, end, cargo, regions)
        k = kpis(view)
        win = previous_window(df, start, end)
        p = kpis(filter_orders(df, *win, cargo, regions)) if win else None
        prev = (lambda key: p[key] if p and p["orders"] else None)
        per = by_period(view, freq)
        cards = dbc.Row(className="g-3", children=[
            dbc.Col(md=6, xl=3, children=indicator("OTIF", _pct(k["otif"]), k["otif"] / OTIF_TARGET * 100,
                                                   f"цель {OTIF_TARGET:.0f} % · выполнено на {k['otif'] / OTIF_TARGET * 100:.0f} %",
                                                   "success" if k["otif"] >= OTIF_TARGET else "warning",
                                                   delta(k["otif"], prev("otif"), "pp"), spark(per["otif"]))),
            dbc.Col(md=6, xl=3, children=indicator("Выручка", _money(k["revenue"]), 100,
                                                   f"заказов: {k['orders']:,}".replace(",", " "), "primary",
                                                   delta(k["revenue"], prev("revenue"), "rel"), spark(per["revenue"]))),
            dbc.Col(md=6, xl=3, children=indicator("Прибыль", _money(k["profit"]), k["margin"] / 40 * 100,
                                                   f"рентабельность {_pct(k['margin'])} (ориентир 40 %)", "info",
                                                   delta(k["profit"], prev("profit"), "rel"), spark(per["profit"]))),
            dbc.Col(md=6, xl=3, children=indicator("В срок / в полном объёме", f"{k['on_time']:.0f} / {k['in_full']:.0f} %",
                                                   k["on_time"], f"отмены: {_pct(k['cancel_rate'])}", "secondary",
                                                   delta(k["on_time"], prev("on_time"), "pp"), spark(per["orders"]))),
        ])
        table = per[["label", "orders", "revenue", "total_cost", "profit", "margin", "otif"]]
        notes = [html.Div([html.Span(className=f"lh-dot lh-dot--{kind}"), text], className="lh-insight")
                 for kind, text in insights(view, freq)]
        notes = [html.Div("Выводы по выборке", className="lh-insights-title"), *notes] if notes else []
        info = f"{len(view):,} из {len(df):,} заказов в выборке".replace(",", " ")
        return (cards, figures.revenue_cost_timeseries(view, freq), figures.cost_pie(view),
                figures.profit_histogram(view), figures.profit_scatter(view, scatter_x), figures.otif_trend(view, freq),
                figures.region_bars(filter_orders(df, start, end, cargo, None), regions),
                table.round(2).to_dict("records"), info, notes)
