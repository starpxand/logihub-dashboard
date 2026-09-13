"""Разметка дашборда."""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html

from .data import PERIODS

CARGO_OPTIONS = ["Электроника", "Продукты питания", "Стройматериалы", "Одежда и обувь", "Мебель", "Медикаменты"]
REGION_OPTIONS = ["Хабаровский край", "Приморский край", "Амурская область", "Сахалинская область", "Еврейская АО"]


def card(title: str, body, subtitle: str | None = None, extra=None) -> dbc.Card:
    head = [html.Div([html.H5(title, className="card-title-lh"),
                      html.Div(subtitle, className="card-subtitle-lh") if subtitle else None]), extra]
    return dbc.Card(dbc.CardBody([html.Div(head, className="card-head-lh"), body]), className="lh-card")


def header() -> html.Header:
    return html.Header(className="lh-header", children=dbc.Container(fluid=True, children=[
        html.Div(className="lh-brand", children=[
            html.Img(src="/assets/logo.svg", className="lh-logo"),
            html.Div([html.H1("ЛогиХаб · Аналитика логистики"),
                      html.P("OTIF и финансовые показатели процесса управления логистикой · вариант 15")]),
        ]),
        html.Div(id="dataset-info", className="lh-dataset"),
    ]))


def upload_panel() -> dcc.Upload:
    return dcc.Upload(id="upload-data", multiple=False, className="lh-upload", children=html.Div([
        html.Div("⤒", className="lh-upload-icon"),
        html.Div([html.B("Перетащите CSV-файл сюда"), " или ", html.Span("выберите на компьютере", className="lh-link")]),
        html.Div("Выгрузка заказов ЛогиХаба (logistics_orders.csv), кодировка UTF-8", className="lh-hint"),
    ]))


def filters() -> dbc.Row:
    return dbc.Row(className="g-3 lh-filters", children=[
        dbc.Col(md=2, children=[html.Label("Период анализа"),
                                dcc.Dropdown(id="period", options=[{"label": v, "value": k} for k, v in PERIODS.items()],
                                             value="M", clearable=False)]),
        dbc.Col(md=3, children=[html.Label("Даты"),
                                dcc.DatePickerRange(id="date-range", display_format="DD.MM.YYYY",
                                                    first_day_of_week=1, className="lh-dates")]),
        dbc.Col(md=4, children=[html.Label("Категории груза"),
                                dcc.Dropdown(id="cargo", options=CARGO_OPTIONS, multi=True,
                                             placeholder="Все категории")]),
        dbc.Col(md=3, children=[html.Label("Регионы доставки"),
                                dcc.Dropdown(id="regions", options=REGION_OPTIONS, multi=True,
                                             placeholder="Все регионы")]),
    ])


def kpi_table() -> dash_table.DataTable:
    return dash_table.DataTable(
        id="table-kpi", page_size=12, sort_action="native", style_as_list_view=True,
        columns=[
            {"name": "Период", "id": "label"},
            {"name": "Заказов", "id": "orders", "type": "numeric"},
            {"name": "Выручка, ₽", "id": "revenue", "type": "numeric", "format": {"specifier": ",.0f"}},
            {"name": "Расходы, ₽", "id": "total_cost", "type": "numeric", "format": {"specifier": ",.0f"}},
            {"name": "Прибыль, ₽", "id": "profit", "type": "numeric", "format": {"specifier": ",.0f"}},
            {"name": "Рентабельность, %", "id": "margin", "type": "numeric", "format": {"specifier": ".1f"}},
            {"name": "OTIF, %", "id": "otif", "type": "numeric", "format": {"specifier": ".1f"}},
        ],
        style_header={"backgroundColor": "#f8fafc", "fontWeight": 700, "color": "#64748b",
                      "textTransform": "uppercase", "fontSize": 11, "border": "none"},
        style_cell={"fontFamily": "Inter, Segoe UI, Arial", "fontSize": 13, "padding": "10px 12px",
                    "textAlign": "right", "border": "none", "borderBottom": "1px solid #e2e8f0"},
        style_cell_conditional=[{"if": {"column_id": "label"}, "textAlign": "left", "fontWeight": 600}],
        style_data_conditional=[
            {"if": {"filter_query": "{profit} < 0", "column_id": "profit"}, "color": "#e5484d"},
            {"if": {"filter_query": "{otif} >= 90", "column_id": "otif"}, "color": "#16a34a", "fontWeight": 700},
            {"if": {"filter_query": "{otif} < 75", "column_id": "otif"}, "color": "#e5484d", "fontWeight": 700},
        ],
    )


def build_layout() -> html.Div:
    return html.Div(className="lh-page", children=[
        dcc.Store(id="store-data"),
        header(),
        dbc.Container(fluid=True, className="lh-body", children=[
            dbc.Row(className="g-3", children=[
                dbc.Col(lg=4, children=card("1. Данные", html.Div([upload_panel(), html.Div(id="upload-status")]),
                                            "Файл загружается из веб-интерфейса, а не из кода")),
                dbc.Col(lg=8, children=card("2. Фильтры", filters(),
                                            "Период, даты, категории груза и регионы применяются ко всем элементам")),
            ]),
            html.Section(className="lh-section", children=[
                html.H2("3. Текущие показатели"), html.Div(id="kpi-indicators", className="lh-kpis")]),
            html.H2("4. Графики и таблица", className="lh-h2"),
            dbc.Row(className="g-3", children=[
                dbc.Col(lg=8, children=card("Динамика доходов и расходов", dcc.Graph(id="graph-timeseries"),
                                            "Линейный график по выбранному периоду; наведите курсор для деталей")),
                dbc.Col(lg=4, children=card("Структура расходов", dcc.Graph(id="graph-costs"), "Доли категорий затрат")),
            ]),
            dbc.Row(className="g-3 mt-1", children=[
                dbc.Col(lg=6, children=card("Распределение прибыли по заказам", dcc.Graph(id="graph-profit-hist"),
                                            "Гистограмма с разбивкой по типу транспорта")),
                dbc.Col(lg=6, children=card(
                    "Корреляция прибыли", dcc.Graph(id="graph-scatter"), "График рассеяния, выберите параметр",
                    extra=dcc.Dropdown(id="scatter-x", clearable=False, value="distance_km", className="lh-mini-dd",
                                       options=[{"label": "от расстояния", "value": "distance_km"},
                                                {"label": "от веса груза", "value": "weight_kg"},
                                                {"label": "от выручки", "value": "revenue"},
                                                {"label": "от расходов", "value": "total_cost"}]))),
            ]),
            dbc.Row(className="g-3 mt-1", children=[
                dbc.Col(lg=7, children=card("OTIF по периодам и релизы продукта", dcc.Graph(id="graph-otif"),
                                            "Главный KPI продукта, цель – 90 %")),
                dbc.Col(lg=5, children=card("Выручка и OTIF по регионам", dcc.Graph(id="graph-regions"),
                                            "Сравнение направлений доставки")),
            ]),
            dbc.Row(className="g-3 mt-1", children=[
                dbc.Col(width=12, children=card("Ключевые финансовые показатели за выбранный период", kpi_table(),
                                          "Сортировка – по клику на заголовок столбца")),
            ]),
            html.Footer("ЛогиХаб © 2026 · учебный проект · тестовые данные сгенерированы для варианта 15",
                        className="lh-footer"),
        ]),
    ])
