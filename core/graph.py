"""
graph.py — Weighted City Graph Builder for SafeEscape.

This module wraps NetworkX to construct a weighted, undirected graph
from synthetic city data.  Each edge carries two weights:

    • **distance** — Euclidean distance between intersections (km).
    • **safety_rating** — Integer score from 1 (dangerous) to 10 (safe).

A composite "cost" is calculated on demand using a tuneable *safety_lambda*
so the A* solver can seamlessly blend shortest-path and safest-path objectives.

Usage:
    from core.graph import CityGraph
    cg = CityGraph(nodes, edges)
    cost = cg.composite_cost("N0", "N5", safety_lambda=0.5)

Author: SafeEscape Team
"""

from __future__ import annotations

import math
from typing import Any

import networkx as nx

from data.mock_data import CityNode, CityEdge


class CityGraph:
    """
    Builds and manages a NetworkX graph representing a city road network.

    Attributes:
        graph (nx.Graph):  The underlying undirected graph.
        positions (dict):  Node-id → (x, y) mapping for visualisation.
    """

    def __init__(
        self,
        nodes: list[CityNode],
        edges: list[CityEdge],
    ) -> None:
        """
        Initialise a CityGraph from raw node and edge data.

        Args:
            nodes: List of city-node dicts (id, label, x, y, zone).
            edges: List of city-edge dicts (source, target, distance, safety_rating).
        """
        self.graph: nx.Graph = nx.Graph()
        self.positions: dict[str, tuple[float, float]] = {}
        self._node_data: dict[str, CityNode] = {}

        # ── Add nodes ──────────────────────────────────────────────
        for node in nodes:
            nid = node["id"]
            self.graph.add_node(
                nid,
                label=node["label"],
                zone=node["zone"],
            )
            self.positions[nid] = (node["x"], node["y"])
            self._node_data[nid] = node

        # ── Add edges ──────────────────────────────────────────────
        for edge in edges:
            self.graph.add_edge(
                edge["source"],
                edge["target"],
                distance=edge["distance"],
                safety_rating=edge["safety_rating"],
            )

    # ──────────────────────────────────────────────────────────
    # Cost helpers
    # ──────────────────────────────────────────────────────────

    def composite_cost(
        self,
        u: str,
        v: str,
        safety_lambda: float = 0.5,
    ) -> float:
        """
        Compute a blended traversal cost for edge (u, v).

        The formula balances *distance* and *danger* using ``safety_lambda``:

            cost = (1 − λ) · distance  +  λ · (10 − safety_rating)

        • λ = 0  → pure shortest path (ignores safety).
        • λ = 1  → pure safest path (ignores distance).

        Args:
            u:             Source node id.
            v:             Target node id.
            safety_lambda: Blending factor in [0, 1].

        Returns:
            The composite cost as a float.

        Raises:
            nx.NetworkXError: If the edge (u, v) does not exist.
        """
        data: dict[str, Any] = self.graph.edges[u, v]
        distance: float = data["distance"]
        safety: int = data["safety_rating"]

        # Convert safety to a "danger" cost: higher is worse
        danger = 10 - safety

        cost = (1 - safety_lambda) * distance + safety_lambda * danger
        return cost

    def heuristic(self, u: str, v: str) -> float:
        """
        Euclidean distance heuristic for A*.

        This is *admissible* — it never over-estimates the true
        shortest-path distance — ensuring A* optimality.

        Args:
            u: Source node id.
            v: Target node id.

        Returns:
            Straight-line Euclidean distance between u and v.
        """
        x1, y1 = self.positions[u]
        x2, y2 = self.positions[v]
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    # ──────────────────────────────────────────────────────────
    # Accessors
    # ──────────────────────────────────────────────────────────

    def get_node_data(self, node_id: str) -> CityNode:
        """Return the raw CityNode dict for a given node id."""
        return self._node_data[node_id]

    def get_edge_data(self, u: str, v: str) -> dict[str, Any]:
        """Return the edge attribute dict for edge (u, v)."""
        return dict(self.graph.edges[u, v])

    def get_all_node_ids(self) -> list[str]:
        """Return a sorted list of all node ids in the graph."""
        return sorted(self.graph.nodes)

    def get_neighbors(self, node_id: str) -> list[str]:
        """Return a list of node ids adjacent to ``node_id``."""
        return list(self.graph.neighbors(node_id))

    def get_edge_safety(self, u: str, v: str) -> int:
        """Return the safety rating for edge (u, v)."""
        return self.graph.edges[u, v]["safety_rating"]

    def get_edge_distance(self, u: str, v: str) -> float:
        """Return the distance for edge (u, v)."""
        return self.graph.edges[u, v]["distance"]

    @property
    def num_nodes(self) -> int:
        """Total number of nodes in the graph."""
        return self.graph.number_of_nodes()

    @property
    def num_edges(self) -> int:
        """Total number of edges in the graph."""
        return self.graph.number_of_edges()

    def __repr__(self) -> str:
        return (
            f"CityGraph(nodes={self.num_nodes}, edges={self.num_edges})"
        )
