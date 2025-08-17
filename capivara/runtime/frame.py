from __future__ import annotations
from typing import List, Tuple
from capivara.runtime.values import VMValue, VMTop, TOP, make_int, make_long, make_float, make_double, make_ref

class StackOverflowError(RuntimeError): ...
class StackUnderflowError(RuntimeError): ...
class LocalAccessError(RuntimeError): ...

class Frame:
    """
    Um frame com locals (tamanho max_locals) e operand_stack (capacidade max_stack).
    long/double ocupam 2 slots (com placeholder TOP).
    """
    def __init__(self, max_locals: int, max_stack: int):
        if max_locals < 0 or max_stack <= 0:
            raise ValueError("max_locals/max_stack inválidos")
        self.max_locals = max_locals
        self.max_stack = max_stack
        self.locals: List[object] = [None] * max_locals
        self.ostack: List[object] = []
        self.pc: int = 0  # program counter (placeholder neste passo)

    # ===== Helpers =====
    def _stack_size(self) -> int:
        # conta slots reais, incluindo TOPs
        return len(self.ostack)

    def _ensure_stack_space(self, slots: int):
        if self._stack_size() + slots > self.max_stack:
            raise StackOverflowError("operand stack overflow")

    def _ensure_local_index(self, index: int, width: int = 1):
        if index < 0 or index + width - 1 >= self.max_locals:
            raise LocalAccessError(f"índice de local inválido: {index} (width={width})")

    # ===== Push/Pop (operand stack) =====
    def push_int(self, v: int):
        self._ensure_stack_space(1)
        self.ostack.append(make_int(v))

    def push_long(self, v: int):
        self._ensure_stack_space(2)
        self.ostack.append(make_long(v))
        self.ostack.append(TOP)

    def push_float(self, v: float):
        self._ensure_stack_space(1)
        self.ostack.append(make_float(v))

    def push_double(self, v: float):
        self._ensure_stack_space(2)
        self.ostack.append(make_double(v))
        self.ostack.append(TOP)

    def push_ref(self, obj_id: int | None):
        self._ensure_stack_space(1)
        self.ostack.append(make_ref(obj_id))

    def pop_slot(self) -> object:
        if not self.ostack:
            raise StackUnderflowError("operand stack underflow")
        return self.ostack.pop()

    def pop_int(self) -> int:
        v = self._pop_oneslot_tag("int")
        return v.value

    def pop_float(self) -> float:
        v = self._pop_oneslot_tag("float")
        return v.value

    def pop_ref(self) -> int | None:
        v = self._pop_oneslot_tag("ref")
        return v.value

    def pop_long(self) -> int:
        return self._pop_twoslot_tag("long")

    def pop_double(self) -> float:
        return self._pop_twoslot_tag("double")

    def _pop_oneslot_tag(self, tag: str) -> VMValue:
        top = self.pop_slot()
        if isinstance(top, VMTop):
            raise StackUnderflowError("TOP inesperado no topo ao ler 1-slot")
        if not isinstance(top, VMValue) or top.tag != tag:
            raise StackUnderflowError(f"tipo no topo não é {tag}")
        return top

    def _pop_twoslot_tag(self, tag: str):
        # topo deve ser TOP, abaixo o valor
        top = self.pop_slot()
        if not isinstance(top, VMTop):
            raise StackUnderflowError("esperava TOP no topo para valor 2-slot")
        val = self.pop_slot()
        if isinstance(val, VMTop) or not isinstance(val, VMValue) or val.tag != tag:
            raise StackUnderflowError(f"abaixo de TOP não há {tag}")
        return val.value

    # ===== Locals =====
    def set_local_int(self, index: int, v: int):
        self._ensure_local_index(index, 1)
        self.locals[index] = make_int(v)

    def set_local_float(self, index: int, v: float):
        self._ensure_local_index(index, 1)
        self.locals[index] = make_float(v)

    def set_local_ref(self, index: int, obj_id: int | None):
        self._ensure_local_index(index, 1)
        self.locals[index] = make_ref(obj_id)

    def set_local_long(self, index: int, v: int):
        self._ensure_local_index(index, 2)
        self.locals[index] = make_long(v)
        self.locals[index + 1] = TOP

    def set_local_double(self, index: int, v: float):
        self._ensure_local_index(index, 2)
        self.locals[index] = make_double(v)
        self.locals[index + 1] = TOP

    def get_local_int(self, index: int) -> int:
        self._ensure_local_index(index, 1)
        val = self.locals[index]
        if not isinstance(val, VMValue) or val.tag != "int":
            raise LocalAccessError("local não contém int")
        return val.value

    def get_local_float(self, index: int) -> float:
        self._ensure_local_index(index, 1)
        val = self.locals[index]
        if not isinstance(val, VMValue) or val.tag != "float":
            raise LocalAccessError("local não contém float")
        return val.value

    def get_local_ref(self, index: int) -> int | None:
        self._ensure_local_index(index, 1)
        val = self.locals[index]
        if not isinstance(val, VMValue) or val.tag != "ref":
            raise LocalAccessError("local não contém ref")
        return val.value

    def get_local_long(self, index: int) -> int:
        self._ensure_local_index(index, 2)
        val = self.locals[index]
        nxt = self.locals[index + 1]
        if not (isinstance(val, VMValue) and val.tag == "long" and isinstance(nxt, VMTop)):
            raise LocalAccessError("layout inválido para long em locals")
        return val.value

    def get_local_double(self, index: int) -> float:
        self._ensure_local_index(index, 2)
        val = self.locals[index]
        nxt = self.locals[index + 1]
        if not (isinstance(val, VMValue) and val.tag == "double" and isinstance(nxt, VMTop)):
            raise LocalAccessError("layout inválido para double em locals")
        return val.value