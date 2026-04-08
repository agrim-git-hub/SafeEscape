# 🛡️ SafeEscape — AI-Powered Safe Route Planning

**SafeEscape** is a modular Python application that uses the **A\* search algorithm** to find optimal escape routes in a city, balancing **speed** and **safety**. Built with **Streamlit**, **NetworkX**, and **Plotly**.

## 📁 Project Structure

```
SafeEscape/
├── app.py                 # Streamlit entry point (UI & Layout)
├── core/
│   ├── graph.py           # CityGraph: weighted graph with safety costs
│   └── solver.py          # A* algorithm with tuneable safety_lambda
├── data/
│   └── mock_data.py       # Synthetic city node/edge generation
├── utils/
│   └── visualization.py   # Plotly-based graph & chart rendering
└── requirements.txt       # Python dependencies
```

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the dashboard
streamlit run app.py
```

## ⚙️ Key Features

| Feature | Description |
|---------|-------------|
| **A\* Pathfinding** | From-scratch implementation with step-by-step logging |
| **Safety Lambda (λ)** | Slider to blend shortest path (λ=0) and safest path (λ=1) |
| **Interactive Map** | Plotly scatter plot with zone-coloured nodes and route overlay |
| **Safety Analytics** | Histograms, zone breakdowns, route safety profiles, gauges |
| **Algorithm Logs** | Full A\* execution trace for educational review |

## 🧮 Core Algorithm

The composite edge cost used by A\* is:

```
cost(u, v) = (1 − λ) · distance + λ · (10 − safety_rating)
```

- **λ = 0** → Pure shortest path
- **λ = 1** → Pure safest path
- **0 < λ < 1** → Balanced trade-off

## 📦 Dependencies

- Python 3.10+
- Streamlit ≥ 1.30
- NetworkX ≥ 3.2
- Plotly ≥ 5.18
- Matplotlib ≥ 3.8
- NumPy ≥ 1.26

## 👥 Authors

SafeEscape Team — College Submission Project
