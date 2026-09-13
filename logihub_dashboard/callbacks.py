"""Колбэки интерактивности дашборда."""
from __future__ import annotations

import io

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, html, no_update

from . import figures
from .data import OTIF_TARGET, DataError, by_period, filter_orders, kpis, parse_upload, prepare


def _money(value: float) -> str:
    if abs(value) >= 1e6:
        return f"{value / 1e6:,.1f} млн ₽".replace(",", " ").replace(".", ",")
    return f"{value:,.0f} ₽".replace(",", " ")


def indicator(title: str, value: str, percent: float, target: str, color: str) -> dbc.Card:
    return dbc.Card(className="lh-kpi", children=dbc.CardBody([
        html.Div(title, className="lh-kpi-title"),
        html.Div(value, className="lh-kpi-value"),
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
        Output("kpi-indicators", "children"), Output("graph-timeseries", "figure"), Output("graph-costs", "figure"),
        Output("graph-profit-hist", "figure"), Output("graph-scatter", "figure"), Output("graph-otif", "figure"),
        Output("graph-regions", "figure"), Output("table-kpi", "data"), Output("dataset-info", "children"),
        Input("store-data", "data"), Input("period", "value"), Input("date-range", "start_date"),
        Input("date-range", "end_date"), Input("cargo", "value"), Input("regions", "value"),
        Input("scatter-x", "value"),
    )
    def update(data, freq, start, end, cargo, regions, scatter_x):
        if not data:
            placeholder = figures.empty()
            hint = html.Div("Загрузите файл с данными, чтобы увидеть показатели", className="lh-empty")
            return hint, *[placeholder] * 6, [], "Данные не загружены"
        df = prepare(pd.read_json(io.StringIO(data), orient="split"))
        view = filter_orders(df, start, end, cargo, regions)
        k = kpis(view)
        cards = dbc.Row(className="g-3", children=[
            dbc.Col(md=6, xl=3, children=indicator("OTIF", f"{k['otif']:.1f} %", k["otif"] / OTIF_TARGET * 100,
                                                   f"цель {OTIF_TARGET:.0f} % · выполнено на {k['otif'] / OTIF_TARGET * 100:.0f} %",
                                                   "success" if k["otif"] >= OTIF_TARGET else "warning")),
            dbc.Col(md=6, xl=3, children=indicator("Выручка", _money(k["revenue"]), 100,
                                                   f"заказов: {k['orders']:,}".replace(",", " "), "primary")),
            dbc.Col(md=6, xl=3, children=indicator("Прибыль", _money(k["profit"]), k["margin"] / 40 * 100,
                                                   f"рентабельность {k['margin']:.1f} % (ориентир 40 %)", "info")),
            dbc.Col(md=6, xl=3, children=indicator("В срок / в полном объёме", f"{k['on_time']:.0f} / {k['in_full']:.0f} %",
                                                   k["on_time"], f"отмены: {k['cancel_rate']:.1f} %", "secondary")),
        ])
        table = by_period(view, freq)[["label", "orders", "revenue", "total_cost", "profit", "margin", "otif"]]
        info = f"{len(view):,} из {len(df):,} заказов в выборке".replace(",", " ")
        return (cards, figures.revenue_cost_timeseries(view, freq), figures.cost_pie(view),
                figures.profit_histogram(view), figures.profit_scatter(view, scatter_x), figures.otif_trend(view, freq),
                figures.region_bars(view), table.round(2).to_dict("records"), info)
