"""
visualization.py — Graph & Path Visualisation Utilities for SafeEscape.

Provides Plotly-based interactive visualisations for:
    • Full city graph rendering with zone-coloured nodes.
    • Highlighted A* path overlay in a distinct colour.
    • Safety analytics charts (histograms, bar charts, gauges).

All functions return Plotly ``Figure`` objects so they integrate
seamlessly with ``st.plotly_chart()`` in the Streamlit dashboard.

Usage:
    from utils.visualization import plot_city_graph, plot_safety_histogram
    fig = plot_city_graph(city_graph, path=["N0", "N3", "N12"])
    st.plotly_chart(fig)

Author: SafeEscape Team
"""

from __future__ import annotations

from typing import Optional

import plotly.graph_objects as go
import plotly.express as px

from core.graph import CityGraph
from data.mock_data import ZONE_METADATA


# ──────────────────────────────────────────────────────────────────────
# Colour Palette
# ──────────────────────────────────────────────────────────────────────

_PATH_COLOR = "#FFD600"          # Bright gold for the route
_PATH_EDGE_COLOR = "#FFD600"
_DEFAULT_EDGE_COLOR = "rgba(150,150,150,0.25)"
_BG_COLOR = "#0E1117"           # Matches Streamlit dark theme
_GRID_COLOR = "rgba(255,255,255,0.04)"


# ──────────────────────────────────────────────────────────────────────
# Map View
# ──────────────────────────────────────────────────────────────────────

def plot_city_graph(
    city_graph: CityGraph,
    path: Optional[list[str]] = None,
    title: str = "City Road Network",
) -> go.Figure:
    """
    Render the full city graph as an interactive Plotly scatter plot.

    Nodes are coloured by zone, edges by safety rating, and (if provided)
    the A* path is overlaid in bright gold.

    Args:
        city_graph: The ``CityGraph`` to visualise.
        path:       Optional ordered list of node ids for the route overlay.
        title:      Plot title.

    Returns:
        A ``plotly.graph_objects.Figure`` ready for display.
    """
    fig = go.Figure()
    G = city_graph.graph
    pos = city_graph.positions

    # Build a set of path edges for quick lookup
    path_edge_set: set[tuple[str, str]] = set()
    if path and len(path) >= 2:
        for i in range(len(path) - 1):
            path_edge_set.add((path[i], path[i + 1]))
            path_edge_set.add((path[i + 1], path[i]))

    # ── Draw ALL edges as a SINGLE batched trace ──────────────
    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    for u, v, data in G.edges(data=True):
        if (u, v) in path_edge_set:
            continue  # skip path edges, drawn separately
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig.add_trace(go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1.2, color="rgba(150,150,150,0.3)"),
        hoverinfo="none",
        showlegend=False,
    ))

    # ── Draw path edges as a SINGLE batched trace ─────────────
    if path and len(path) >= 2:
        path_x: list[float | None] = []
        path_y: list[float | None] = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            path_x.extend([x0, x1, None])
            path_y.extend([y0, y1, None])

        fig.add_trace(go.Scatter(
            x=path_x,
            y=path_y,
            mode="lines",
            line=dict(width=4.5, color=_PATH_EDGE_COLOR),
            hoverinfo="none",
            showlegend=False,
        ))

    # ── Draw nodes ────────────────────────────────────────────
    zone_groups: dict[str, list[str]] = {}
    for nid in G.nodes:
        zone = G.nodes[nid]["zone"]
        zone_groups.setdefault(zone, []).append(nid)

    for zone, nids in zone_groups.items():
        meta = ZONE_METADATA.get(zone, {})
        color = meta.get("color", "#888")
        xs = [pos[n][0] for n in nids]
        ys = [pos[n][1] for n in nids]
        labels = [G.nodes[n].get("label", n) for n in nids]
        texts = [
            f"<b>{G.nodes[n].get('label', n)}</b><br>"
            f"Zone: {zone}<br>ID: {n}"
            for n in nids
        ]

        # Make path nodes slightly larger
        sizes = [
            14 if (path and n in path) else 9
            for n in nids
        ]
        border_colors = [
            _PATH_COLOR if (path and n in path) else color
            for n in nids
        ]

        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="markers+text",
            marker=dict(
                size=sizes,
                color=color,
                line=dict(width=2, color=border_colors),
                opacity=0.95,
            ),
            text=labels,
            textposition="top center",
            textfont=dict(size=8, color="rgba(255,255,255,0.7)"),
            hoverinfo="text",
            hovertext=texts,
            name=zone,
        ))

    # ── Layout ────────────────────────────────────────────────
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color="white")),
        plot_bgcolor=_BG_COLOR,
        paper_bgcolor=_BG_COLOR,
        xaxis=dict(
            showgrid=True, gridcolor=_GRID_COLOR,
            zeroline=False, showticklabels=False,
        ),
        yaxis=dict(
            showgrid=True, gridcolor=_GRID_COLOR,
            zeroline=False, showticklabels=False,
        ),
        legend=dict(
            font=dict(color="white"),
            bgcolor="rgba(0,0,0,0.4)",
            bordercolor="rgba(255,255,255,0.1)",
        ),
        margin=dict(l=20, r=20, t=50, b=20),
        height=600,
    )
    return fig


# ──────────────────────────────────────────────────────────────────────
# Safety Analytics Charts
# ──────────────────────────────────────────────────────────────────────

def plot_safety_histogram(city_graph: CityGraph) -> go.Figure:
    """
    Create a histogram of edge safety ratings across the entire graph.

    Args:
        city_graph: The ``CityGraph`` to analyse.

    Returns:
        A Plotly ``Figure`` with the safety distribution.
    """
    ratings = [
        data["safety_rating"]
        for _, _, data in city_graph.graph.edges(data=True)
    ]

    fig = px.histogram(
        x=ratings,
        nbins=10,
        title="Distribution of Edge Safety Ratings",
        labels={"x": "Safety Rating (1–10)", "count": "Number of Roads"},
        color_discrete_sequence=["#26C6DA"],
    )
    fig.update_layout(
        plot_bgcolor=_BG_COLOR,
        paper_bgcolor=_BG_COLOR,
        font=dict(color="white"),
        bargap=0.1,
        xaxis=dict(dtick=1),
    )
    return fig


def plot_zone_safety_breakdown(city_graph: CityGraph) -> go.Figure:
    """
    Bar chart showing average safety rating per zone.

    Args:
        city_graph: The ``CityGraph`` to analyse.

    Returns:
        A Plotly ``Figure`` grouped by zone.
    """
    G = city_graph.graph
    zone_safety: dict[str, list[int]] = {}

    for u, v, data in G.edges(data=True):
        for nid in (u, v):
            zone = G.nodes[nid]["zone"]
            zone_safety.setdefault(zone, []).append(data["safety_rating"])

    zones = sorted(zone_safety.keys())
    averages = [
        sum(zone_safety[z]) / len(zone_safety[z]) for z in zones
    ]
    colors = [ZONE_METADATA.get(z, {}).get("color", "#888") for z in zones]

    fig = go.Figure(go.Bar(
        x=zones,
        y=averages,
        marker_color=colors,
        text=[f"{a:.1f}" for a in averages],
        textposition="outside",
    ))
    fig.update_layout(
        title="Average Safety Rating by Zone",
        plot_bgcolor=_BG_COLOR,
        paper_bgcolor=_BG_COLOR,
        font=dict(color="white"),
        yaxis=dict(title="Avg Safety (1–10)", range=[0, 11]),
        xaxis=dict(title="Zone"),
    )
    return fig


def plot_path_safety_profile(
    city_graph: CityGraph,
    path: list[str],
) -> go.Figure:
    """
    Line chart showing the safety rating of each edge along the route.

    Useful for identifying weak-spots (dangerous stretches) on the path.

    Args:
        city_graph: The ``CityGraph``.
        path:       Ordered list of node ids.

    Returns:
        A Plotly ``Figure`` with per-edge safety profile.
    """
    if len(path) < 2:
        fig = go.Figure()
        fig.update_layout(title="No path to display")
        return fig

    edge_labels: list[str] = []
    safeties: list[int] = []
    distances: list[float] = []

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_labels.append(f"{u}→{v}")
        safeties.append(city_graph.get_edge_safety(u, v))
        distances.append(city_graph.get_edge_distance(u, v))

    fig = go.Figure()

    # Safety line
    fig.add_trace(go.Scatter(
        x=edge_labels, y=safeties,
        mode="lines+markers",
        name="Safety Rating",
        line=dict(color="#66BB6A", width=3),
        marker=dict(size=9),
    ))

    # Danger threshold
    fig.add_hline(
        y=4, line_dash="dash",
        line_color="rgba(255,82,82,0.6)",
        annotation_text="Danger Threshold",
        annotation_font_color="rgba(255,82,82,0.8)",
    )

    fig.update_layout(
        title="Safety Profile Along Route",
        plot_bgcolor=_BG_COLOR,
        paper_bgcolor=_BG_COLOR,
        font=dict(color="white"),
        yaxis=dict(title="Safety Rating", range=[0, 11], dtick=1),
        xaxis=dict(title="Edge"),
        height=350,
    )
    return fig


def plot_cost_gauge(
    total_cost: float,
    total_distance: float,
    avg_safety: float,
) -> go.Figure:
    """
    Create a dashboard-style indicator with key route metrics.

    Args:
        total_cost:     Composite cost of the route.
        total_distance: Total Euclidean distance (km).
        avg_safety:     Average safety rating (1–10).

    Returns:
        A Plotly ``Figure`` with three gauge indicators.
    """
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=1, cols=3,
        specs=[[
            {"type": "indicator"},
            {"type": "indicator"},
            {"type": "indicator"},
        ]],
    )

    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=total_cost,
        title={"text": "Total Cost", "font": {"size": 14}},
        gauge=dict(
            axis=dict(range=[0, max(total_cost * 2, 50)]),
            bar=dict(color="#FFD600"),
            bgcolor="rgba(255,255,255,0.05)",
        ),
    ), row=1, col=1)

    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=total_distance,
        title={"text": "Distance (km)", "font": {"size": 14}},
        gauge=dict(
            axis=dict(range=[0, max(total_distance * 2, 100)]),
            bar=dict(color="#29B6F6"),
            bgcolor="rgba(255,255,255,0.05)",
        ),
    ), row=1, col=2)

    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=avg_safety,
        title={"text": "Avg Safety", "font": {"size": 14}},
        gauge=dict(
            axis=dict(range=[0, 10]),
            bar=dict(color="#66BB6A"),
            bgcolor="rgba(255,255,255,0.05)",
            threshold=dict(
                line=dict(color="red", width=2),
                thickness=0.75, value=4,
            ),
        ),
    ), row=1, col=3)

    fig.update_layout(
        paper_bgcolor=_BG_COLOR,
        font=dict(color="white"),
        height=250,
        margin=dict(l=30, r=30, t=40, b=20),
    )
    return fig
