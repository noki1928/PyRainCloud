"""Quickstart from the business hypothesis; renders the images used in README and docs.

Run:  uv run python examples/quickstart.py   (or: python examples/quickstart.py)
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import pyraincloud as rc  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent
OUT = EXAMPLES.parent / "docs" / "images"  # pictures for README
PALETTE = ["#66c2a5", "#fc8d62", "#8da0cb"]


def make_data(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "group": ["Control"] * 30 + ["Treatment A"] * 30 + ["Treatment B"] * 30,
            "reaction_time": np.concatenate(
                [rng.normal(500, 50, 30), rng.normal(450, 60, 30), rng.normal(480, 55, 30)]
            ),
        }
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = make_data()

    # 1. Basic plot: one call
    fig, ax = rc.raincloud(data=df, x="group", y="reaction_time", random_state=0)
    fig.savefig(OUT / "01_basic.png", dpi=150)

    # 2. Customisation: palette, transparency, sizes, horizontal orientation
    fig, ax = rc.raincloud(
        data=df,
        x="group",
        y="reaction_time",
        orient="h",
        palette=PALETTE,
        cloud_alpha=0.6,
        cloud_width=0.9,
        point_size=4,
        point_alpha=0.8,
        box_width=0.2,
        random_state=0,
    )
    fig.savefig(OUT / "02_custom_horizontal.png", dpi=150)

    fig, ax = rc.raincloud(
        data=df, x="group", y="reaction_time", palette=PALETTE, add_boxes=False, random_state=0
    )
    fig.savefig(OUT / "02b_no_boxes.png", dpi=150)

    # 3. Further matplotlib customisation of the returned (fig, ax) + saving
    fig, ax = rc.raincloud(
        data=df,
        x="group",
        y="reaction_time",
        palette=PALETTE,
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
    fig.savefig(OUT / "03_annotated.png", dpi=150)
    # WBS T11: publication-ready result saved next to the example
    fig.savefig(EXAMPLES / "raincloud_plot.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(EXAMPLES / "raincloud_plot.png", dpi=300, bbox_inches="tight")
    plt.close("all")
    print(f"Saved images to {OUT} and {EXAMPLES}")


if __name__ == "__main__":
    main()
