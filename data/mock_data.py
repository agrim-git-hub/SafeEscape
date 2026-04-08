"""
mock_data.py — Synthetic City Data Generator for SafeEscape.

This module generates realistic synthetic city nodes and edges that
simulate an urban road network. Each node represents an intersection
or landmark, and each edge represents a road segment with associated
distance and safety attributes.

Usage:
    from data.mock_data import generate_city_nodes, generate_city_edges

Author: SafeEscape Team
"""

from __future__ import annotations

import random
import math
from typing import TypedDict


# ──────────────────────────────────────────────────────────────────────
# Type Definitions
# ──────────────────────────────────────────────────────────────────────

class CityNode(TypedDict):
    """Typed dictionary representing a single city node (intersection)."""
    id: str
    label: str
    x: float
    y: float
    zone: str


class CityEdge(TypedDict):
    """Typed dictionary representing a road segment between two nodes."""
    source: str
    target: str
    distance: float
    safety_rating: int  # 1 (dangerous) → 10 (very safe)


# ──────────────────────────────────────────────────────────────────────
# Zone Definitions
# ──────────────────────────────────────────────────────────────────────

ZONE_METADATA: dict[str, dict] = {
    "Residential": {
        "safety_range": (6, 10),
        "color": "#4CAF50",
        "description": "Low-traffic residential streets",
    },
    "Commercial": {
        "safety_range": (4, 8),
        "color": "#2196F3",
        "description": "Busy commercial / market areas",
    },
    "Industrial": {
        "safety_range": (2, 6),
        "color": "#FF9800",
        "description": "Industrial zones with heavy vehicles",
    },
    "Highway": {
        "safety_range": (1, 5),
        "color": "#F44336",
        "description": "High-speed highway corridors",
    },
    "Park": {
        "safety_range": (7, 10),
        "color": "#8BC34A",
        "description": "Green park zones — pedestrian-friendly",
    },
}

ZONE_NAMES: list[str] = list(ZONE_METADATA.keys())

# Landmark-style labels for realism
_LANDMARK_PREFIXES: list[str] = [
    "Main St", "Park Ave", "Station Rd", "Market Sq", "Lake View",
    "Temple Ln", "College Rd", "Ring Rd", "MG Road", "Gandhi Chowk",
    "Nehru Nagar", "Sector", "Phase", "Block", "Cross Rd",
    "Hill View", "River Side", "Tech Park", "Old Town", "New Colony",
]


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────

def generate_city_nodes(
    num_nodes: int = 30,
    grid_size: float = 100.0,
    seed: int | None = 42,
) -> list[CityNode]:
    """
    Generate synthetic city intersection nodes on a 2-D plane.

    Each node is placed with slight random jitter around a loose grid
    to mimic realistic urban layouts rather than a perfect lattice.

    Args:
        num_nodes:  Total number of intersections to create.
        grid_size:  The bounding square size (0 → grid_size) for placement.
        seed:       Random seed for reproducibility (None for true random).

    Returns:
        A list of ``CityNode`` dicts, each containing id, label,
        (x, y) coordinates, and an assigned zone.
    """
    rng = random.Random(seed)

    cols = int(math.ceil(math.sqrt(num_nodes)))
    spacing = grid_size / max(cols, 1)

    nodes: list[CityNode] = []
    for i in range(num_nodes):
        row, col = divmod(i, cols)
        # Add jitter so the layout feels organic, not robotic
        jitter_x = rng.uniform(-spacing * 0.3, spacing * 0.3)
        jitter_y = rng.uniform(-spacing * 0.3, spacing * 0.3)

        node: CityNode = {
            "id": f"N{i}",
            "label": f"{rng.choice(_LANDMARK_PREFIXES)} {i}",
            "x": round(col * spacing + jitter_x, 2),
            "y": round(row * spacing + jitter_y, 2),
            "zone": rng.choice(ZONE_NAMES),
        }
        nodes.append(node)

    return nodes


def generate_city_edges(
    nodes: list[CityNode],
    connectivity: float = 0.35,
    max_distance: float = 30.0,
    seed: int | None = 42,
) -> list[CityEdge]:
    """
    Generate road segments (edges) between nearby city nodes.

    An edge is created between two nodes if they are within
    ``max_distance`` Euclidean distance AND a random roll passes the
    ``connectivity`` threshold.  Safety ratings are derived from the
    zones of the two endpoint nodes.

    Args:
        nodes:         List of ``CityNode`` dicts from ``generate_city_nodes``.
        connectivity:  Probability (0-1) that an eligible pair gets an edge.
        max_distance:  Maximum Euclidean distance to consider a connection.
        seed:          Random seed for reproducibility.

    Returns:
        A list of ``CityEdge`` dicts with source, target, distance,
        and safety_rating fields.
    """
    rng = random.Random(seed)
    edges: list[CityEdge] = []
    seen: set[tuple[str, str]] = set()

    for i, src in enumerate(nodes):
        for j, dst in enumerate(nodes):
            if i >= j:
                continue

            dx = src["x"] - dst["x"]
            dy = src["y"] - dst["y"]
            dist = math.sqrt(dx * dx + dy * dy)

            if dist > max_distance:
                continue

            if rng.random() > connectivity:
                continue

            pair = (src["id"], dst["id"])
            if pair in seen:
                continue
            seen.add(pair)

            # Safety = average of both endpoint zone ranges + noise
            src_zone = ZONE_METADATA[src["zone"]]
            dst_zone = ZONE_METADATA[dst["zone"]]
            lo = min(src_zone["safety_range"][0], dst_zone["safety_range"][0])
            hi = max(src_zone["safety_range"][1], dst_zone["safety_range"][1])
            safety = rng.randint(lo, hi)

            edge: CityEdge = {
                "source": src["id"],
                "target": dst["id"],
                "distance": round(dist, 2),
                "safety_rating": safety,
            }
            edges.append(edge)

    return edges


def get_zone_metadata() -> dict[str, dict]:
    """Return a copy of zone metadata (colors, safety ranges, etc.)."""
    return dict(ZONE_METADATA)
