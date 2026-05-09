#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.real_images import ExtractConfig, extract_real_images, safe_run_id  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract representative real-run frames from videos or exported image directories."
    )
    parser.add_argument("--source", required=True, help="Video file, image file, image directory, or directory of run media.")
    parser.add_argument("--run-id", required=True, help="Stable run identifier, e.g. R-Apt-17.")
    parser.add_argument("--output-dir", default="docs/real_runs", help="Directory for extracted galleries.")
    parser.add_argument("--every-seconds", type=float, default=2.0, help="Video sampling period.")
    parser.add_argument("--max-frames", type=int, default=24, help="Maximum frames per source.")
    parser.add_argument("--width", type=int, default=960, help="Extracted video frame width.")
    args = parser.parse_args()

    manifest = extract_real_images(
        ExtractConfig(
            source=Path(args.source),
            output_dir=Path(args.output_dir),
            run_id=safe_run_id(args.run_id),
            every_seconds=args.every_seconds,
            max_frames=args.max_frames,
            width=args.width,
        )
    )
    run_dir = Path(args.output_dir) / str(manifest["run_id"])
    print(f"Extracted {len(manifest['frames'])} frames")
    print(f"Manifest: {run_dir / 'manifest.json'}")
    print(f"Gallery:   {run_dir / 'gallery.md'}")
    print(f"Contact:   {run_dir / 'contact_sheet.svg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
