"""Точка входа дашборда «ЛогиХаб».

    python app.py            # http://127.0.0.1:8050
"""
from __future__ import annotations

import os

import dash_bootstrap_components as dbc
from dash import Dash

from logihub_dashboard.callbacks import register
from logihub_dashboard.layout import build_layout


def create_app() -> Dash:
    app = Dash(__name__, title="ЛогиХаб – аналитика логистики", external_stylesheets=[
        dbc.themes.BOOTSTRAP, "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap"])
    app.layout = build_layout()
    register(app)
    return app


app = create_app()
server = app.server

if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8050")),
            debug=os.getenv("DEBUG", "0") == "1")
