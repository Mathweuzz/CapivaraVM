from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

# Representações simples para operandos e locais
# Mantemos tipo lógico (tag) e valor Python.

@dataclass
class VMValue:
    tag: str   # 'int','long','float','double','ref'
    value: Any

@dataclass
class VMTop:
    """Placeholder para o 2º slot de long/double em locals/stack."""
    pass

TOP = VMTop()

def as_int32(v: int) -> int:
    v &= 0xFFFFFFFF
    # signed int32
    return v if v < 0x80000000 else v - (1 << 32)

def as_long(v: int) -> int:
    v &= 0xFFFFFFFFFFFFFFFF
    return v if v < (1 << 63) else v - (1 << 64)

def make_int(v: int) -> VMValue:
    return VMValue("int", as_int32(int(v)))

def make_long(v: int) -> VMValue:
    return VMValue("long", as_long(int(v)))

def make_float(v: float) -> VMValue:
    return VMValue("float", float(v))

def make_double(v: float) -> VMValue:
    return VMValue("double", float(v))

def make_ref(obj_id: Optional[int]) -> VMValue:
    # obj_id=None representa null
    return VMValue("ref", obj_id)