from __future__ import annotations
from typing import Dict, Optional, Tuple

from capivara.loader.classpath import ClassPath
from capivara.classfile.reader import read_classfile
from capivara.runtime.klass import RuntimeClass, _cp_class_name
from capivara.runtime.strings import StringPool
from capivara.runtime.heap import Heap
from capivara.util.flags import ACC_STATIC, ACC_FINAL
from capivara.classfile.attributes import ConstantValueAttribute

class ClassLoader:
    """
    ClassLoader simples baseado em diretórios. Cacheia classes carregadas.
    Mantém um Heap e um StringPool.
    """
    def __init__(self, classpath_entries: list[str]):
        self.classpath = ClassPath(classpath_entries)
        self.loaded: Dict[str, RuntimeClass] = {}
        self.string_pool = StringPool()
        self.heap = Heap()

    def _load_bytes(self, binary_name: str) -> bytes:
        b = self.classpath.read_class_bytes(binary_name)
        if b is None:
            raise FileNotFoundError(f".class não encontrado no classpath: {binary_name}")
        return b

    def load_class(self, binary_name: str) -> RuntimeClass:
        if binary_name in self.loaded:
            return self.loaded[binary_name]

        data = self._load_bytes(binary_name)
        cf = read_classfile(data)
        cp = cf.constant_pool
        this_name = _cp_class_name(cp, cf.this_class)
        super_name = _cp_class_name(cp, cf.super_class) if cf.super_class != 0 else None

        rc = RuntimeClass(name=this_name, super_name=super_name, cf=cf)
        self.loaded[this_name] = rc

        if super_name and super_name != "java/lang/Object":
            self.load_class(super_name)

        rc.link()

        # Bind ConstantValue String -> StringPool (se houver)
        for f in cf.fields:
            if (f.access_flags & (ACC_STATIC | ACC_FINAL)) == (ACC_STATIC | ACC_FINAL):
                for a in f.attributes:
                    if isinstance(a, ConstantValueAttribute):
                        e = cp.get(a.constantvalue_index)
                        from capivara.classfile.constant_pool import CpString
                        if isinstance(e, CpString):
                            s = cp.get_utf8(e.string_index)
                            sid = self.string_pool.intern(s)
                            key = (cp.get_utf8(f.name_index), cp.get_utf8(f.descriptor_index))
                            from capivara.runtime.values import make_ref
                            rc.statics[key] = make_ref(sid)

        return rc
