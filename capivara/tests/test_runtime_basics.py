import shutil
import subprocess
import unittest
from pathlib import Path

from capivara.util.descriptors import (
    parse_field_descriptor, parse_method_descriptor,
    BaseType, ObjectType, ArrayType, DescriptorError
)
from capivara.runtime.frame import Frame, StackOverflowError, StackUnderflowError, LocalAccessError
from capivara.runtime.values import TOP
from capivara.runtime.strings import StringPool
from capivara.classfile.reader import read_classfile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "capivara" / "tests" / "fixtures"

class TestDescriptors(unittest.TestCase):
    def test_field_and_array_descriptors(self):
        t = parse_field_descriptor("I")
        self.assertIsInstance(t, BaseType)
        self.assertEqual(t.code, "I")
        self.assertEqual(t.width(), 1)

        t = parse_field_descriptor("J")
        self.assertIsInstance(t, BaseType)
        self.assertEqual(t.code, "J")
        self.assertEqual(t.width(), 2)

        t = parse_field_descriptor("Ljava/lang/String;")
        self.assertIsInstance(t, ObjectType)
        self.assertEqual(t.internal_name, "java/lang/String")

        t = parse_field_descriptor("[I")
        self.assertIsInstance(t, ArrayType)
        self.assertEqual(t.dims, 1)
        self.assertIsInstance(t.component, BaseType)
        self.assertEqual(t.component.code, "I")

        t = parse_field_descriptor("[[Ljava/lang/String;")
        self.assertIsInstance(t, ArrayType)
        self.assertEqual(t.dims, 2)
        self.assertIsInstance(t.component, ObjectType)
        self.assertEqual(t.component.internal_name, "java/lang/String")

        with self.assertRaises(DescriptorError):
            parse_field_descriptor("Lbadname")  # falta ';'

    def test_method_descriptor(self):
        params, ret = parse_method_descriptor("(I[Ljava/lang/String;)V")
        self.assertEqual(len(params), 2)
        self.assertIsInstance(params[0], BaseType)
        self.assertEqual(params[0].code, "I")
        self.assertIsInstance(params[1], ArrayType)
        self.assertIsInstance(params[1].component, ObjectType)
        self.assertEqual(ret.code, "V")

class TestFrame(unittest.TestCase):
    def test_push_pop_and_widths(self):
        fr = Frame(max_locals=8, max_stack=8)

        fr.push_int(10)
        fr.push_long(0x100000000)  # cabe em 64b
        fr.push_double(3.14)
        fr.push_ref(None)
        # Stack: [int, long, TOP, double, TOP, ref] => 6 slots
        self.assertEqual(len(fr.ostack), 6)
        self.assertIs(fr.ostack[2], TOP)
        self.assertIs(fr.ostack[4], TOP)

        r = fr.pop_ref()
        self.assertIsNone(r)
        d = fr.pop_double()
        self.assertAlmostEqual(d, 3.14, places=6)
        l = fr.pop_long()
        self.assertEqual(l, 0x100000000 - (1 << 32))  # signed
        i = fr.pop_int()
        self.assertEqual(i, 10)
        with self.assertRaises(StackUnderflowError):
            fr.pop_int()

    def test_locals_layout(self):
        fr = Frame(max_locals=6, max_stack=4)
        fr.set_local_int(0, 7)
        fr.set_local_long(1, 9)
        fr.set_local_double(3, 2.5)
        fr.set_local_ref(5, None)

        self.assertEqual(fr.get_local_int(0), 7)
        self.assertEqual(fr.get_local_long(1), 9)
        self.assertEqual(fr.get_local_double(3), 2.5)
        self.assertIsNone(fr.get_local_ref(5))
        self.assertIs(fr.locals[2], TOP)
        self.assertIs(fr.locals[4], TOP)

        with self.assertRaises(LocalAccessError):
            fr.set_local_long(5, 1)  # estoura limite de width=2

    def test_stack_overflow(self):
        fr = Frame(max_locals=1, max_stack=2)
        fr.push_int(1)
        with self.assertRaises(StackOverflowError):
            fr.push_double(1.0)

class TestStringPool(unittest.TestCase):
    def test_intern_identity(self):
        pool = StringPool()
        a = pool.intern("capivara")
        b = pool.intern("capivara")
        c = pool.intern("Capivara")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(pool.get(a), "capivara")

class TestDescriptorFromClass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build_dir = PROJECT_ROOT / "build" / "sigdemo"
        if cls.build_dir.exists():
            shutil.rmtree(cls.build_dir)
        cls.build_dir.mkdir(parents=True, exist_ok=True)
        # compila SigDemo
        src = FIXTURES / "SigDemo.java"
        (cls.build_dir / "SigDemo.java").write_text(src.read_text(), encoding="utf-8")
        r = subprocess.run(["javac", "--release", "8", "SigDemo.java"],
                           cwd=str(cls.build_dir), capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"Falha ao compilar SigDemo.java: {r.stderr}")
        cls.class_bytes = (cls.build_dir / "SigDemo.class").read_bytes()

    def test_parse_method_descriptor_from_cp(self):
        cf = read_classfile(self.class_bytes)
        cp = cf.constant_pool
        # encontra método 'f'
        for m in cf.methods:
            name = cp.get_utf8(m.name_index)
            if name == "f":
                desc = cp.get_utf8(m.descriptor_index)  # ex.: (IJ[Ljava/lang/String;)I
                params, ret = parse_method_descriptor(desc)
                self.assertEqual(len(params), 3)
                self.assertIsInstance(params[0], BaseType)
                self.assertEqual(params[0].code, "I")
                self.assertIsInstance(params[1], BaseType)
                self.assertEqual(params[1].code, "J")
                self.assertIsInstance(params[2], ArrayType)
                self.assertIsInstance(params[2].component, ObjectType)
                self.assertIsInstance(ret, BaseType)
                self.assertEqual(ret.code, "I")
                break
        else:
            self.fail("método 'f' não encontrado em SigDemo")