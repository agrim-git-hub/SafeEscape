"""
solver.py — A* Pathfinding Solver for SafeEscape.

Implements a clean, from-scratch A* search algorithm over a ``CityGraph``.
The solver uses a tuneable ``safety_lambda`` parameter so users can
seamlessly shift between *shortest* and *safest* route priorities.

Key concepts:
    • g(n) — actual cost from the start node to node n.
    • h(n) — heuristic estimate from node n to the goal (Euclidean distance).
    • f(n) = g(n) + h(n) — the priority used by the open-set min-heap.

The composite edge cost is computed by ``CityGraph.composite_cost``.

Usage:
    from core.solver import AStarSolver
    solver = AStarSolver(city_graph)
    result = solver.solve("N0", "N29", safety_lambda=0.6)
    print(result.path, result.total_cost)

Author: SafeEscape Team
"""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from typing import Optional

from core.graph import CityGraph


# ──────────────────────────────────────────────────────────────────────
# Result Container
# ──────────────────────────────────────────────────────────────────────

@dataclass
class AStarResult:
    """
    Immutable container for A* search results.

    Attributes:
        path:            Ordered list of node ids from start to goal.
        total_cost:      Sum of composite costs along the path.
        total_distance:  Sum of raw distances along the path.
        avg_safety:      Average safety rating of edges on the path.
        nodes_explored:  Number of nodes popped from the open set.
        execution_ms:    Wall-clock time of the search in milliseconds.
        logs:            Step-by-step log entries for the Algorithm Logs tab.
        success:         Whether a valid path was found.
    """
    path: list[str] = field(default_factory=list)
    total_cost: float = 0.0
    total_distance: float = 0.0
    avg_safety: float = 0.0
    nodes_explored: int = 0
    execution_ms: float = 0.0
    logs: list[str] = field(default_factory=list)
    success: bool = False


# ──────────────────────────────────────────────────────────────────────
# A* Solver
# ──────────────────────────────────────────────────────────────────────

class AStarSolver:
    """
    A* pathfinding solver over a :class:`CityGraph`.

    The solver is stateless — each call to :meth:`solve` is independent,
    making it safe to reuse across multiple queries.
    """

    def __init__(self, city_graph: CityGraph) -> None:
        """
        Initialise the solver with a reference to the city graph.

        Args:
            city_graph: A fully constructed ``CityGraph`` instance.
        """
        self._graph: CityGraph = city_graph

    def solve(
        self,
        start: str,
        goal: str,
        safety_lambda: float = 0.5,
    ) -> AStarResult:
        """
        Run A* search from ``start`` to ``goal``.

        Args:
            start:         Source node id.
            goal:          Destination node id.
            safety_lambda: Blending factor [0, 1].
                           0 = shortest path, 1 = safest path.

        Returns:
            An ``AStarResult`` containing the optimal path, costs,
            exploration stats, and step-by-step logs.
        """
        result = AStarResult()
        graph = self._graph
        logs = result.logs

        # ── Validation ────────────────────────────────────────────
        all_ids = set(graph.get_all_node_ids())
        if start not in all_ids:
            logs.append(f"❌ Start node '{start}' not found in graph.")
            return result
        if goal not in all_ids:
            logs.append(f"❌ Goal node '{goal}' not found in graph.")
            return result

        logs.append(
            f"🚀 A* search initiated: {start} → {goal}  "
            f"(λ = {safety_lambda:.2f})"
        )
        t0 = time.perf_counter()

        # ── Data structures ───────────────────────────────────────
        # open_set: min-heap of (f_score, counter, node_id)
        # counter breaks ties deterministically
        counter: int = 0
        open_set: list[tuple[float, int, str]] = []

        g_score: dict[str, float] = {start: 0.0}
        came_from: dict[str, Optional[str]] = {start: None}
        closed: set[str] = set()

        h_start = graph.heuristic(start, goal)
        heapq.heappush(open_set, (h_start, counter, start))
        counter += 1

        logs.append(
            f"   h({start}) = {h_start:.2f}  |  Open set size: 1"
        )

        # ── Main loop ─────────────────────────────────────────────
        while open_set:
            f_current, _, current = heapq.heappop(open_set)
            result.nodes_explored += 1

            if current in closed:
                continue
            closed.add(current)

            logs.append(
                f"📍 Exploring {current}  |  "
                f"f = {f_current:.2f}  |  "
                f"g = {g_score[current]:.2f}  |  "
                f"Explored: {result.nodes_explored}"
            )

            # ── Goal reached ──────────────────────────────────────
            if current == goal:
                elapsed = (time.perf_counter() - t0) * 1000
                result.execution_ms = round(elapsed, 3)
                result.path = self._reconstruct_path(came_from, goal)
                result.total_cost = g_score[goal]
                result.success = True

                # Compute distance & safety stats along the path
                result.total_distance, result.avg_safety = (
                    self._path_stats(result.path)
                )

                logs.append(
                    f"✅ Goal reached!  Cost: {result.total_cost:.2f}  |  "
                    f"Distance: {result.total_distance:.2f}  |  "
                    f"Avg Safety: {result.avg_safety:.1f}  |  "
                    f"Time: {result.execution_ms:.1f} ms"
                )
                return result

            # ── Expand neighbors ──────────────────────────────────
            for neighbor in graph.get_neighbors(current):
                if neighbor in closed:
                    continue

                edge_cost = graph.composite_cost(
                    current, neighbor, safety_lambda
                )
                tentative_g = g_score[current] + edge_cost

                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    h_val = graph.heuristic(neighbor, goal)
                    f_val = tentative_g + h_val

                    heapq.heappush(open_set, (f_val, counter, neighbor))
                    counter += 1

                    logs.append(
                        f"   ↳ Relaxed {current}→{neighbor}  "
                        f"g={tentative_g:.2f}  h={h_val:.2f}  f={f_val:.2f}"
                    )

        # ── No path found ─────────────────────────────────────────
        elapsed = (time.perf_counter() - t0) * 1000
        result.execution_ms = round(elapsed, 3)
        logs.append(
            f"⛔ No path found from {start} to {goal} "
            f"after exploring {result.nodes_explored} nodes "
            f"({result.execution_ms:.1f} ms)."
        )
        return result

    # ──────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _reconstruct_path(
        came_from: dict[str, Optional[str]],
        current: str,
    ) -> list[str]:
        """
        Trace back from *current* to the start using the came_from map.

        Args:
            came_from: Mapping of node → predecessor.
            current:   The goal node to trace back from.

        Returns:
            Ordered path from start to goal.
        """
        path: list[str] = [current]
        while came_from.get(current) is not None:
            current = came_from[current]  # type: ignore[assignment]
            path.append(current)
        path.reverse()
        return path

    def _path_stats(
        self,
        path: list[str],
    ) -> tuple[float, float]:
        """
        Compute total distance and average safety along a path.

        Args:
            path: Ordered list of node ids.

        Returns:
            (total_distance, average_safety_rating)
        """
        if len(path) < 2:
            return 0.0, 0.0

        total_dist = 0.0
        total_safety = 0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            total_dist += self._graph.get_edge_distance(u, v)
            total_safety += self._graph.get_edge_safety(u, v)

        num_edges = len(path) - 1
        avg_safety = total_safety / num_edges if num_edges else 0.0
        return round(total_dist, 2), round(avg_safety, 2)
