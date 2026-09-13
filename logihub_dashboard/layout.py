"""Разметка дашборда."""
from dash import dcc, html


def graph_block(title: str, graph_id: str) -> html.Div:
    return html.Div([html.H3(title), dcc.Graph(id=graph_id)])


def build_layout() -> html.Div:
    return html.Div([
        html.H1("ЛогиХаб – аналитический дашборд"),
        html.Div(id="kpi-indicators"),
        graph_block("Динамика доходов и расходов", "graph-timeseries"),
        graph_block("Структура расходов", "graph-costs"),
        graph_block("Распределение прибыли", "graph-profit-hist"),
        graph_block("Корреляция прибыли", "graph-scatter"),
        html.H3("Ключевые финансовые показатели"),
        html.Div(id="table-kpi"),
    ])
