import tempfile
from pathlib import Path
import unittest

from aurora.real_images import ExtractConfig, discover_sources, extract_real_images, safe_run_id


class RealImagesTest(unittest.TestCase):
    def test_safe_run_id(self) -> None:
        self.assertEqual(safe_run_id("R-Apt-17 / Robot A.mov"), "r-apt-17-robot-a-mov")

    def test_discover_sources_finds_media(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run.mp4").write_bytes(b"fake")
            (root / "frame.jpg").write_bytes(b"fake")
            (root / "ignore.txt").write_text("x")

            found = {path.name for path in discover_sources(root)}

        self.assertEqual(found, {"frame.jpg", "run.mp4"})

    def test_extract_from_exported_image_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "images"
            output = root / "out"
            source.mkdir()
            for idx in range(3):
                (source / f"frame_{idx}.jpg").write_bytes(f"fake-jpeg-{idx}".encode())

            manifest = extract_real_images(
                ExtractConfig(source=source, output_dir=output, run_id="R-Test", max_frames=2)
            )
            run_dir = output / "r-test"

            self.assertEqual(len(manifest["frames"]), 2)
            self.assertTrue((run_dir / "manifest.json").exists())
            self.assertTrue((run_dir / "gallery.md").exists())
            self.assertTrue((run_dir / "contact_sheet.svg").exists())


if __name__ == "__main__":
    unittest.main()
