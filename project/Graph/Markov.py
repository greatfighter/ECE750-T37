import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx

# Create a directed graph
G = nx.DiGraph()

# Add nodes with scientific notations
nodes = {
    "M": ("Raw Metrics", "circle"),
    "Φ(M)": ("Feature Extraction", "circle"),
    "s": ("State", "circle"),
    "o": ("Observation", "circle"),
    "π(a|s)": ("Policy", "hexagon"),
    "a": ("Action", "diamond"),
    "s'": ("Next State", "circle"),
    "R(s,a)": ("Reward Function", "rectangle"),
    "P(s'|s,a)": ("Transition Dynamics", "rectangle"),
    "T(π)": ("Training Process", "rectangle"),
    "RL Models": ("RL Models (PPO, A2C, etc.)", "hexagon"),
    "Env": ("Environment", "diamond"),
}

# Add edges with relationships
edges = [
    ("M", "Φ(M)", "Extract"),
    ("Φ(M)", "s", "→"),
    ("s", "o", "Partial"),
    ("o", "π(a|s)", "Input"),
    ("π(a|s)", "a", "Action"),
    ("a", "Env", "Impact"),
    ("Env", "s'", "Update"),
    ("s'", "R(s,a)", "Feedback"),
    ("R(s,a)", "T(π)", "Optimize"),
    ("T(π)", "π(a|s)", "Improve Policy"),
    ("T(π)", "RL Models", "Train"),
    ("RL Models", "π(a|s)", "Enhance"),
    ("Env", "M", "Metrics"),
    ("s", "P(s'|s,a)", "Input State"),
    ("a", "P(s'|s,a)", "Input Action"),
    ("P(s'|s,a)", "s'", "Generate Next State"),
]

# Initialize the graph
pos = {
    "M": (0, 4.5), "Φ(M)": (1, 4), "s": (2, 3.5), "o": (3, 4),
    "π(a|s)": (4, 4), "a": (5, 3.5), "Env": (6, 4),
    "s'": (6, 3), "R(s,a)": (6, 2), "P(s'|s,a)": (4, 2.5),
    "T(π)": (3, 2), "RL Models": (2, 3),
}

# Draw graph
plt.figure(figsize=(16, 10))

# Node styles by shape
shape_mapping = {"circle": "o", "hexagon": "h", "rectangle": "s", "diamond": "d"}
for node, (label, shape) in nodes.items():
    nx.draw_networkx_nodes(
        G, pos, nodelist=[node], node_shape=shape_mapping[shape],
        node_color="lightblue" if shape == "circle" else
                    "lightgreen" if shape == "hexagon" else
                    "lightcoral" if shape == "rectangle" else
                    "gold", alpha=0.9, node_size=3000  # Smaller node size
    )

# Add edges
edge_colors = ["gray", "blue", "green", "orange", "purple"]  # Cycle through these
edge_labels = {}
for i, (u, v, label) in enumerate(edges):
    G.add_edge(u, v, label=label)
    nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], edge_color=edge_colors[i % len(edge_colors)], width=2, alpha=0.6)
    edge_labels[(u, v)] = label

# Add edge labels
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=20)

# Add labels
nx.draw_networkx_labels(G, pos, labels={node: node for node in G.nodes()}, font_size=20, font_weight="bold")

# Create a legend
legend_elements = [
    mpatches.Patch(color="lightblue", label="Circle: Metrics/States/Observations"),
    mpatches.Patch(color="lightgreen", label="Hexagon: Policies/Models"),
    mpatches.Patch(color="lightcoral", label="Rectangle: Training/Dynamics"),
    mpatches.Patch(color="gold", label="Diamond: Actions/Environment"),
]
plt.legend(handles=legend_elements, loc="lower center", bbox_to_anchor=(0.5, -0.1), ncol=2, frameon=False)

# Final touches
plt.title("Reinforcement Learning Training and Execution Workflow", fontsize=20)
plt.axis("off")
plt.show()
