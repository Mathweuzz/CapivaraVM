from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple

class DescriptorError(ValueError):
    pass


@dataclass(frozen=True)
class BaseType:
    code: str  # 'I','J','F','D','B','C','S','Z','V'
    def width(self) -> int:
        # largura em slots de operand stack/locals
        return 2 if self.code in ("J", "D") else 1
    def __str__(self) -> str:
        return self.code

@dataclass(frozen=True)
class ObjectType:
    internal_name: str  # ex.: "java/lang/String"
    def width(self) -> int:
        return 1
    def __str__(self) -> str:
        return f"L{self.internal_name};"

@dataclass(frozen=True)
class ArrayType:
    dims: int
    component: TypeLike
    def width(self) -> int:
        return 1
    def __str__(self) -> str:
        return "[" * self.dims + str(self.component)

TypeLike = BaseType | ObjectType | ArrayType

_PRIMS = {
    "B": "byte",
    "C": "char",
    "D": "double",
    "F": "float",
    "I": "int",
    "J": "long",
    "S": "short",
    "Z": "boolean",
    "V": "void",
}

def _expect(cond: bool, msg: str, s: str, i: int) -> None:
    if not cond:
        raise DescriptorError(f"{msg} em pos={i} para '{s}'")

def _parse_field_type(s: str, i: int) -> Tuple[TypeLike, int]:
    ch = s[i]
    if ch in _PRIMS:
        return BaseType(ch), i + 1
    if ch == "L":
        j = s.find(";", i)
        _expect(j != -1, "faltou ';' do ObjectType", s, i)
        name = s[i + 1 : j]
        _expect(len(name) > 0, "nome de classe vazio", s, i)
        return ObjectType(name), j + 1
    if ch == "[":
        dims = 0
        while i < len(s) and s[i] == "[":
            dims += 1
            i += 1
        _expect(i < len(s), "array sem componente", s, i)
        comp, k = _parse_field_type(s, i)
        return ArrayType(dims, comp), k
    raise DescriptorError(f"tipo inválido '{ch}' em '{s}' pos={i}")

def parse_field_descriptor(s: str) -> TypeLike:
    _expect(len(s) > 0, "descritor vazio", s, 0)
    t, k = _parse_field_type(s, 0)
    _expect(k == len(s), "lixo após descritor de campo", s, k)
    return t

def parse_method_descriptor(s: str) -> Tuple[List[TypeLike], TypeLike]:
    _expect(len(s) >= 3 and s[0] == "(", "método deve iniciar com '('", s, 0)
    i = 1
    params: List[TypeLike] = []
    while i < len(s) and s[i] != ")":
        t, i = _parse_field_type(s, i)
        params.append(t)
    _expect(i < len(s) and s[i] == ")", "faltou ')'", s, i)
    i += 1
    _expect(i < len(s), "faltou tipo de retorno", s, i)
    ret, k = _parse_field_type(s, i)
    return params, ret
