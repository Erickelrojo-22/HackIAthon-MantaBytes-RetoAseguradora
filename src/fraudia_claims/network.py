from __future__ import annotations

import math
from typing import Any

from fraudia_claims.agent_tools import get_relationship_network
from fraudia_claims.config import DEFAULT_DB_PATH


def graph_payload(limit: int = 60, db_path=DEFAULT_DB_PATH) -> dict[str, list[dict[str, Any]]]:
    return get_relationship_network(limit=limit, db_path=db_path)


def build_plotly_figure(payload: dict[str, list[dict[str, Any]]]):
    try:
        import plotly.graph_objects as go
    except Exception:
        return None

    nodes = payload["nodes"]
    edges = payload["edges"]
    if not nodes:
        return None

    node_ids = [node["id"] for node in nodes]
    radius_by_type = {"Siniestro": 1.0, "Asegurado": 1.75, "Proveedor": 2.5}
    positions = {}
    for idx, node in enumerate(nodes):
        angle = 2 * math.pi * idx / max(1, len(nodes))
        radius = radius_by_type.get(node.get("tipo"), 2.0)
        positions[node["id"]] = (radius * math.cos(angle), radius * math.sin(angle))

    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    for edge in edges:
        if edge["source"] not in positions or edge["target"] not in positions:
            continue
        x0, y0 = positions[edge["source"]]
        x1, y1 = positions[edge["target"]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    colors = {"Rojo": "#d62728", "Amarillo": "#f2c94c", "Verde": "#2ca02c"}
    symbols = {"Siniestro": "circle", "Asegurado": "diamond", "Proveedor": "square"}
    node_x = [positions[node_id][0] for node_id in node_ids]
    node_y = [positions[node_id][1] for node_id in node_ids]
    node_text = [
        f"{node['label']}<br>{node['tipo']}<br>{node.get('ramo', '')}<br>Score {node.get('score', '')}"
        for node in nodes
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=0.7, color="#9aa3af"),
            hoverinfo="none",
            name="relaciones",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            marker=dict(
                size=[18 if node["tipo"] == "Siniestro" else 14 for node in nodes],
                color=[colors.get(node.get("nivel"), "#6b7280") for node in nodes],
                symbol=[symbols.get(node.get("tipo"), "circle") for node in nodes],
                line=dict(width=1, color="#111827"),
            ),
            text=[node["label"] if node["tipo"] != "Siniestro" else "" for node in nodes],
            textposition="top center",
            hovertext=node_text,
            hoverinfo="text",
            name="nodos",
        )
    )
    fig.update_layout(
        height=650,
        showlegend=False,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="white",
    )
    return fig
