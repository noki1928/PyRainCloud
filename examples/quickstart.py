"""Quickstart from the business hypothesis as a plain script (no notebook needed).

Run:  uv run python examples/quickstart.py   (or: python examples/quickstart.py)

Saves examples/raincloud_plot.pdf and .png. The step-by-step notebook with the
same example is examples/quickstart.ipynb; it also renders the README images.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import pyraincloud as rc

EXAMPLES = Path(__file__).resolve().parent

rng = np.random.default_rng(42)
df = pd.DataFrame(
    {
        "group": ["Control"] * 30 + ["Treatment A"] * 30 + ["Treatment B"] * 30,
        "reaction_time": np.concatenate(
            [rng.normal(500, 50, 30), rng.normal(450, 60, 30), rng.normal(480, 55, 30)]
        ),
    }
)

fig, ax = rc.raincloud(
    data=df,
    x="group",
    y="reaction_time",
    orient="v",
    palette=["#66c2a5", "#fc8d62", "#8da0cb"],
    cloud_alpha=0.5,
    cloud_width=0.8,
    point_size=3,
    point_alpha=0.6,
    random_state=0,
)

ax.set_title("Reaction Time by Treatment Group", fontsize=14, fontweight="bold")
ax.set_xlabel("Treatment Group", fontsize=12)
ax.set_ylabel("Reaction Time (ms)", fontsize=12)
ax.plot([0, 0, 1, 1], [612, 620, 620, 612], color="black", linewidth=1)
ax.annotate("p < 0.05", xy=(0.5, 622), ha="center", va="bottom")
ax.grid(axis="y", alpha=0.3)

# WBS T11: publication-ready result saved next to the example
for name in ("raincloud_plot.pdf", "raincloud_plot.png"):
    fig.savefig(EXAMPLES / name, dpi=300, bbox_inches="tight")
print(f"Saved raincloud_plot.pdf/.png to {EXAMPLES}")

plt.show()  # the library never calls show() itself
