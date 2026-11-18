"""Integration checks for the portable CLI. Engine tests use smoke --sample."""
import json
from pathlib import Path
import shutil
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

    def test_quota_failover_preserves_checkpoint_and_workspace(self):
        mock = self.project.parent / "handoff.py"
        mock.write_text(
            """import json, re, sys
from pathlib import Path
prompt = sys.stdin.read()
folder = Path(re.search(r'Job output directory: (.+)', prompt)[1])
memory = Path('.studio/memory.md')
assert memory.is_file()
partial = Path('partial-work.txt')
if sys.argv[1] == 'primary':
    partial.write_text('saved edit')
    memory.write_text('The relay uses amber.')
    (folder / 'checkpoint.md').write_text('Next: verify the core interaction.')
    (folder / 'report.md').write_text('Incomplete report')
    print(json.dumps({'type': 'turn.failed', 'error': {'message': 'You have hit your usage limit'}}))
    sys.exit(1)
assert partial.read_text() == 'saved edit'
assert memory.read_text() == 'The relay uses amber.'
if 'role: producer' in prompt:
    assert 'Prior attempt folders' in prompt
    checkpoint = folder.parent / 'attempt-1-primary/checkpoint.md'
    assert checkpoint.read_text() == 'Next: verify the core interaction.'
else:
    assert 'attempt-2-backup' in prompt
(folder / 'report.md').write_text('Verified and completed')
""",
            encoding="utf-8",
        )
        mapping = mock.with_suffix(".json")
        mapping.write_text(json.dumps({
            name: [sys.executable, str(mock), name] for name in ("primary", "backup")
        }), encoding="utf-8")
        self.run_cli("setup", "--engine", "godot", "--agents", "primary", "backup",
                     "--provider-file", str(mapping), "--non-interactive")
        self.run_cli("workflow", str(REPO / "examples/beacon-relay.md"), "--through", "gameplay")
        run = next((self.project / ".studio/jobs").glob("workflow-*"))
        for role in ("producer", "gameplay"):
            handoff = json.loads((run / role / "handoff.json").read_text(encoding="utf-8"))
            self.assertEqual(handoff["provider"], "backup")
            self.assertEqual(handoff["exit_code"], 0)
        self.assertFalse((run / "gameplay/attempt-1-primary").exists())

    @unittest.skipUnless(shutil.which("git"), "Git is required for the memory commit check")
    def test_memory_commit_excludes_unrelated_staged_files(self):
        worker = self.project.parent / "worker.py"
        worker.write_text(
            """import json, re, sys
from pathlib import Path
prompt = sys.stdin.read()
assert 'StudioMemory/*.json' in prompt
folder = Path(re.search(r'Job output directory: (.+)', prompt)[1])
(folder / 'memory.json').write_text(json.dumps({
    'decisions': ['Use an amber relay core.'],
    'next_steps': ['Test the pickup interaction.']
}))
(folder / 'report.md').write_text('Fixture report')
""",
            encoding="utf-8",
        )
        mapping = worker.with_suffix(".json")
        mapping.write_text(json.dumps({"fixture": [sys.executable, str(worker)]}), encoding="utf-8")
        self.run_cli("setup", "--engine", "godot", "--agents", "fixture", "--provider-file",
                     str(mapping), "--memory-commit", "--non-interactive")

        def git(*args, cwd=None):
            result = subprocess.run(["git", *args], cwd=cwd or self.project, check=False,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.strip()

        git("init")
        git("config", "user.name", "Studio Fixture")
        git("config", "user.email", "studio@example.invalid")
        git("add", "--", "project.godot")
        git("commit", "-m", "Seed game")
        git("config", "commit.gpgsign", "false")
        (self.project / "unrelated.txt").write_text("Already staged", encoding="utf-8")
        git("add", "--", "unrelated.txt")
        self.run_cli("job", "producer", str(REPO / "examples/beacon-relay.md"))
        committed = git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD")
        self.assertTrue(committed.startswith("StudioMemory/"), committed)
        self.assertEqual(git("diff", "--cached", "--name-only"), "unrelated.txt")
        clone = self.project.parent / "Second checkout"
        git("clone", "--no-hardlinks", self.project.name, clone.name, cwd=self.project.parent)
        record = next((clone / "StudioMemory").glob("*.json"))
        data = json.loads(record.read_text(encoding="utf-8"))
        self.assertEqual(data["attempts"][0]["decisions"], ["Use an amber relay core."])
        self.assertFalse((clone / ".studio/config.json").exists())


if __name__ == "__main__":
    unittest.main()
