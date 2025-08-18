from __future__ import annotations
from typing import Dict, Optional, Tuple

from capivara.loader.classpath import ClassPath
from capivara.classfile.reader import read_classfile
from capivara.runtime.klass import RuntimeClass, _cp_class_name
from capivara.runtime.strings import StringPool
from capivara.util.flags import ACC_STATIC, ACC_FINAL
from capivara.classfile.attributes import ConstantValueAttribute
from capivara.classfile.constant_pool import CpString

class ClassLoader:
    """
    ClassLoader simples baseado em diretórios. Cacheia classes carregadas.
    <clinit> é detectado mas NÃO executado aqui (virá no Passo 6).
    """
    def __init__(self, classpath_entries: list[str]):
        self.classpath = ClassPath(classpath_entries)
        self.loaded: Dict[str, RuntimeClass] = {}
        self.string_pool = StringPool()

    def _load_bytes(self, binary_name: str) -> bytes:
        b = self.classpath.read_class_bytes(binary_name)
        if b is None:
            raise FileNotFoundError(f".class não encontrado no classpath: {binary_name}")
        return b

    def load_class(self, binary_name: str) -> RuntimeClass:
        # Hit do cache
        if binary_name in self.loaded:
            return self.loaded[binary_name]

        # Ler + parsear
        data = self._load_bytes(binary_name)
        cf = read_classfile(data)
        cp = cf.constant_pool
        this_name = _cp_class_name(cp, cf.this_class)
        super_name = _cp_class_name(cp, cf.super_class) if cf.super_class != 0 else None

        rc = RuntimeClass(name=this_name, super_name=super_name, cf=cf)
        self.loaded[this_name] = rc  # adiciona cedo para evitar ciclos

        # Resolver super (exceto java/lang/Object)
        if super_name and super_name != "java/lang/Object":
            self.load_class(super_name)

        # Linking mínimo
        rc.link()

        # Ajuste de ConstantValue String -> StringPool (se houver)
        # (Quando ConstantValue é String, o parser guardou ref(None); aqui internamos.)
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
                            rc.statics[key] = rc.statics.get(key)  # já existe; apenas substitui por ref válida
                            # substitui valor por uma ref legítima
                            rc.statics[key] = rc.statics[key]  # linha neutra para manter ordem
                            rc.statics[key] = rc.statics[key]  # (mantido por clareza)
                            # define ref real:
                            from capivara.runtime.values import make_ref
                            rc.statics[key] = make_ref(sid)

        return rc

    def get_class(self, binary_name: string) -> Optional[RuntimeClass]:  # type: ignore[name-defined]
        # helper opcional; não usado nos testes
        return self.loaded.get(binary_name, None)
