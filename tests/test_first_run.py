"""Offline regressions for first-run authentication and the npm launcher."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FirstRunTests(unittest.TestCase):
    def test_key_survives_new_process_and_logout(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
            env.pop("CYBERBARA_API_KEY", None)
            # Override the application's store only, without changing the user's home.
            script = (
                "import sys; from pathlib import Path; "
                "import cyberbara_cli.config as c; "
                "c.API_KEY_STORE_PATH=Path(sys.argv.pop(1)); "
                "from cyberbara_cli.cli import main; main()"
            )
            store = Path(tmp) / "config" / "api_key"

            def run(*args):
                return subprocess.run(
                    [shutil.which("python3"), "-c", script, str(store), *args],
                    env=env, text=True, capture_output=True, timeout=10,
                )

            configured = run("auth", "configure", "--api-key", "test-offline-key-123456")
            self.assertEqual(configured.returncode, 0, configured.stderr)
            self.assertTrue(json.loads(configured.stdout)["data"]["saved"])
            self.assertEqual(store.read_text(), "test-offline-key-123456\n")
            if os.name == "posix":
                self.assertEqual(store.stat().st_mode & 0o777, 0o600)
            whoami = run("auth", "whoami")
            self.assertEqual(whoami.returncode, 0, whoami.stderr)
            self.assertEqual(json.loads(whoami.stdout)["data"]["source"], "cache")
            self.assertNotIn("test-offline-key-123456", whoami.stdout)
            self.assertEqual(run("auth", "logout").returncode, 0)
            self.assertFalse(store.exists())
            self.assertNotEqual(run("auth", "whoami").returncode, 0)

    @unittest.skipUnless(shutil.which("node"), "Node.js not installed")
    def test_npm_launcher_in_path_with_apostrophe(self):
        with tempfile.TemporaryDirectory(prefix="cyberbara's install ") as tmp:
            target = Path(tmp) / "package"
            shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            result = subprocess.run(
                ["node", str(target / "bin" / "cyberbara.js"), "--help"],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Generate images", result.stdout)


if __name__ == "__main__":
    unittest.main()
