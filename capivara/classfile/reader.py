from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, List
from capivara.util.bytesio import ByteStream
from capivara.util import opcodes as OP
from capivara.classfile.constant_pool import (
    ConstantPool,
    CpUtf8, CpInteger, CpFloat, CpLong, CpDouble,
    CpClass, CpString, CpNameAndType,
    CpFieldref, CpMethodref, CpInterfaceMethodref,
    CpPlaceholder,
)
from capivara.classfile.members import parse_fields, parse_methods, FieldInfo, MethodInfo
from capivara.classfile.attributes import parse_attributes, AttributeInfo

MAGIC = 0xCAFEBABE

@dataclass
class ClassFile:
    magic: int
    minor_version: int
    major_version: int
    constant_pool: ConstantPool

    access_flags: int
    this_class: int
    super_class: int
    interfaces: List[int]

    fields: List[FieldInfo]
    methods: List[MethodInfo]
    attributes: List[AttributeInfo]

def _read_cp_entry(bs: ByteStream) -> Tuple[int, object]:
    tag = bs.read_u1()

    if tag == OP.CP_Utf8:
        length = bs.read_u2()
        raw = bs.read_bytes(length)
        try:
            s = raw.decode("utf-8")
        except UnicodeDecodeError:
            s = raw.decode("utf-8", errors="replace")
        return tag, CpUtf8(tag, s)

    if tag == OP.CP_Integer:
        v = bs.read_u4()
        if v & 0x80000000:
            v = v - (1 << 32)
        return tag, CpInteger(tag, v)

    if tag == OP.CP_Float:
        v = bs.read_f4()
        return tag, CpFloat(tag, v)

    if tag == OP.CP_Long:
        u = bs.read_u8()
        if u & 0x8000000000000000:
            u = u - (1 << 64)
        return tag, CpLong(tag, u)

    if tag == OP.CP_Double:
        v = bs.read_f8()
        return tag, CpDouble(tag, v)

    if tag == OP.CP_Class:
        name_index = bs.read_u2()
        return tag, CpClass(tag, name_index)

    if tag == OP.CP_String:
        string_index = bs.read_u2()
        return tag, CpString(tag, string_index)

    if tag == OP.CP_NameAndType:
        name_index = bs.read_u2()
        desc_index = bs.read_u2()
        return tag, CpNameAndType(tag, name_index, desc_index)

    if tag == OP.CP_Fieldref:
        class_index = bs.read_u2()
        nt_index = bs.read_u2()
        return tag, CpFieldref(tag, class_index, nt_index)

    if tag == OP.CP_Methodref:
        class_index = bs.read_u2()
        nt_index = bs.read_u2()
        return tag, CpMethodref(tag, class_index, nt_index)

    if tag == OP.CP_InterfaceMethodref:
        class_index = bs.read_u2()
        nt_index = bs.read_u2()
        return tag, CpInterfaceMethodref(tag, class_index, nt_index)

    raise NotImplementedError(f"Tag de Constant Pool não suportada no Passo 2: {tag}")

def read_classfile(data: bytes) -> ClassFile:
    bs = ByteStream(data)
    magic = bs.read_u4()
    if magic != MAGIC:
        raise ValueError(f"Arquivo .class inválido: magic=0x{magic:08X} (esperado 0xCAFEBABE)")
    minor = bs.read_u2()
    major = bs.read_u2()
    if major != 52:
        raise ValueError(f"Versão major não suportada neste passo: {major} (esperado 52)")

    cp_count = bs.read_u2()
    cp = ConstantPool(cp_count)
    i = 1
    while i <= cp_count - 1:
        tag, entry = _read_cp_entry(bs)
        cp.set(i, entry)
        if tag in (OP.CP_Long, OP.CP_Double):
            i += 1
            cp.set(i, CpPlaceholder(tag))
        i += 1

    # ===== Restante da estrutura do ClassFile =====
    access_flags = bs.read_u2()
    this_class = bs.read_u2()
    super_class = bs.read_u2()

    interfaces_count = bs.read_u2()
    interfaces: List[int] = [bs.read_u2() for _ in range(interfaces_count)]

    fields_count = bs.read_u2()
    fields = parse_fields(bs, cp, fields_count)

    methods_count = bs.read_u2()
    methods = parse_methods(bs, cp, methods_count)

    attributes_count = bs.read_u2()
    attributes = parse_attributes(bs, cp, attributes_count)

    return ClassFile(
        magic=magic,
        minor_version=minor,
        major_version=major,
        constant_pool=cp,
        access_flags=access_flags,
        this_class=this_class,
        super_class=super_class,
        interfaces=interfaces,
        fields=fields,
        methods=methods,
        attributes=attributes,
    )