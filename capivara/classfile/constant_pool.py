from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Union
from capivara.util import opcodes as OP

@dataclass
class CpInfo:
    tag: int

@dataclass
class CpUtf8(CpInfo):
    value: str

@dataclass
class CpInteger(CpInfo):
    value: int  # int32

@dataclass
class CpFloat(CpInfo):
    value: float

@dataclass
class CpLong(CpInfo):
    value: int  # int64

@dataclass
class CpDouble(CpInfo):
    value: float  # float64

@dataclass
class CpClass(CpInfo):
    name_index: int

@dataclass
class CpString(CpInfo):
    string_index: int

@dataclass
class CpNameAndType(CpInfo):
    name_index: int
    descriptor_index: int

@dataclass
class CpRef(CpInfo):
    class_index: int
    name_and_type_index: int

@dataclass
class CpFieldref(CpRef):
    pass

@dataclass
class CpMethodref(CpRef):
    pass

@dataclass
class CpInterfaceMethodref(CpRef):
    pass

# Placeholder para entradas 2-slot (Long/Double) — o índice existe mas não contém dado.
@dataclass
class CpPlaceholder(CpInfo):
    pass

CPEntry = Union[
    None,               # índice 0 não é usado
    CpInfo,
    CpUtf8, CpInteger, CpFloat, CpLong, CpDouble,
    CpClass, CpString, CpNameAndType,
    CpFieldref, CpMethodref, CpInterfaceMethodref,
    CpPlaceholder,
]

class ConstantPool:
    """
    Armazena a CP como lista 1-based (índice 0 = None).
    Oferece utilitários de obtenção e busca.
    """
    def __init__(self, size: int):
        # Tamanho reportado em file = constant_pool_count (entradas = count-1)
        self.entries: List[CPEntry] = [None] * size

    def __len__(self) -> int:
        return len(self.entries)

    def set(self, index: int, entry: CPEntry) -> None:
        self.entries[index] = entry

    def get(self, index: int) -> CPEntry:
        if not (0 < index < len(self.entries)):
            raise IndexError(f"CP index {index} fora do range 1..{len(self.entries)-1}")
        e = self.entries[index]
        if e is None:
            raise ValueError(f"CP index {index} é None/placeholder")
        return e

    def get_utf8(self, index: int) -> str:
        e = self.get(index)
        if isinstance(e, CpUtf8):
            return e.value
        raise TypeError(f"CP index {index} não é Utf8 (tag={e.tag})")

    def try_get_utf8(self, index: int) -> Optional[str]:
        try:
            return self.get_utf8(index)
        except Exception:
            return None

    def find_utf8(self, s: str) -> list[int]:
        """Retorna todos os índices Utf8 com valor == s."""
        out: list[int] = []
        for i, e in enumerate(self.entries):
            if isinstance(e, CpUtf8) and e.value == s:
                out.append(i)
        return out

    def as_debug_list(self) -> list[str]:
        """Lista amigável (para depuração/testes)."""
        lines = []
        for i, e in enumerate(self.entries):
            if i == 0:
                continue
            if e is None:
                lines.append(f"#{i:<3} <None>")
                continue
            t = type(e).__name__
            if isinstance(e, CpUtf8):
                lines.append(f"#{i:<3} {t} {e.value!r}")
            elif isinstance(e, (CpInteger, CpFloat, CpLong, CpDouble)):
                lines.append(f"#{i:<3} {t} {e.value!r}")
            elif isinstance(e, CpClass):
                lines.append(f"#{i:<3} {t} name_index={e.name_index}")
            elif isinstance(e, CpString):
                lines.append(f"#{i:<3} {t} string_index={e.string_index}")
            elif isinstance(e, CpNameAndType):
                lines.append(f"#{i:<3} {t} name_index={e.name_index} desc_index={e.descriptor_index}")
            elif isinstance(e, (CpFieldref, CpMethodref, CpInterfaceMethodref)):
                lines.append(f"#{i:<3} {t} class_index={e.class_index} nt_index={e.name_and_type_index}")
            else:
                lines.append(f"#{i:<3} {t}")
        return lines