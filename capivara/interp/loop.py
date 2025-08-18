from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from capivara.util import opcodes as OP
from capivara.runtime.frame import Frame, StackUnderflowError
from capivara.runtime.values import make_int

@dataclass
class ExecResult:
    kind: str          # "void" | "int"
    int_value: Optional[int] = None

class Interpreter:
    """
    Laço do intérprete p/ subset de inteiros e controle de fluxo.
    Método alvo deve ser 'static' e sem argumentos (neste passo).
    """
    def __init__(self):
        pass

    @staticmethod
    def _s1(b: int) -> int:
        # converte byte (0..255) para signed (-128..127)
        return b - 256 if b >= 128 else b

    @staticmethod
    def _s2(hi: int, lo: int) -> int:
        # 16-bit signed
        v = (hi << 8) | lo
        return v - 65536 if v >= 32768 else v

    @staticmethod
    def _idiv(a: int, b: int) -> int:
        if b == 0:
            raise ZeroDivisionError("divisão por zero (idiv)")
        return int(a / b)  # trunca para zero

    @staticmethod
    def _irem(a: int, b: int) -> int:
        if b == 0:
            raise ZeroDivisionError("divisão por zero (irem)")
        return a - int(a / b) * b  # resto com sinal do dividendo (semântica Java)

    def exec_code(self, code: bytes, max_locals: int, max_stack: int) -> ExecResult:
        fr = Frame(max_locals=max_locals, max_stack=max_stack)
        # Nota: Locals já ficam em zero/null por padrão em Java; nosso Frame inicia com None.
        # Para este passo, só usaremos locals explicitamente setados por bytecodes.

        pc = 0
        n = len(code)
        while pc < n:
            op = code[pc]
            pc += 1

            # ===== Constantes =====
            if op == OP.NOP:
                continue
            elif OP.ICONST_M1 <= op <= OP.ICONST_5:
                v = -1 if op == OP.ICONST_M1 else (op - OP.ICONST_0)
                fr.push_int(v)
            elif op == OP.BIPUSH:
                b = code[pc]; pc += 1
                fr.push_int(self._s1(b))
            elif op == OP.SIPUSH:
                hi = code[pc]; lo = code[pc+1]; pc += 2
                fr.push_int(self._s2(hi, lo))

            # ===== Loads/Stores =====
            elif op == OP.ILOAD:
                idx = code[pc]; pc += 1
                fr.push_int(fr.get_local_int(idx))
            elif op in (OP.ILOAD_0, OP.ILOAD_1, OP.ILOAD_2, OP.ILOAD_3):
                idx = op - OP.ILOAD_0
                fr.push_int(fr.get_local_int(idx))
            elif op == OP.ISTORE:
                idx = code[pc]; pc += 1
                v = fr.pop_int()
                fr.set_local_int(idx, v)
            elif op in (OP.ISTORE_0, OP.ISTORE_1, OP.ISTORE_2, OP.ISTORE_3):
                idx = op - OP.ISTORE_0
                v = fr.pop_int()
                fr.set_local_int(idx, v)
            elif op == OP.IINC:
                idx = code[pc]; const = self._s1(code[pc+1]); pc += 2
                cur = fr.get_local_int(idx)
                fr.set_local_int(idx, cur + const)
            elif op == OP.INEG:
                v = fr.pop_int()
                fr.push_int(-v)

            # ===== Aritmética =====
            elif op == OP.IADD:
                b = fr.pop_int(); a = fr.pop_int()
                fr.push_int(a + b)
            elif op == OP.ISUB:
                b = fr.pop_int(); a = fr.pop_int()
                fr.push_int(a - b)
            elif op == OP.IMUL:
                b = fr.pop_int(); a = fr.pop_int()
                fr.push_int(a * b)
            elif op == OP.IDIV:
                b = fr.pop_int(); a = fr.pop_int()
                fr.push_int(self._idiv(a, b))
            elif op == OP.IREM:
                b = fr.pop_int(); a = fr.pop_int()
                fr.push_int(self._irem(a, b))

            # ===== Condicionais (1 operando) =====
            elif op in (OP.IFEQ, OP.IFNE, OP.IFLT, OP.IFGE, OP.IFGT, OP.IFLE):
                hi = code[pc]; lo = code[pc+1]; pc += 2
                off = self._s2(hi, lo)
                v = fr.pop_int()
                cond = (
                    (op == OP.IFEQ and v == 0) or
                    (op == OP.IFNE and v != 0) or
                    (op == OP.IFLT and v <  0) or
                    (op == OP.IFGE and v >= 0) or
                    (op == OP.IFGT and v >  0) or
                    (op == OP.IFLE and v <= 0)
                )
                if cond:
                    pc = pc + off - 3  # -3 pois já consumimos opcode+2 bytes do offset

            # ===== Condicionais (2 operandos) =====
            elif op in (OP.IF_ICMPEQ, OP.IF_ICMPNE, OP.IF_ICMPLT, OP.IF_ICMPGE, OP.IF_ICMPGT, OP.IF_ICMPLE):
                hi = code[pc]; lo = code[pc+1]; pc += 2
                off = self._s2(hi, lo)
                b = fr.pop_int(); a = fr.pop_int()
                cond = (
                    (op == OP.IF_ICMPEQ and a == b) or
                    (op == OP.IF_ICMPNE and a != b) or
                    (op == OP.IF_ICMPLT and a <  b) or
                    (op == OP.IF_ICMPGE and a >= b) or
                    (op == OP.IF_ICMPGT and a >  b) or
                    (op == OP.IF_ICMPLE and a <= b)
                )
                if cond:
                    pc = pc + off - 3

            # ===== Goto =====
            elif op == OP.GOTO:
                hi = code[pc]; lo = code[pc+1]; pc += 2
                off = self._s2(hi, lo)
                pc = pc + off - 3

            # ===== Retornos =====
            elif op == OP.IRETURN:
                v = fr.pop_int()
                return ExecResult("int", v)
            elif op == OP.RETURN:
                return ExecResult("void")

            else:
                raise NotImplementedError(f"Opcode 0x{op:02x} não suportado neste passo")
        # Se sair do loop sem return:
        return ExecResult("void")