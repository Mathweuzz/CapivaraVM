import shutil
import subprocess
import unittest
from pathlib import Path

from capivara.loader.loader import ClassLoader
from capivara.runtime.values import VMValue
from capivara.util.flags import ACC_STATIC, ACC_FINAL

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "capivara" / "tests" / "fixtures"

class TestLoaderDirs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build_dir = PROJECT_ROOT / "build" / "loader1"
        if cls.build_dir.exists():
            shutil.rmtree(cls.build_dir)
        cls.build_dir.mkdir(parents=True, exist_ok=True)

        # Copia e compila A.java e B.java
        for name in ("A.java", "B.java"):
            (cls.build_dir / name).write_text((FIXTURES / name).read_text(), encoding="utf-8")
        r = subprocess.run(["javac", "--release", "8", "A.java", "B.java"],
                           cwd=str(cls.build_dir), capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"Falha ao compilar fixtures A/B: {r.stderr}")

    def test_load_and_link_static_constantvalue(self):
        ld = ClassLoader([str(self.build_dir)])
        rcA = ld.load_class("A")
        self.assertEqual(rcA.name, "A")
        # super é java/lang/Object — aceito sem carregar do JDK
        self.assertEqual(rcA.super_name, "java/lang/Object")

        # ConstantValue final: C deve estar setado como 7
        v = rcA.statics.get(("C", "I"))
        self.assertIsInstance(v, VMValue)
        self.assertEqual(v.tag, "int")
        self.assertEqual(v.value, 7)

        # Campo não-final X não deve ter valor de inicialização (fica default 0)
        vX = rcA.statics.get(("X", "I"))
        self.assertIsInstance(vX, VMValue)
        self.assertEqual(vX.tag, "int")
        self.assertEqual(vX.value, 0)

        # <clinit> detectado (mas não executado)
        self.assertIsNotNone(rcA.clinit)

    def test_resolve_super_and_cache(self):
        ld = ClassLoader([str(self.build_dir)])
        rcB = ld.load_class("B")
        self.assertEqual(rcB.name, "B")
        self.assertEqual(rcB.super_name, "A")
        # ao carregar B, a superclasse A deve estar no cache
        rcA = ld.loaded.get("A")
        self.assertIsNotNone(rcA)
        # C deve estar preparado (7)
        v = rcA.statics.get(("C", "I"))
        self.assertEqual(v.value, 7)

if __name__ == "__main__":
    unittest.main(verbosity=2)