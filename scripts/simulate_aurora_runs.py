#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.simulated_runs import TASKS, SimRunConfig, simulate_run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic AURORA simulation frames.")
    parser.add_argument("--task", choices=sorted(TASKS), default="drawer_tool")
    parser.add_argument("--run-id", default="sim-drawer-tool-demo")
    parser.add_argument("--output-dir", default="docs/sim_runs")
    parser.add_argument("--frames", type=int, default=14)
    parser.add_argument("--seed", type=int, default=145)
    args = parser.parse_args()

    manifest = simulate_run(
        SimRunConfig(
            run_id=args.run_id,
            task=args.task,
            output_dir=Path(args.output_dir),
            frames=args.frames,
            seed=args.seed,
        )
    )
    run_dir = Path(args.output_dir) / str(manifest["run_id"])
    print(f"Generated {len(manifest['frames'])} synthetic frames")
    print(f"Manifest:      {run_dir / 'manifest.json'}")
    print(f"Gallery:       {run_dir / 'gallery.md'}")
    print(f"Contact sheet: {run_dir / 'contact_sheet.svg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
