import shutil
import subprocess
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "capivara" / "tests" / "fixtures"

class TestObjectsAndFields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build_dir = PROJECT_ROOT / "build" / "objects"
        if cls.build_dir.exists():
            shutil.rmtree(cls.build_dir)
        cls.build_dir.mkdir(parents=True, exist_ok=True)

        for name in ("InstFields.java", "StaticsDemo.java", "VirtCall.java"):
            (cls.build_dir / name).write_text((FIXTURES / name).read_text(), encoding="utf-8")
        r = subprocess.run(
            ["javac", "--release", "8", "InstFields.java", "StaticsDemo.java", "VirtCall.java"],
            cwd=str(cls.build_dir), capture_output=True, text=True
        )
        if r.returncode != 0:
            raise RuntimeError(f"Falha ao compilar fixtures objetos/campos: {r.stderr}")

    def _run(self, klass: str, desc: str="()I"):
        cmd = [sys.executable, "-m", "capivara.cli", "run", klass, "--cp", str(self.build_dir),
               "--entry", "run", "--desc", desc]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_instance_fields_and_constructor(self):
        r = self._run("InstFields", "()I")
        self.assertEqual(r.returncode, 0, msg=(r.stdout + r.stderr))
        self.assertIn("RET: 13", r.stdout)

    def test_statics_get_put(self):
        r = self._run("StaticsDemo", "()I")
        self.assertEqual(r.returncode, 0, msg=(r.stdout + r.stderr))
        self.assertIn("RET: 7", r.stdout)

    def test_invokevirtual_override(self):
        r = self._run("VirtCall", "()I")
        self.assertEqual(r.returncode, 0, msg=(r.stdout + r.stderr))
        self.assertIn("RET: 3", r.stdout)

if __name__ == "__main__":
    unittest.main(verbosity=2)
