#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import html
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.benchmarks import (  # noqa: E402
    ARCHITECTURE_ABLATION,
    LATENCY_PROFILE,
    PPO_RECOVERY,
    QUANTIZATION_RESULTS,
    REAL_TASK_RESULTS,
    SIM_RESULTS,
)

ASSETS = ROOT / "docs" / "assets"

COLORS = {
    "ink": "#1f2937",
    "muted": "#64748b",
    "grid": "#d7dee8",
    "blue": "#2563eb",
    "teal": "#0f766e",
    "orange": "#ea580c",
    "red": "#dc2626",
    "green": "#16a34a",
    "purple": "#7c3aed",
    "amber": "#d97706",
    "panel": "#f8fafc",
}


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def write_svg(path: Path, body: str, width: int = 1100, height: int = 620) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                '<style>text{font-family:Inter,Arial,sans-serif;fill:#1f2937}.title{font-weight:700;font-size:28px}.label{font-size:15px}.small{font-size:12px;fill:#64748b}.axis{stroke:#94a3b8;stroke-width:1}.grid{stroke:#d7dee8;stroke-width:1}.box{stroke:#334155;stroke-width:1.2;rx:8}.arrow{stroke:#334155;stroke-width:2;fill:none;marker-end:url(#arrow)}</style>',
                '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#334155"/></marker></defs>',
                body,
                "</svg>",
            ]
        ),
        encoding="utf-8",
    )


def text(x: float, y: float, value: object, klass: str = "label", anchor: str = "middle") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{klass}" text-anchor="{anchor}">{esc(value)}</text>'


def rect(x: float, y: float, w: float, h: float, fill: str, stroke: str = "none", klass: str = "") -> str:
    class_attr = f' class="{klass}"' if klass else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="7" fill="{fill}" stroke="{stroke}"{class_attr}/>'


def architecture() -> None:
    boxes = [
        ("Cameras\nRGB-D + wrist", 70, 160, COLORS["blue"]),
        ("Occupancy\nTSDF + slots", 235, 160, COLORS["teal"]),
        ("System 2\n7B semantic planner\n5-10 Hz", 410, 160, COLORS["purple"]),
        ("Intent Ring\nCRC + TTL", 610, 160, COLORS["amber"]),
        ("System 1\n88M reactive ctrl\n125 Hz", 775, 160, COLORS["green"]),
        ("Safety Critic\nhard veto", 945, 160, COLORS["red"]),
        ("Actuators\nbase arm gripper", 945, 340, COLORS["orange"]),
        ("Peer Robot\nstate + intent", 430, 380, COLORS["muted"]),
    ]
    body = [text(550, 55, "AURORA asynchronous dual-rate control graph", "title")]
    for label, x, y, color in boxes:
        body.append(rect(x, y, 130, 94, "#ffffff", color, "box"))
        lines = label.split("\n")
        for idx, line in enumerate(lines):
            body.append(text(x + 65, y + 32 + idx * 19, line, "label" if idx == 0 else "small"))
    arrows = [
        (200, 207, 235, 207),
        (365, 207, 410, 207),
        (540, 207, 610, 207),
        (740, 207, 775, 207),
        (905, 207, 945, 207),
        (1010, 254, 1010, 340),
        (495, 380, 495, 254),
        (560, 425, 775, 238),
    ]
    for x1, y1, x2, y2 in arrows:
        body.append(f'<path d="M{x1},{y1} L{x2},{y2}" class="arrow"/>')
    body.append(text(565, 510, "Slow semantics publish compact, time-bounded intent; fast control never blocks on VLA inference.", "label"))
    write_svg(ASSETS / "architecture.svg", "\n".join(body), 1120, 570)


def grouped_bar(path: Path, title: str, categories: list[str], series: list[tuple[str, list[float], str]], y_max: float) -> None:
    width, height = 1100, 620
    left, right, top, bottom = 95, 35, 86, 120
    chart_w, chart_h = width - left - right, height - top - bottom
    group_w = chart_w / len(categories)
    bar_w = min(48, group_w / (len(series) + 1.2))
    body = [text(width / 2, 45, title, "title")]
    for tick in range(6):
        value = y_max * tick / 5
        y = top + chart_h - chart_h * value / y_max
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="grid"/>')
        body.append(text(left - 14, y + 4, f"{value:.2g}", "small", "end"))
    body.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+chart_h}" class="axis"/>')
    body.append(f'<line x1="{left}" y1="{top+chart_h}" x2="{width-right}" y2="{top+chart_h}" class="axis"/>')
    for i, category in enumerate(categories):
        cx = left + group_w * (i + 0.5)
        body.append(text(cx, top + chart_h + 28, category, "small"))
        start_x = cx - (len(series) * bar_w) / 2
        for j, (_, values, color) in enumerate(series):
            value = values[i]
            h = chart_h * value / y_max
            x = start_x + j * bar_w
            y = top + chart_h - h
            body.append(rect(x, y, bar_w * 0.82, h, color))
            body.append(text(x + bar_w * 0.41, y - 6, f"{value:.2g}", "small"))
    legend_x = left
    for name, _, color in series:
        body.append(rect(legend_x, height - 48, 18, 18, color))
        body.append(text(legend_x + 25, height - 34, name, "small", "start"))
        legend_x += 165
    write_svg(path, "\n".join(body), width, height)


def real_results() -> None:
    grouped_bar(
        ASSETS / "real_task_results.svg",
        "Real paired trials: success and collision by task",
        [row["task"] for row in REAL_TASK_RESULTS],
        [
            ("Success", [row["success"] for row in REAL_TASK_RESULTS], COLORS["green"]),
            ("Collision", [row["collision"] for row in REAL_TASK_RESULTS], COLORS["red"]),
        ],
        0.8,
    )


def sim_real_gap() -> None:
    real_by_task = {row["task"]: row["success"] for row in REAL_TASK_RESULTS}
    categories = ["Handoff", "Clutter+Tool", "Drawer+Tool", "Language"]
    grouped_bar(
        ASSETS / "sim_real_gap.svg",
        "Held-out simulation vs real success",
        categories,
        [
            ("Simulation", [next(row["success"] for row in SIM_RESULTS if row["task"] == c) for c in categories], COLORS["blue"]),
            ("Real", [real_by_task[c] for c in categories], COLORS["orange"]),
        ],
        0.8,
    )


def ablation() -> None:
    grouped_bar(
        ASSETS / "architecture_ablation.svg",
        "Architecture ablation: asynchronous split matters",
        [row["architecture"] for row in ARCHITECTURE_ABLATION],
        [
            ("Success", [row["success"] for row in ARCHITECTURE_ABLATION], COLORS["green"]),
            ("Collision", [row["collision"] for row in ARCHITECTURE_ABLATION], COLORS["red"]),
        ],
        0.7,
    )


def latency() -> None:
    categories = list(next(iter(LATENCY_PROFILE.values())).keys())
    grouped_bar(
        ASSETS / "latency_profile.svg",
        "Final edge p95 latency profile, milliseconds",
        categories,
        [
            ("Robot A", [LATENCY_PROFILE["Robot A"][c] for c in categories], COLORS["blue"]),
            ("Robot B", [LATENCY_PROFILE["Robot B"][c] for c in categories], COLORS["teal"]),
        ],
        230.0,
    )


def quantization_scatter() -> None:
    width, height = 1100, 620
    left, right, top, bottom = 100, 60, 80, 90
    chart_w, chart_h = width - left - right, height - top - bottom
    x_min, x_max = 130.0, 410.0
    y_min, y_max = 0.35, 0.62
    body = [text(width / 2, 45, "Quantization tradeoff: planner latency vs rare-tool success", "title")]
    for tick in range(6):
        x_val = x_min + (x_max - x_min) * tick / 5
        x = left + chart_w * (x_val - x_min) / (x_max - x_min)
        body.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height-bottom}" class="grid"/>')
        body.append(text(x, height - bottom + 26, f"{x_val:.0f}", "small"))
        y_val = y_min + (y_max - y_min) * tick / 5
        y = top + chart_h - chart_h * (y_val - y_min) / (y_max - y_min)
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="grid"/>')
        body.append(text(left - 14, y + 4, f"{y_val:.2f}", "small", "end"))
    body.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" class="axis"/>')
    body.append(f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" class="axis"/>')
    palette = [COLORS["purple"], COLORS["red"], COLORS["green"], COLORS["amber"], COLORS["blue"]]
    for row, color in zip(QUANTIZATION_RESULTS, palette):
        x = left + chart_w * (row["planner_p95"] - x_min) / (x_max - x_min)
        y = top + chart_h - chart_h * (row["rare_tool"] - y_min) / (y_max - y_min)
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="{color}" stroke="#111827" stroke-width="1"/>')
        body.append(text(x + 16, y - 12, row["engine"], "small", "start"))
    body.append(text(width / 2, height - 25, "Planner p95 latency (ms)", "label"))
    body.append(f'<text x="30" y="{height/2:.1f}" class="label" transform="rotate(-90 30 {height/2:.1f})" text-anchor="middle">Rare-tool success</text>')
    write_svg(ASSETS / "quantization_tradeoff.svg", "\n".join(body), width, height)


def ppo_recovery() -> None:
    grouped_bar(
        ASSETS / "ppo_recovery.svg",
        "PPO residual recovery diagnostics",
        [row["run"] for row in PPO_RECOVERY],
        [
            ("Recovery success", [row["recovery_success"] for row in PPO_RECOVERY], COLORS["green"]),
            ("Freeze rate", [row["freeze_rate"] for row in PPO_RECOVERY], COLORS["red"]),
            ("Entropy", [row["entropy"] for row in PPO_RECOVERY], COLORS["blue"]),
        ],
        0.55,
    )


def main() -> int:
    architecture()
    real_results()
    sim_real_gap()
    ablation()
    latency()
    quantization_scatter()
    ppo_recovery()
    print(f"wrote SVG figures to {ASSETS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
