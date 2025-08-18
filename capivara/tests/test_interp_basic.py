import os
import sys
import shutil
import subprocess
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "capivara" / "tests" / "fixtures"

class TestInterpreterBasic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build_dir = PROJECT_ROOT / "build" / "interp1"
        if cls.build_dir.exists():
            shutil.rmtree(cls.build_dir)
        cls.build_dir.mkdir(parents=True, exist_ok=True)

        # Compila fixtures
        for name in ("SumN.java", "FlowOps.java"):
            (cls.build_dir / name).write_text((FIXTURES / name).read_text(), encoding="utf-8")
        r = subprocess.run(
            ["javac", "--release", "8", "SumN.java", "FlowOps.java"],
            cwd=str(cls.build_dir), capture_output=True, text=True
        )
        if r.returncode != 0:
            raise RuntimeError(f"Falha ao compilar fixtures: {r.stderr}")

    def _run(self, klass: str, desc: str = "()I"):
        cmd = [sys.executable, "-m", "capivara.cli", "run", klass, "--cp", str(self.build_dir), "--entry", "run", "--desc", desc]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_sumN(self):
        r = self._run("SumN", "()I")
        self.assertEqual(r.returncode, 0, msg=(r.stdout + r.stderr))
        self.assertIn("RET: 15", r.stdout)

    def test_flowops(self):
        r = self._run("FlowOps", "()I")
        self.assertEqual(r.returncode, 0, msg=(r.stdout + r.stderr))
        self.assertIn("RET: 1", r.stdout)

if __name__ == "__main__":
    unittest.main(verbosity=2)