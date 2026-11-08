"""Render the step-by-step screens for the user guide.

Every screen is produced by actually executing the code of a notebook cell and
drawing that code together with its real output (text, exception or figure),
in the style of a Jupyter cell.

Run:  uv run python docs/make_screens.py
"""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import tempfile
import textwrap
import traceback
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screens"

MONO = "DejaVu Sans Mono"
CODE_BG = "#f5f5f5"
CODE_EDGE = "#cfcfcf"
PROMPT_IN = "#303f9f"
PROMPT_OUT = "#d84315"
ERR_BG = "#fdecea"
FONT_PT = 9.5
LINE_IN = 0.205  # inches per text line
WIDTH_IN = 8.0


class Session:
    """A tiny notebook kernel: shared namespace, execution counter, captured output."""

    def __init__(self, workdir: Path):
        self.ns: dict = {}
        self.count = 0
        self.workdir = workdir

    def run(self, code: str):
        """Execute ``code``; return (stdout, last-expression repr, error text, figure png)."""
        self.count += 1
        plt.close("all")
        buf = io.StringIO()
        result = error = None
        lines = code.rstrip().splitlines()
        body, last = "\n".join(lines[:-1]), lines[-1]
        old = os.getcwd()
        os.chdir(self.workdir)
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                try:
                    compile(last, "<cell>", "eval")
                    is_expr = not last.startswith((" ", "\t", ")", "]", "}"))
                except SyntaxError:
                    is_expr = False
                if is_expr:
                    exec(body, self.ns)
                    value = eval(last, self.ns)
                    if value is not None and not isinstance(value, tuple):
                        result = value.to_string() if hasattr(value, "to_string") else repr(value)
                else:
                    exec(code, self.ns)
        except Exception as exc:  # noqa: BLE001 - shown to the user as a traceback
            tb = traceback.format_exception_only(type(exc), exc)
            error = "".join(tb).strip()
        finally:
            os.chdir(old)
        fig_png = None
        if plt.get_fignums():
            fig = plt.figure(plt.get_fignums()[-1])
            fig_png = self.workdir / f"_fig{self.count}.png"
            fig.savefig(fig_png, dpi=130)
        return buf.getvalue().rstrip(), result, error, fig_png


def _wrap(text: str, width: int = 92) -> list[str]:
    out: list[str] = []
    for line in text.splitlines() or [""]:
        out.extend(textwrap.wrap(line, width, replace_whitespace=False) or [""])
    return out


def render_cell(path: Path, n: int, code: str, stdout: str, result, error, fig_png) -> None:
    code_lines = code.rstrip().splitlines()
    text_out = [s for s in (stdout, result) if s]
    out_lines = _wrap("\n".join(text_out)) if text_out else []
    err_lines = _wrap(error) if error else []
    img = mpimg.imread(fig_png) if fig_png else None
    img_h = 0.0
    if img is not None:
        h, w = img.shape[:2]
        img_w = WIDTH_IN - 1.2
        img_h = img_w * h / w

    pad = 0.12
    code_h = len(code_lines) * LINE_IN + 2 * pad
    out_h = (len(out_lines) * LINE_IN + 2 * pad) if out_lines else 0
    err_h = (len(err_lines) * LINE_IN + 2 * pad) if err_lines else 0
    total = 0.15 + code_h + 0.1 + out_h + err_h + (img_h + 0.1 if img is not None else 0) + 0.1

    fig = plt.figure(figsize=(WIDTH_IN, total), dpi=150)
    fig.patch.set_facecolor("white")

    def y(inches_from_top: float) -> float:
        return 1 - inches_from_top / total

    def box(top: float, height: float, color: str, edge: str | None = None) -> None:
        ax = fig.add_axes([1.0 / WIDTH_IN, y(top + height), 1 - 1.1 / WIDTH_IN, height / total])
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_facecolor(color)
        for s in ax.spines.values():
            s.set_color(edge or color)

    top = 0.15
    box(top, code_h, CODE_BG, CODE_EDGE)
    fig.text(
        0.1 / WIDTH_IN, y(top + pad + 0.15), f"[{n}]:", family=MONO, size=FONT_PT, color=PROMPT_IN
    )
    for i, line in enumerate(code_lines):
        fig.text(1.1 / WIDTH_IN, y(top + pad + 0.15 + i * LINE_IN), line, family=MONO, size=FONT_PT)
    top += code_h + 0.1

    if out_lines:
        if result is not None:
            fig.text(
                0.1 / WIDTH_IN,
                y(top + pad + 0.15),
                f"[{n}]:",
                family=MONO,
                size=FONT_PT,
                color=PROMPT_OUT,
            )
        for i, line in enumerate(out_lines):
            fig.text(
                1.1 / WIDTH_IN, y(top + pad + 0.15 + i * LINE_IN), line, family=MONO, size=FONT_PT
            )
        top += out_h
    if err_lines:
        box(top, err_h, ERR_BG)
        for i, line in enumerate(err_lines):
            fig.text(
                1.1 / WIDTH_IN,
                y(top + pad + 0.15 + i * LINE_IN),
                line,
                family=MONO,
                size=FONT_PT,
                color="#b71c1c",
            )
        top += err_h
    if img is not None:
        ax = fig.add_axes(
            [1.0 / WIDTH_IN, y(top + img_h), (WIDTH_IN - 1.2) / WIDTH_IN, img_h / total]
        )
        ax.imshow(img)
        ax.axis("off")
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)


def render_terminal(path: Path, command: str, output: str) -> None:
    lines = [f"$ {command}"] + _wrap(output, 96)
    h = len(lines) * LINE_IN + 0.35
    fig = plt.figure(figsize=(WIDTH_IN, h), dpi=150)
    fig.patch.set_facecolor("#1e1e1e")
    for i, line in enumerate(lines):
        color = "#8ae234" if i == 0 else "#e0e0e0"
        fig.text(
            0.15 / WIDTH_IN,
            1 - (0.25 + i * LINE_IN) / h,
            line,
            family=MONO,
            size=FONT_PT,
            color=color,
        )
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)


CELLS: list[tuple[str, str]] = [
    (
        "01_import",
        """\
import pyraincloud as rc
print("PyRainCloud", rc.__version__)
help(rc.raincloud)""".replace(
            "help(rc.raincloud)", "print(rc.raincloud.__doc__.split('Parameters')[0].strip())"
        ),
    ),
    (
        "02_data",
        """\
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
df = pd.DataFrame({
    "group": ["Control"] * 30 + ["Treatment A"] * 30 + ["Treatment B"] * 30,
    "reaction_time": np.concatenate([rng.normal(500, 50, 30),
                                     rng.normal(450, 60, 30),
                                     rng.normal(480, 55, 30)]),
})
df.sample(6, random_state=1)""",
    ),
    (
        "03_basic",
        """\
fig, ax = rc.raincloud(data=df, x="group", y="reaction_time")""",
    ),
    (
        "04_custom_h",
        """\
palette = ["#66c2a5", "#fc8d62", "#8da0cb"]
fig, ax = rc.raincloud(
    data=df, x="group", y="reaction_time",
    orient="h", palette=palette,
    cloud_alpha=0.6, cloud_width=0.9,
    point_size=4, point_alpha=0.8, box_width=0.2,
    random_state=0,
)""",
    ),
    (
        "05_no_boxes",
        """\
fig, ax = rc.raincloud(data=df, x="group", y="reaction_time",
                       palette=palette, add_boxes=False, random_state=0)""",
    ),
    (
        "06_annotate",
        """\
fig, ax = rc.raincloud(data=df, x="group", y="reaction_time",
                       palette=palette, random_state=0)
ax.set_title("Reaction Time by Treatment Group", fontsize=14, fontweight="bold")
ax.set_xlabel("Treatment Group")
ax.set_ylabel("Reaction Time (ms)")
ax.plot([0, 0, 1, 1], [612, 620, 620, 612], color="black", linewidth=1)
ax.annotate("p < 0.05", xy=(0.5, 622), ha="center", va="bottom")""",
    ),
    (
        "07_savefig",
        """\
fig.savefig("raincloud_plot.pdf", dpi=300, bbox_inches="tight")
fig.savefig("raincloud_plot.png", dpi=300, bbox_inches="tight")
import os
for name in ("raincloud_plot.pdf", "raincloud_plot.png"):
    print(f"{name:20s} {os.path.getsize(name) / 1024:7.1f} KB")""",
    ),
    (
        "08_err_column",
        """\
fig, ax = rc.raincloud(data=df, x="condition", y="reaction_time")""",
    ),
    (
        "09_err_palette",
        """\
fig, ax = rc.raincloud(data=df, x="group", y="reaction_time",
                       palette=["#66c2a5", "#fc8d62"])""",
    ),
    (
        "10_warn_nan",
        """\
import warnings
df_nan = df.copy()
df_nan.loc[[0, 1, 35], "reaction_time"] = np.nan
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    fig, ax = rc.raincloud(data=df_nan, x="group", y="reaction_time")
for w in caught:
    print(f"{w.category.__name__}: {w.message}")""",
    ),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        session = Session(Path(tmp))
        for name, code in CELLS:
            stdout, result, error, fig_png = session.run(code)
            render_cell(OUT / f"{name}.png", session.count, code, stdout, result, error, fig_png)
            print(f"{name}: ok" + (f" (error: {error.splitlines()[-1]})" if error else ""))

    env = {**os.environ, "NO_COLOR": "1"}
    check = subprocess.run(
        ["uv", "run", "python", "-c", "import pyraincloud as rc; print(rc.__version__)"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    render_terminal(
        OUT / "00_install_check.png",
        'uv run python -c "import pyraincloud as rc; print(rc.__version__)"',
        check.stdout.strip(),
    )
    print("00_install_check: ok")


if __name__ == "__main__":
    main()
