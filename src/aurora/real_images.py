from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
BAG_EXTENSIONS = {".bag", ".db3"}


@dataclass(frozen=True)
class ExtractConfig:
    source: Path
    output_dir: Path
    run_id: str
    every_seconds: float = 2.0
    max_frames: int = 24
    width: int = 960


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_sources(source: Path) -> list[Path]:
    if source.is_file():
        return [source]
    if not source.is_dir():
        raise FileNotFoundError(f"source does not exist: {source}")
    found: list[Path] = []
    for path in sorted(source.rglob("*")):
        if path.suffix.lower() in VIDEO_EXTENSIONS | IMAGE_EXTENSIONS | BAG_EXTENSIONS:
            found.append(path)
    return found


def safe_run_id(value: str) -> str:
    keep = []
    last_dash = False
    for char in value.strip().lower():
        if char.isalnum() or char in {"-", "_"}:
            keep.append(char)
            last_dash = char == "-"
        elif char in {" ", ".", "/"}:
            if not last_dash:
                keep.append("-")
                last_dash = True
    cleaned = "".join(keep).strip("-")
    return cleaned or "real-run"


def extract_real_images(config: ExtractConfig) -> dict[str, object]:
    """Extract representative frames from real video/image sources.

    ROS bag formats are detected but intentionally not decoded here because
    reliable extraction depends on ROS 1/2 message definitions and topic names.
    Convert bag image topics to videos first, or pass an exported image folder.
    """

    output = config.output_dir / safe_run_id(config.run_id)
    frames_dir = output / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    sources = discover_sources(config.source)
    if not sources:
        raise ValueError(f"no supported images or videos found under {config.source}")

    manifest: dict[str, object] = {
        "run_id": safe_run_id(config.run_id),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(config.source),
        "every_seconds": config.every_seconds,
        "max_frames": config.max_frames,
        "width": config.width,
        "sources": [],
        "frames": [],
    }

    frame_index = 0
    processed_image_dirs: set[Path] = set()
    for source in sources:
        suffix = source.suffix.lower()
        if suffix in BAG_EXTENSIONS:
            manifest["sources"].append(
                {
                    "path": str(source),
                    "type": "bag",
                    "status": "skipped",
                    "reason": "ROS bags require topic-specific conversion before frame extraction",
                }
            )
            continue
        if suffix in IMAGE_EXTENSIONS:
            if source.parent in processed_image_dirs:
                continue
            processed_image_dirs.add(source.parent)
            frame_index = _copy_sampled_images(source, frames_dir, frame_index, config, manifest)
            continue
        if suffix in VIDEO_EXTENSIONS:
            frame_index = _extract_video_frames(source, frames_dir, frame_index, config, manifest)
            continue

    frames = sorted(frames_dir.glob("*.jpg"))
    if not frames:
        raise ValueError("no frames were extracted; provide video files or exported image folders")

    manifest["frames"] = [
        {
            "file": str(path.relative_to(output)),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in frames
    ]
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_gallery_markdown(output, frames)
    write_contact_sheet_svg(output, frames)
    return manifest


def _copy_sampled_images(
    source: Path,
    frames_dir: Path,
    frame_index: int,
    config: ExtractConfig,
    manifest: dict[str, object],
) -> int:
    parent = source.parent
    images = [path for path in sorted(parent.iterdir()) if path.suffix.lower() in IMAGE_EXTENSIONS]
    if not images:
        images = [source]
    stride = max(1, math.ceil(len(images) / max(1, config.max_frames)))
    copied = 0
    for image in images[::stride]:
        if copied >= config.max_frames:
            break
        frame_index += 1
        target = frames_dir / f"frame_{frame_index:04d}.jpg"
        shutil.copyfile(image, target)
        copied += 1
    manifest["sources"].append(
        {
            "path": str(parent),
            "type": "image-directory",
            "status": "ok",
            "frames": copied,
        }
    )
    return frame_index


def _extract_video_frames(
    source: Path,
    frames_dir: Path,
    frame_index: int,
    config: ExtractConfig,
    manifest: dict[str, object],
) -> int:
    before = set(frames_dir.glob("*.jpg"))
    pattern = frames_dir / f"{source.stem}_%04d.jpg"
    fps_expr = f"fps=1/{config.every_seconds},scale={config.width}:-2"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vf",
        fps_expr,
        "-frames:v",
        str(config.max_frames),
        str(pattern),
    ]
    subprocess.run(cmd, check=True)
    generated = sorted(set(frames_dir.glob("*.jpg")) - before)
    renamed = 0
    for generated_path in generated:
        frame_index += 1
        target = frames_dir / f"frame_{frame_index:04d}.jpg"
        generated_path.replace(target)
        renamed += 1
    manifest["sources"].append(
        {
            "path": str(source),
            "type": "video",
            "status": "ok",
            "frames": renamed,
            "sha256": sha256_file(source),
        }
    )
    return frame_index


def write_gallery_markdown(output: Path, frames: list[Path]) -> None:
    lines = [
        f"# Real Run Image Gallery: `{output.name}`",
        "",
        "These frames were extracted from user-provided real-run media. They are not generated or simulated.",
        "",
    ]
    for frame in frames:
        rel = frame.relative_to(output)
        lines.append(f'<img src="{rel.as_posix()}" width="320" alt="{frame.name}">')
    (output / "gallery.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_contact_sheet_svg(output: Path, frames: list[Path], columns: int = 4) -> None:
    thumb_w, thumb_h = 240, 160
    pad = 18
    rows = math.ceil(len(frames) / columns)
    width = columns * thumb_w + (columns + 1) * pad
    height = rows * (thumb_h + 34) + 72
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="18" y="34" font-family="Inter,Arial,sans-serif" font-size="22" font-weight="700" fill="#1f2937">Real-run extracted frames</text>',
    ]
    for idx, frame in enumerate(frames):
        row = idx // columns
        col = idx % columns
        x = pad + col * (thumb_w + pad)
        y = 58 + row * (thumb_h + 34)
        rel = frame.relative_to(output)
        parts.append(f'<rect x="{x}" y="{y}" width="{thumb_w}" height="{thumb_h}" rx="6" fill="#e2e8f0" stroke="#94a3b8"/>')
        parts.append(f'<image href="{rel.as_posix()}" x="{x}" y="{y}" width="{thumb_w}" height="{thumb_h}" preserveAspectRatio="xMidYMid slice"/>')
        parts.append(f'<text x="{x}" y="{y + thumb_h + 20}" font-family="Inter,Arial,sans-serif" font-size="12" fill="#475569">{frame.name}</text>')
    parts.append("</svg>")
    (output / "contact_sheet.svg").write_text("\n".join(parts), encoding="utf-8")
