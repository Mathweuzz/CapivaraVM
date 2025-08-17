from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple
from capivara.util.bytesio import ByteStream
from capivara.util import opcodes as OP
from capivara.classfile.constant_pool import (
    ConstantPool,
    CpUtf8, CpInteger, CpFloat, CpLong, CpDouble,
    CpClass, CpString, CpNameAndType,
    CpFieldref, CpMethodref, CpInterfaceMethodref,
    CpPlaceholder,
)

MAGIC = 0xCAFEBABE

@dataclass
class ClassFile:
    magic: int
    minor_version: int
    major_version: int
    constant_pool: ConstantPool
    # (Demais campos serão adicionados no Passo 3)

def _read_cp_entry(bs: ByteStream) -> Tuple[int, object]:
    tag = bs.read_u1()

    if tag == OP.CP_Utf8:
        length = bs.read_u2()
        raw = bs.read_bytes(length)
        # Simplificação: decodifica como UTF-8 "normal".
        # Em Java, o formato é MUTF-8, mas para nomes ASCII/UTF8 simples funciona.
        # Ajustaremos se necessário quando surgirem casos com NUL/surrogates.
        try:
            s = raw.decode("utf-8")
        except UnicodeDecodeError:
            s = raw.decode("utf-8", errors="replace")
        return tag, CpUtf8(tag, s)

    if tag == OP.CP_Integer:
        v = bs.read_u4()
        # converte para signed 32-bit
        if v & 0x80000000:
            v = v - (1 << 32)
        return tag, CpInteger(tag, v)

    if tag == OP.CP_Float:
        # IEEE 754 float32
        bs.pos -= 0  # apenas por simetria de leitura
        v = bs.read_f4()
        return tag, CpFloat(tag, v)

    if tag == OP.CP_Long:
        u = bs.read_u8()
        # signed 64-bit
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

    # Tags não suportadas neste passo — lançamos exceção clara.
    raise NotImplementedError(f"Tag de Constant Pool não suportada no Passo 2: {tag}")

def read_classfile(data: bytes) -> ClassFile:
    bs = ByteStream(data)
    magic = bs.read_u4()
    if magic != MAGIC:
        raise ValueError(f"Arquivo .class inválido: magic=0x{magic:08X} (esperado 0xCAFEBABE)")
    minor = bs.read_u2()
    major = bs.read_u2()
    # Aceitamos 52 (Java 8). Outros majors serão suportados mais tarde.
    if major != 52:
        # Não bloqueamos, mas avisamos cedo — Passo 2 foca em 52.
        raise ValueError(f"Versão major não suportada neste passo: {major} (esperado 52)")

    cp_count = bs.read_u2()
    cp = ConstantPool(cp_count)
    i = 1
    while i <= cp_count - 1:
        tag, entry = _read_cp_entry(bs)
        cp.set(i, entry)
        if tag in (OP.CP_Long, OP.CP_Double):
            # Reserva a próxima entrada como placeholder, conforme a especificação.
            i += 1
            cp.set(i, CpPlaceholder(tag))
        i += 1

    # Demais campos (access_flags, this_class, super_class...) virão no Passo 3.
    return ClassFile(
        magic=magic,
        minor_version=minor,
        major_version=major,
        constant_pool=cp,
    )