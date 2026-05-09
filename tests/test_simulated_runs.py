import tempfile
from pathlib import Path
import unittest

from aurora.simulated_runs import SimRunConfig, simulate_run


class SimulatedRunsTest(unittest.TestCase):
    def test_simulate_run_writes_manifest_and_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = simulate_run(
                SimRunConfig(
                    run_id="Sim Drawer Demo",
                    task="drawer_tool",
                    output_dir=Path(tmp),
                    frames=4,
                    seed=3,
                )
            )
            run_dir = Path(tmp) / "sim-drawer-demo"

            self.assertEqual(manifest["task"], "drawer_tool")
            self.assertEqual(len(manifest["frames"]), 4)
            self.assertTrue((run_dir / "manifest.json").exists())
            self.assertTrue((run_dir / "contact_sheet.svg").exists())
            self.assertTrue((run_dir / "frames" / "frame_0001.svg").exists())


if __name__ == "__main__":
    unittest.main()
