from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List

from capivara.classfile.reader import ClassFile
from capivara.classfile.constant_pool import ConstantPool, CpClass
from capivara.classfile.attributes import (
    AttributeInfo, CodeAttribute, ConstantValueAttribute
)
from capivara.classfile.members import FieldInfo, MethodInfo
from capivara.util.descriptors import parse_field_descriptor, BaseType, ObjectType, ArrayType
from capivara.util import flags as FL
from capivara.runtime.values import (
    VMValue, make_int, make_long, make_float, make_double, make_ref
)

def _cp_class_name(cp: ConstantPool, class_index: int) -> str:
    c = cp.get(class_index)
    assert isinstance(c, CpClass)
    return cp.get_utf8(c.name_index)

def _default_static_value(desc: str) -> VMValue:
    t = parse_field_descriptor(desc)
    if isinstance(t, BaseType):
        if t.code == "I" or t.code in ("B","C","S","Z"):
            return make_int(0)
        if t.code == "J":
            return make_long(0)
        if t.code == "F":
            return make_float(0.0)
        if t.code == "D":
            return make_double(0.0)
        if t.code == "V":
            raise ValueError("campo não pode ter retorno void")
    # Objetos e arrays -> null
    return make_ref(None)

@dataclass
class RuntimeClass:
    name: str
    super_name: Optional[str]
    cf: ClassFile

    # área de estáticos: chave = (fieldName, fieldDesc)
    statics: Dict[Tuple[str, str], VMValue] = field(default_factory=dict)

    # referência ao MethodInfo do <clinit> (se existir) e ao seu Code (se houver)
    clinit: Optional[MethodInfo] = None
    clinit_code: Optional[CodeAttribute] = None

    # status simples (para futuro): "loaded" -> "linked" -> "initialized"
    status: str = "loaded"

    def find_method(self, name: str, desc: str) -> Optional[MethodInfo]:
        cp = self.cf.constant_pool
        for m in self.cf.methods:
            n = cp.get_utf8(m.name_index)
            d = cp.get_utf8(m.descriptor_index)
            if n == name and d == desc:
                return m
        return None

    def _extract_code(self, m: MethodInfo) -> Optional[CodeAttribute]:
        for a in m.attributes:
            if isinstance(a, CodeAttribute):
                return a
        return None

    def link(self) -> None:
        """Linking mínimo: prepara estáticos com default e ConstantValue; detecta <clinit>."""
        if self.status != "loaded":
            return
        cp = self.cf.constant_pool

        # 1) Estáticos: defaults
        for f in self.cf.fields:
            is_static = (f.access_flags & FL.ACC_STATIC) != 0
            if not is_static:
                continue
            name = cp.get_utf8(f.name_index)
            desc = cp.get_utf8(f.descriptor_index)
            self.statics[(name, desc)] = _default_static_value(desc)

        # 2) ConstantValue em estáticos final (int/long/float/double/String)
        for f in self.cf.fields:
            is_static = (f.access_flags & FL.ACC_STATIC) != 0
            is_final  = (f.access_flags & FL.ACC_FINAL) != 0
            if not (is_static and is_final):
                continue
            cv = next((a for a in f.attributes if isinstance(a, ConstantValueAttribute)), None)
            if not cv:
                continue
            # resolve valor
            val = _resolve_constantvalue(cp, cv.constantvalue_index)
            name = cp.get_utf8(f.name_index)
            desc = cp.get_utf8(f.descriptor_index)
            self.statics[(name, desc)] = val

        # 3) Detecta <clinit>()V
        m = self.find_method("<clinit>", "()V")
        if m:
            self.clinit = m
            self.clinit_code = self._extract_code(m)

        self.status = "linked"

def _resolve_constantvalue(cp: ConstantPool, idx: int) -> VMValue:
    e = cp.get(idx)
    tname = type(e).__name__

    # Integer/Float/Long/Double — tags já foram normalizados no parser
    from capivara.classfile.constant_pool import CpInteger, CpFloat, CpLong, CpDouble, CpString
    if isinstance(e, CpInteger):
        return make_int(e.value)
    if isinstance(e, CpFloat):
        return make_float(e.value)
    if isinstance(e, CpLong):
        return make_long(e.value)
    if isinstance(e, CpDouble):
        return make_double(e.value)
    if isinstance(e, CpString):
        s_utf = cp.get_utf8(e.string_index)
        # Para agora, retorna uma "ref" abstrata (string pool será ligado no loader)
        # O loader substituirá esse ref por um id do StringPool.
        # Aqui devolvemos um ref None com "sombra" textual — faremos binding no loader.
        # Para simplificar neste passo, retornaremos ref(None); o loader irá ajustar.
        return make_ref(None)
    raise TypeError(f"ConstantValue não suportado para {tname}")