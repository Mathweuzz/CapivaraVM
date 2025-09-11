import shutil
import subprocess
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "capivara" / "tests" / "fixtures"

class TestInvocationsStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build_dir = PROJECT_ROOT / "build" / "invokes"
        if cls.build_dir.exists():
            shutil.rmtree(cls.build_dir)
        cls.build_dir.mkdir(parents=True, exist_ok=True)

        for name in ("ChainCalls.java", "InheritStatic.java"):
            (cls.build_dir / name).write_text((FIXTURES / name).read_text(), encoding="utf-8")
        r = subprocess.run(["javac", "--release", "8", "ChainCalls.java", "InheritStatic.java"],
                           cwd=str(cls.build_dir), capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"Falha ao compilar fixtures invokes: {r.stderr}")

    def _run(self, klass: str, desc: str="()I"):
        cmd = [sys.executable, "-m", "capivara.cli", "run", klass, "--cp", str(self.build_dir),
               "--entry", "run", "--desc", desc]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_chaincalls(self):
        r = self._run("ChainCalls", "()I")
        self.assertEqual(r.returncode, 0, msg=(r.stdout + r.stderr))
        self.assertIn("RET: 18", r.stdout)

    def test_inherit_static(self):
        r = self._run("InheritStatic", "()I")
        self.assertEqual(r.returncode, 0, msg=(r.stdout + r.stderr))
        self.assertIn("RET: 10", r.stdout)

if __name__ == "__main__":
    unittest.main(verbosity=2)
