"""Точка входа: python app.py"""
from dash import Dash

from logihub_dashboard.layout import build_layout

app = Dash(__name__, title="ЛогиХаб – дашборд")
app.layout = build_layout()
server = app.server

if __name__ == "__main__":
    app.run(debug=True)
