"""Integration checks for the portable CLI. Engine tests use smoke --sample."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class StudioTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.project = Path(folder.name) / "Game With Spaces"

    def run_cli(self, *args, expected=0):
        process = subprocess.run(
            [sys.executable, str(REPO / "studio.py"), "--project", str(self.project), *args],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(process.returncode, expected, process.stdout + process.stderr)
        return process.stdout

    def test_blank_and_adoption(self):
        self.run_cli("setup", "--engine", "godot", "--agents", "codex", "--non-interactive")
        game = self.project / "project.godot"
        initial = game.read_bytes()
        self.assertNotIn(b"run/main_scene", initial)
        self.run_cli("setup", "--agents", "codex", "claude", "--route", "qa=codex", "--non-interactive")
        self.assertEqual(game.read_bytes(), initial)
        settings = json.loads((self.project / ".studio/config.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["roles"]["qa"], "codex")
        self.assertEqual(settings["roles"]["marketing"], "claude")

    def test_workflow_dry_run(self):
        self.run_cli("setup", "--engine", "unity", "--template", "beacon",
                     "--agents", "codex", "claude", "gemini", "--non-interactive")
        self.run_cli("workflow", str(REPO / "examples/beacon-relay.md"),
                     "--through", "marketing", "--dry-run")
        manifest = next((self.project / ".studio/jobs").glob("*/workflow.json"))
        steps = json.loads(manifest.read_text(encoding="utf-8"))["stages"]
        self.assertEqual(len(steps), 9)
        self.assertEqual(steps["qa"]["provider"], "gemini")

    def test_custom_provider_and_qa_gate(self):
        mock = self.project.parent / "fake.py"
        mock.write_text(
            "import re, sys\n"
            "from pathlib import Path\n"
            "output = Path(re.search(r'Job output directory: (.+)', sys.stdin.read())[1])\n"
            "(output / 'report.md').write_text('Fixture report')\n"
            "(output / 'verdict.json').write_text('{\"passed\": false}')\n",
            encoding="utf-8",
        )
        mapping = mock.with_suffix(".json")
        mapping.write_text(json.dumps({"fixture": [sys.executable, str(mock)]}), encoding="utf-8")
        self.run_cli("setup", "--engine", "godot", "--agents", "fixture", "--provider-file",
                     str(mapping), "--non-interactive")
        self.run_cli("workflow", str(REPO / "examples/beacon-relay.md"),
                     "--from", "qa", "--through", "marketing", expected=4)
        run = next((self.project / ".studio/jobs").glob("workflow-*"))
        self.assertFalse((run / "marketing").exists())


if __name__ == "__main__":
    unittest.main()
