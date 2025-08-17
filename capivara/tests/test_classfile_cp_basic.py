import os
import re
import sys
import shutil
import subprocess
import unittest
from pathlib import Path

from capivara.classfile.reader import read_classfile, MAGIC
from capivara.classfile.constant_pool import (
    CpUtf8, CpClass, CpString, CpMethodref, CpFieldref, CpNameAndType,
    CpFloat, CpDouble, CpLong, CpInteger
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "capivara" / "tests" / "fixtures"

class TestClassfileConstantPool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Compila CPDemo.java com --release 8
        cls.build_dir = PROJECT_ROOT / "build" / "cpdemo"
        if cls.build_dir.exists():
            shutil.rmtree(cls.build_dir)
        cls.build_dir.mkdir(parents=True, exist_ok=True)
        src = FIXTURES / "CPDemo.java"
        (cls.build_dir / "CPDemo.java").write_text(src.read_text(), encoding="utf-8")

        r = subprocess.run(["javac", "--release", "8", "CPDemo.java"],
                           cwd=str(cls.build_dir), capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"Falha ao compilar CPDemo.java: {r.stderr}")

        # Carrega bytes do .class compilado
        cls.class_path = cls.build_dir / "CPDemo.class"
        cls.class_bytes = cls.class_path.read_bytes()

        # Saída do javap -v (para comparação parcial)
        r = subprocess.run(["javap", "-v", "-cp", str(cls.build_dir), "CPDemo"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"Falha ao rodar javap -v: {r.stderr}")
        cls.javap_text = r.stdout

    def test_magic_and_version(self):
        cf = read_classfile(self.class_bytes)
        self.assertEqual(cf.magic, MAGIC)
        self.assertEqual(cf.major_version, 52)
        # minor pode variar, mas normalmente 0 para javac --release 8
        self.assertIsInstance(cf.minor_version, int)

    def test_constant_pool_core_items(self):
        cf = read_classfile(self.class_bytes)
        cp = cf.constant_pool

        # Deve haver um Utf8 "capivara"
        idxs = cp.find_utf8("capivara")
        self.assertTrue(len(idxs) >= 1, "Utf8 'capivara' não encontrado na CP")

        # Deve haver um Utf8 "CPDemo" e um Class apontando pra ele
        idxs_name = cp.find_utf8("CPDemo")
        self.assertTrue(idxs_name, "Utf8 'CPDemo' não encontrado")
        has_class_cpdemo = False
        for i in range(1, len(cp)):
            e = cp.entries[i]
            if isinstance(e, CpClass):
                name = cp.try_get_utf8(e.name_index)
                if name == "CPDemo":
                    has_class_cpdemo = True
                    break
        self.assertTrue(has_class_cpdemo, "CpClass para 'CPDemo' não encontrado")

        # Presença de elementos típicos: java/io/PrintStream e println
        self.assertTrue(cp.find_utf8("java/io/PrintStream"), "Utf8 'java/io/PrintStream' ausente")
        self.assertTrue(cp.find_utf8("println"), "Utf8 'println' ausente")

        # Opcional: conferir que há ao menos um Float/Double/Long/Integer na CP
        has_num = any(isinstance(cp.entries[i], (CpFloat, CpDouble, CpLong, CpInteger))
                      for i in range(1, len(cp)))
        self.assertTrue(has_num, "Nenhuma constante numérica encontrada na CP (esperado pelo CPDemo)")

    def test_compare_with_javap_partial(self):
        # Extrai major/minor do javap -v
        m_major = re.search(r"major version:\s*(\d+)", self.javap_text)
        m_minor = re.search(r"minor version:\s*(\d+)", self.javap_text)
        self.assertIsNotNone(m_major, "javap -v não mostrou 'major version'")
        self.assertIsNotNone(m_minor, "javap -v não mostrou 'minor version'")

        major = int(m_major.group(1))
        minor = int(m_minor.group(1))
        self.assertEqual(major, 52, "javap não reportou major 52 (compilação deveria ser --release 8)")

        cf = read_classfile(self.class_bytes)
        self.assertEqual(cf.major_version, major)
        self.assertEqual(cf.minor_version, minor)

        # Confirma presença da string "capivara" no javap (Constant pool)
        self.assertIn("capivara", self.javap_text)

if __name__ == "__main__":
    unittest.main(verbosity=2)