"""
app.py — SafeEscape Streamlit Dashboard.

The main entry point for the SafeEscape application. Provides an
interactive dashboard where users can:

    1. Configure city parameters and the Safety-vs-Speed trade-off.
    2. Visualise the city road network with the optimal route highlighted.
    3. Review safety analytics (distributions, zone breakdowns, gauges).
    4. Inspect step-by-step A* algorithm logs for educational insight.

Run with:
    streamlit run app.py

Author: SafeEscape Team
"""

from __future__ import annotations

import streamlit as st

from data.mock_data import generate_city_nodes, generate_city_edges, ZONE_METADATA
from core.graph import CityGraph
from core.solver import AStarSolver
from utils.visualization import (
    plot_city_graph,
    plot_safety_histogram,
    plot_zone_safety_breakdown,
    plot_path_safety_profile,
    plot_cost_gauge,
)


# ──────────────────────────────────────────────────────────────────────
# Page Configuration
# ──────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SafeEscape — Smart Route Planner",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────
# Custom CSS for a polished look
# ──────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* ── Global ──────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ── Header banner ───────────────────────────────────────── */
    .hero-banner {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .hero-banner h1 {
        margin: 0;
        font-size: 2.2rem;
        background: linear-gradient(90deg, #FFD600, #FF6D00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-banner p {
        color: rgba(255,255,255,0.65);
        margin: 0.4rem 0 0 0;
        font-size: 1rem;
    }

    /* ── Metric cards ────────────────────────────────────────── */
    .metric-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        text-align: center;
    }
    .metric-card h3 {
        margin: 0;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: rgba(255,255,255,0.5);
    }
    .metric-card .value {
        font-size: 2rem;
        font-weight: 700;
        margin: 0.3rem 0;
    }
    .metric-card .sub {
        font-size: 0.75rem;
        color: rgba(255,255,255,0.4);
    }

    /* ── Log box ─────────────────────────────────────────────── */
    .log-line {
        font-family: 'Fira Code', 'Consolas', monospace;
        font-size: 0.82rem;
        padding: 3px 0;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        color: rgba(255,255,255,0.78);
    }

    /* ── Sidebar polish ──────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0E1117 0%, #1a1f2e 100%);
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #FFD600;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# Hero Banner
# ──────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero-banner">
    <h1>🛡️ SafeEscape</h1>
    <p>AI-Powered Safe Route Planning — Balancing Speed and Safety with A*</p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# Sidebar — Parameters
# ──────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuration")

    st.subheader("City Parameters")
    num_nodes = st.slider(
        "Number of Intersections",
        min_value=10, max_value=60, value=30, step=5,
        help="Total intersections (nodes) in the synthetic city.",
    )
    connectivity = st.slider(
        "Road Connectivity",
        min_value=0.1, max_value=0.8, value=0.35, step=0.05,
        help="Probability that two nearby intersections are connected.",
    )
    seed = st.number_input(
        "Random Seed",
        min_value=0, max_value=9999, value=42,
        help="Seed for reproducible city generation.",
    )

    st.divider()
    st.subheader("🎯 Safety vs Speed")
    safety_lambda = st.slider(
        "Safety Lambda (λ)",
        min_value=0.0, max_value=1.0, value=0.5, step=0.05,
        help=(
            "λ = 0 → Shortest path (ignores safety).  \n"
            "λ = 1 → Safest path (ignores distance)."
        ),
    )

    # Visual feedback on lambda
    if safety_lambda < 0.3:
        st.info("⚡ **Speed Priority** — finding the shortest route.")
    elif safety_lambda > 0.7:
        st.success("🛡️ **Safety Priority** — avoiding dangerous roads.")
    else:
        st.warning("⚖️ **Balanced** — blending speed and safety.")

    st.divider()
    st.subheader("📍 Route Selection")

# ──────────────────────────────────────────────────────────────────────
# Build Graph
# ──────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="🏗️ Generating city map…")
def build_city(n: int, conn: float, s: int) -> CityGraph:
    """Generate city data, build and cache the entire CityGraph object."""
    nodes = generate_city_nodes(num_nodes=n, seed=s)
    edges = generate_city_edges(nodes, connectivity=conn, seed=s)
    return CityGraph(nodes, edges)


city_graph = build_city(num_nodes, connectivity, seed)

# ── Source / Destination selectors (in sidebar) ─────────────
all_ids = city_graph.get_all_node_ids()

with st.sidebar:
    start_node = st.selectbox(
        "Start Node",
        options=all_ids,
        index=0,
        format_func=lambda n: f"{n} — {city_graph.get_node_data(n)['label']}",
    )
    goal_node = st.selectbox(
        "Goal Node",
        options=all_ids,
        index=min(len(all_ids) - 1, len(all_ids) // 2),
        format_func=lambda n: f"{n} — {city_graph.get_node_data(n)['label']}",
    )

    run_search = st.button("🔍 Find Route", type="primary", use_container_width=True)

    st.divider()
    st.caption(
        f"Graph: **{city_graph.num_nodes}** nodes · "
        f"**{city_graph.num_edges}** edges"
    )

# ──────────────────────────────────────────────────────────────────────
# Run A* Solver
# ──────────────────────────────────────────────────────────────────────

# Persist result in session state so it survives re-runs
if "result" not in st.session_state:
    st.session_state.result = None

if run_search:
    if start_node == goal_node:
        st.error("⚠️ Start and Goal nodes must be different.")
    else:
        solver = AStarSolver(city_graph)
        st.session_state.result = solver.solve(
            start_node, goal_node, safety_lambda
        )

result = st.session_state.result

# ──────────────────────────────────────────────────────────────────────
# Main Content — Tabs
# ──────────────────────────────────────────────────────────────────────

tab_map, tab_analytics, tab_logs = st.tabs([
    "🗺️  Map View",
    "📊  Safety Analytics",
    "📋  Algorithm Logs",
])

# ── Tab 1: Map View ──────────────────────────────────────────
with tab_map:
    path = result.path if result and result.success else None

    if result and result.success:
        # Metric cards row
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>Total Cost</h3>
                <div class="value" style="color:#FFD600">{result.total_cost:.2f}</div>
                <div class="sub">composite (λ={safety_lambda})</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>Distance</h3>
                <div class="value" style="color:#29B6F6">{result.total_distance:.1f} km</div>
                <div class="sub">Euclidean sum</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            safety_color = "#66BB6A" if result.avg_safety >= 5 else "#FF5252"
            st.markdown(f"""
            <div class="metric-card">
                <h3>Avg Safety</h3>
                <div class="value" style="color:{safety_color}">{result.avg_safety:.1f}/10</div>
                <div class="sub">along route</div>
            </div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>Nodes Explored</h3>
                <div class="value" style="color:#CE93D8">{result.nodes_explored}</div>
                <div class="sub">{result.execution_ms:.1f} ms</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("")  # spacer

    map_title = "City Road Network" + (
        f"  —  Route: {' → '.join(path)}" if path else ""
    )
    fig_map = plot_city_graph(city_graph, path=path, title=map_title)
    st.plotly_chart(fig_map, use_container_width=True, key="main_map")

    if result and not result.success:
        st.error(
            f"⛔ No route found from **{start_node}** to **{goal_node}**. "
            "Try increasing road connectivity or choosing different nodes."
        )

# ── Tab 2: Safety Analytics ──────────────────────────────────
with tab_analytics:
    st.subheader("Network-Wide Safety Analysis")

    fig_hist = plot_safety_histogram(city_graph)
    fig_zone = plot_zone_safety_breakdown(city_graph)

    col_hist, col_zone = st.columns(2)
    with col_hist:
        st.plotly_chart(fig_hist, use_container_width=True, key="hist")
    with col_zone:
        st.plotly_chart(fig_zone, use_container_width=True, key="zone")

    if result and result.success:
        st.divider()
        st.subheader("Route-Specific Analytics")

        st.plotly_chart(
            plot_cost_gauge(
                result.total_cost,
                result.total_distance,
                result.avg_safety,
            ),
            use_container_width=True,
        )

        st.plotly_chart(
            plot_path_safety_profile(city_graph, result.path),
            use_container_width=True,
        )
    else:
        st.info("Run a search to see route-specific analytics.")

    # Zone legend
    st.divider()
    st.subheader("Zone Reference")
    zone_cols = st.columns(len(ZONE_METADATA))
    for col, (zone, meta) in zip(zone_cols, ZONE_METADATA.items()):
        with col:
            st.markdown(
                f"<div style='text-align:center'>"
                f"<span style='display:inline-block;width:16px;height:16px;"
                f"background:{meta['color']};border-radius:50%;'></span>"
                f"<br><b>{zone}</b><br>"
                f"<span style='font-size:0.75rem;color:rgba(255,255,255,0.5)'>"
                f"Safety: {meta['safety_range'][0]}–{meta['safety_range'][1]}"
                f"</span></div>",
                unsafe_allow_html=True,
            )

# ── Tab 3: Algorithm Logs ────────────────────────────────────
with tab_logs:
    st.subheader("A* Step-by-Step Execution Log")

    if result and result.logs:
        st.caption(
            f"**{result.nodes_explored}** nodes explored in "
            f"**{result.execution_ms:.1f} ms**  ·  "
            f"λ = {safety_lambda}"
        )

        # Batch ALL log lines into a single HTML block for performance
        log_html = "\n".join(
            f'<div class="log-line">{line}</div>' for line in result.logs
        )
        st.markdown(log_html, unsafe_allow_html=True)
    else:
        st.info(
            "Click **🔍 Find Route** in the sidebar to run the A* "
            "algorithm and see step-by-step logs here."
        )

    # Educational explanation
    with st.expander("📖 How A* Works", expanded=False):
        st.markdown("""
### A* Search Algorithm

A* is a **best-first graph search algorithm** that finds the least-cost
path from a start node to a goal node.

#### Key Formulas

| Symbol | Meaning |
|--------|---------|
| $g(n)$ | Actual cost from **start** to node $n$ |
| $h(n)$ | Heuristic estimate from $n$ to **goal** (Euclidean distance) |
| $f(n)$ | $g(n) + h(n)$ — the priority score |

#### SafeEscape Composite Cost

In SafeEscape, each edge has both a **distance** and a **safety rating**.  
The composite cost blends them using a parameter **λ** (lambda):

$$
\\text{cost}(u, v) = (1 - \\lambda) \\cdot \\text{distance} + \\lambda \\cdot (10 - \\text{safety})
$$

- **λ = 0** → Pure shortest path (ignores safety)
- **λ = 1** → Pure safest path (ignores distance)
- **0 < λ < 1** → A balanced trade-off

#### Why A*?

- **Optimal**: Guaranteed to find the best path when the heuristic is *admissible*.
- **Efficient**: Explores far fewer nodes than Dijkstra's algorithm by using the heuristic.
- **Flexible**: The composite cost function makes it easy to encode multi-objective preferences.
        """)

# ──────────────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────────────

st.divider()
st.markdown(
    "<div style='text-align:center;color:rgba(255,255,255,0.25);font-size:0.8rem'>"
    "SafeEscape v1.0 — Built with Streamlit · NetworkX · Plotly · A*"
    "</div>",
    unsafe_allow_html=True,
)
