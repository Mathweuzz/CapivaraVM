import re
import shutil
import subprocess
import unittest
from pathlib import Path

from capivara.classfile.reader import read_classfile
from capivara.classfile.constant_pool import CpClass, CpUtf8, CpInteger
from capivara.classfile.attributes import (
    CodeAttribute, LineNumberTableAttribute, SourceFileAttribute, ConstantValueAttribute
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "capivara" / "tests" / "fixtures"

def _cp_utf8(cp, idx: int) -> str:
    return cp.get_utf8(idx)

def _class_name(cp, class_index: int) -> str:
    c = cp.get(class_index)
    assert isinstance(c, CpClass)
    return _cp_utf8(cp, c.name_index)

class TestMembersAndAttributes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Compilar fixture com --release 8
        cls.build_dir = PROJECT_ROOT / "build" / "members"
        if cls.build_dir.exists():
            shutil.rmtree(cls.build_dir)
        cls.build_dir.mkdir(parents=True, exist_ok=True)

        src = FIXTURES / "CPDemo.java"
        (cls.build_dir / "CPDemo.java").write_text(src.read_text(), encoding="utf-8")
        r = subprocess.run(["javac", "--release", "8", "CPDemo.java"],
                           cwd=str(cls.build_dir), capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"Falha ao compilar CPDemo.java: {r.stderr}")

        cls.class_bytes = (cls.build_dir / "CPDemo.class").read_bytes()

        # javap -v para comparação parcial
        r = subprocess.run(["javap", "-v", "-cp", str(cls.build_dir), "CPDemo"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"Falha ao rodar javap -v: {r.stderr}")
        cls.javap_text = r.stdout

    def test_header_and_names(self):
        cf = read_classfile(self.class_bytes)
        cp = cf.constant_pool

        this_name = _class_name(cp, cf.this_class)
        super_name = _class_name(cp, cf.super_class)

        self.assertEqual(this_name, "CPDemo")
        self.assertEqual(super_name, "java/lang/Object")

        # SourceFile no nível de classe
        sf = [a for a in cf.attributes if isinstance(a, SourceFileAttribute)]
        self.assertTrue(sf, "Atributo SourceFile ausente no nível de classe")
        src_name = _cp_utf8(cp, sf[0].sourcefile_index)
        self.assertEqual(src_name, "CPDemo.java")

    def test_field_constantvalue(self):
        cf = read_classfile(self.class_bytes)
        cp = cf.constant_pool

        # Procura por field 'XI' do tipo 'I' e ConstantValue 42
        found = False
        for f in cf.fields:
            name = _cp_utf8(cp, f.name_index)
            desc = _cp_utf8(cp, f.descriptor_index)
            if name == "XI" and desc == "I":
                cvs = [a for a in f.attributes if isinstance(a, ConstantValueAttribute)]
                self.assertTrue(cvs, "Field XI deveria ter ConstantValue (é final)")
                cv_idx = cvs[0].constantvalue_index
                cv_entry = cp.get(cv_idx)
                self.assertIsInstance(cv_entry, CpInteger)
                self.assertEqual(cv_entry.value, 42)
                found = True
                break
        self.assertTrue(found, "Field estático final XI=42 não encontrado")

    def test_method_main_code_and_lnt(self):
        cf = read_classfile(self.class_bytes)
        cp = cf.constant_pool

        # main(String[])
        main = None
        for m in cf.methods:
            name = _cp_utf8(cp, m.name_index)
            desc = _cp_utf8(cp, m.descriptor_index)
            if name == "main" and desc == "([Ljava/lang/String;)V":
                main = m
                break
        self.assertIsNotNone(main, "Método main não encontrado")

        codes = [a for a in main.attributes if isinstance(a, CodeAttribute)]
        self.assertTrue(codes, "Método main deveria ter atributo Code")
        code_attr = codes[0]
        self.assertGreater(len(code_attr.code), 0, "Code do main deveria ter bytes")

        # LineNumberTable dentro do Code
        lnts = [a for a in code_attr.attributes if isinstance(a, LineNumberTableAttribute)]
        self.assertTrue(lnts, "Code do main deveria ter LineNumberTable")
        self.assertGreaterEqual(len(lnts[0].line_numbers), 1)

    def test_compare_with_javap_names(self):
        # Verifica que javap lista CPDemo e Object
        self.assertIn("CPDemo", self.javap_text)
        self.assertIn("java/lang/Object", self.javap_text)

if __name__ == "__main__":
    unittest.main(verbosity=2)