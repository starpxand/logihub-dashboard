"""Построение графиков Plotly для дашборда."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .data import OTIF_TARGET, PERIODS, by_period, completed, cost_structure

NAVY, BLUE, ORANGE, AMBER, GREEN, RED, GREY = "#0b1b3f", "#2f5bea", "#ff8a3d", "#ffb547", "#16a34a", "#e5484d", "#94a3b8"
PALETTE = [NAVY, BLUE, ORANGE, AMBER, "#7c93f5", GREY]
RELEASES = [("2024-01-01", "v1.0"), ("2025-02-01", "v1.5"), ("2026-02-01", "v2.0")]


def _style(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=10, r=10, t=46, b=10),
        font=dict(family="Inter, Segoe UI, Arial", size=12, color="#0f172a"),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0, title_text=""),
        hoverlabel=dict(bgcolor="white", font_size=12), separators=", ",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#eef2f7")
    return fig


def empty(message: str = "Загрузите CSV-файл, чтобы построить график") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=14, color=GREY), x=0.5, y=0.5,
                       xref="paper", yref="paper")
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _style(fig)


def revenue_cost_timeseries(df: pd.DataFrame, freq: str) -> go.Figure:
    data = by_period(df, freq)
    if data.empty:
        return empty("Нет данных за выбранный период")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["label"], y=data["revenue"] / 1e6, name="Доходы (выручка)", mode="lines+markers",
                             line=dict(color=BLUE, width=3), hovertemplate="%{x}<br>Выручка: %{y:.2f} млн ₽<extra></extra>"))
    fig.add_trace(go.Scatter(x=data["label"], y=data["total_cost"] / 1e6, name="Расходы", mode="lines+markers",
                             line=dict(color=ORANGE, width=3), hovertemplate="%{x}<br>Расходы: %{y:.2f} млн ₽<extra></extra>"))
    fig.add_trace(go.Bar(x=data["label"], y=data["profit"] / 1e6, name="Прибыль", marker_color="rgba(22,163,74,.25)",
                         hovertemplate="%{x}<br>Прибыль: %{y:.2f} млн ₽<extra></extra>"))
    fig.update_yaxes(title_text="млн ₽")
    return _style(fig)


def cost_pie(df: pd.DataFrame) -> go.Figure:
    data = cost_structure(df)
    if data["amount"].sum() == 0:
        return empty("Нет расходов за выбранный период")
    fig = px.pie(data, names="category", values="amount", hole=0.55, color_discrete_sequence=PALETTE)
    fig.update_traces(textposition="outside", textinfo="percent+label",
                      hovertemplate="%{label}<br>%{value:,.0f} ₽ (%{percent})<extra></extra>")
    fig.update_layout(showlegend=False)
    return _style(fig, 340)


def profit_histogram(df: pd.DataFrame) -> go.Figure:
    done = completed(df)
    if done.empty:
        return empty("Нет данных")
    fig = px.histogram(done, x="profit", nbins=40, color="transport_type", color_discrete_sequence=PALETTE,
                       labels={"profit": "Прибыль с заказа, ₽", "transport_type": "Транспорт", "count": "Заказов"})
    fig.add_vline(x=0, line_color=RED, line_dash="dash", annotation_text="убыток / прибыль")
    fig.update_layout(bargap=0.05, barmode="stack", yaxis_title="Число заказов")
    return _style(fig, 340)


def profit_scatter(df: pd.DataFrame, x_metric: str = "distance_km") -> go.Figure:
    done = completed(df)
    if done.empty:
        return empty("Нет данных")
    sample = done.sample(min(len(done), 2500), random_state=15)
    labels = {"distance_km": "Расстояние, км", "weight_kg": "Вес груза, кг", "revenue": "Выручка, ₽",
              "total_cost": "Расходы, ₽", "profit": "Прибыль, ₽", "transport_type": "Транспорт"}
    fig = px.scatter(sample, x=x_metric, y="profit", color="transport_type", opacity=0.6,
                     color_discrete_sequence=PALETTE, labels=labels,
                     hover_data={"order_id": True, "client": True, "cargo_type": True, "region": True,
                                 "revenue": ":,.0f", "total_cost": ":,.0f"})
    corr = done[[x_metric, "profit"]].corr().iloc[0, 1]
    fig.add_annotation(text=f"Корреляция Пирсона r = {corr:.2f}", x=0.99, y=0.97, xref="paper", yref="paper", xanchor="right",
                       showarrow=False, bgcolor="white", bordercolor="#e2e8f0", font=dict(size=12))
    return _style(fig, 380)


def otif_trend(df: pd.DataFrame, freq: str) -> go.Figure:
    data = by_period(df, freq)
    if data.empty:
        return empty("Нет данных")
    fig = go.Figure(go.Scatter(x=data["period"], y=data["otif"], mode="lines+markers", name="OTIF",
                               line=dict(color=NAVY, width=3), fill="tozeroy", fillcolor="rgba(47,91,234,.08)",
                               customdata=data["label"], hovertemplate="%{customdata}<br>OTIF: %{y:.1f} %<extra></extra>"))
    fig.add_hline(y=OTIF_TARGET, line_dash="dot", line_color=ORANGE, annotation_text=f"цель {OTIF_TARGET:.0f} %")
    lo, hi = data["period"].min(), data["period"].max()
    for start, name in RELEASES:
        x = pd.Timestamp(start)
        if lo <= x <= hi:
            fig.add_vline(x=x, line_dash="dash", line_color=GREY)
            fig.add_annotation(x=x, y=99, text=name, showarrow=False, yanchor="top", xanchor="left",
                               font=dict(color=NAVY, size=12))
    fig.update_yaxes(range=[50, 100], title_text="%")
    fig.update_xaxes(tickformat={"M": "%m.%Y", "Q": "Q%q %Y", "Y": "%Y"}.get(freq, "%m.%Y"))
    return _style(fig, 300)


def region_bars(df: pd.DataFrame) -> go.Figure:
    done = completed(df)
    if done.empty:
        return empty("Нет данных")
    data = done.groupby("region").agg(revenue=("revenue", "sum"), otif=("otif", "mean")).reset_index()
    data = data.sort_values("revenue")
    fig = go.Figure(go.Bar(x=data["revenue"] / 1e6, y=data["region"], orientation="h", marker_color=BLUE,
                           text=[f"OTIF {v * 100:.0f} %" for v in data["otif"]], textposition="inside",
                           insidetextanchor="end", textfont=dict(color="white"),
                           hovertemplate="%{y}<br>Выручка: %{x:.1f} млн ₽<extra></extra>"))
    fig.update_xaxes(title_text="Выручка, млн ₽", showgrid=True, gridcolor="#eef2f7")
    return _style(fig, 300)


def period_title(freq: str) -> str:
    return PERIODS.get(freq, "Месяц").lower()
