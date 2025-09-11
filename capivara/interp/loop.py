from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Tuple

from capivara.util import opcodes as OP
from capivara.runtime.frame import Frame
from capivara.util.descriptors import parse_method_descriptor, parse_field_descriptor, BaseType, ObjectType, ArrayType
from capivara.loader.loader import ClassLoader
from capivara.runtime.klass import RuntimeClass
from capivara.runtime.heap import VMObject
from capivara.classfile.constant_pool import (
    ConstantPool, CpMethodref, CpClass, CpNameAndType, CpFieldref
)
from capivara.classfile.attributes import CodeAttribute
from capivara.util import flags as FL

@dataclass
class ExecResult:
    kind: str          # "void" | "int"
    int_value: Optional[int] = None

class Interpreter:
    """
    Intérprete com invocações e objetos básicos.
    """
    def __init__(self, loader: ClassLoader):
        self.loader = loader

    # ===== utils numéricas =====
    @staticmethod
    def _s1(b: int) -> int:
        return b - 256 if b >= 128 else b

    @staticmethod
    def _s2(hi: int, lo: int) -> int:
        v = (hi << 8) | lo
        return v - 65536 if v >= 32768 else v

    @staticmethod
    def _idiv(a: int, b: int) -> int:
        if b == 0:
            raise ZeroDivisionError("divisão por zero (idiv)")
        return int(a / b)

    @staticmethod
    def _irem(a: int, b: int) -> int:
        if b == 0:
            raise ZeroDivisionError("divisão por zero (irem)")
        return a - int(a / b) * b

    # ===== resolução CP =====
    def _resolve_methodref(self, cp: ConstantPool, index: int) -> Tuple[str, str, str]:
        e = cp.get(index)
        if not isinstance(e, CpMethodref):
            raise TypeError("índice não é Methodref")
        cls = cp.get(e.class_index)
        assert isinstance(cls, CpClass)
        owner = cp.get_utf8(cls.name_index)
        nt = cp.get(e.name_and_type_index)
        assert isinstance(nt, CpNameAndType)
        name = cp.get_utf8(nt.name_index)
        desc = cp.get_utf8(nt.descriptor_index)
        return owner, name, desc

    def _resolve_fieldref(self, cp: ConstantPool, index: int) -> Tuple[str, str, str]:
        e = cp.get(index)
        if not isinstance(e, CpFieldref):
            raise TypeError("índice não é Fieldref")
        cls = cp.get(e.class_index)
        assert isinstance(cls, CpClass)
        owner = cp.get_utf8(cls.name_index)
        nt = cp.get(e.name_and_type_index)
        assert isinstance(nt, CpNameAndType)
        name = cp.get_utf8(nt.name_index)
        desc = cp.get_utf8(nt.descriptor_index)
        return owner, name, desc

    def _lookup_static_in_hierarchy(self, owner_name: str, name: str, desc: str) -> Tuple[RuntimeClass, CodeAttribute]:
        rc = self.loader.load_class(owner_name)
        while True:
            m = rc.find_method(name, desc)
            if m and (m.access_flags & FL.ACC_STATIC):
                code: CodeAttribute | None = None
                for a in m.attributes:
                    if isinstance(a, CodeAttribute):
                        code = a
                        break
                if not code:
                    raise RuntimeError("método alvo sem atributo Code")
                return rc, code
            if not rc.super_name:
                break
            rc = self.loader.load_class(rc.super_name)
        raise LookupError(f"método não encontrado (static): {owner_name}.{name}{desc}")

    def _lookup_instance_in_hierarchy(self, rc: RuntimeClass, name: str, desc: str) -> Tuple[RuntimeClass, CodeAttribute]:
        cur = rc
        while True:
            m = cur.find_method(name, desc)
            if m and (m.access_flags & FL.ACC_STATIC) == 0:
                code: CodeAttribute | None = None
                for a in m.attributes:
                    if isinstance(a, CodeAttribute):
                        code = a
                        break
                if not code:
                    raise RuntimeError("método alvo sem atributo Code")
                return cur, code
            if not cur.super_name:
                break
            cur = self.loader.load_class(cur.super_name)
        raise LookupError(f"método não encontrado (instance): {rc.name}.{name}{desc}")

    def _lookup_field_in_hierarchy(self, owner_name: str, name: str, desc: str, expect_static: bool) -> Tuple[RuntimeClass, bool]:
        rc = self.loader.load_class(owner_name)
        while True:
            cp = rc.cf.constant_pool
            for f in rc.cf.fields:
                is_static = (f.access_flags & FL.ACC_STATIC) != 0
                if is_static != expect_static:
                    continue
                if cp.get_utf8(f.name_index) == name and cp.get_utf8(f.descriptor_index) == desc:
                    return rc, is_static
            if not rc.super_name:
                break
            rc = self.loader.load_class(rc.super_name)
        kind = "static" if expect_static else "instance"
        raise LookupError(f"campo não encontrado ({kind}): {owner_name}.{name}{desc}")

    # ===== Execução de um método (frame) =====
    def _run_frame(self, rc: RuntimeClass, code: CodeAttribute, frame: Frame) -> ExecResult:
        cp = rc.cf.constant_pool
        code_bytes = code.code
        pc = 0
        n = len(code_bytes)

        while pc < n:
            op = code_bytes[pc]
            pc += 1

            # ===== Constantes / refs =====
            if op == OP.NOP:
                continue
            elif op == OP.ACONST_NULL:
                frame.push_ref(None)
            elif OP.ICONST_M1 <= op <= OP.ICONST_5:
                v = -1 if op == OP.ICONST_M1 else (op - OP.ICONST_0)
                frame.push_int(v)
            elif op == OP.BIPUSH:
                b = code_bytes[pc]; pc += 1
                frame.push_int(self._s1(b))
            elif op == OP.SIPUSH:
                hi = code_bytes[pc]; lo = code_bytes[pc+1]; pc += 2
                frame.push_int(self._s2(hi, lo))

            # ===== Loads/Stores (int/ref) =====
            elif op == OP.ILOAD:
                idx = code_bytes[pc]; pc += 1
                frame.push_int(frame.get_local_int(idx))
            elif op in (OP.ILOAD_0, OP.ILOAD_1, OP.ILOAD_2, OP.ILOAD_3):
                idx = op - OP.ILOAD_0
                frame.push_int(frame.get_local_int(idx))
            elif op == OP.ISTORE:
                idx = code_bytes[pc]; pc += 1
                v = frame.pop_int()
                frame.set_local_int(idx, v)
            elif op in (OP.ISTORE_0, OP.ISTORE_1, OP.ISTORE_2, OP.ISTORE_3):
                idx = op - OP.ISTORE_0
                v = frame.pop_int()
                frame.set_local_int(idx, v)

            elif op == OP.ALOAD:
                idx = code_bytes[pc]; pc += 1
                frame.push_ref(frame.get_local_ref(idx))
            elif op in (OP.ALOAD_0, OP.ALOAD_1, OP.ALOAD_2, OP.ALOAD_3):
                idx = op - OP.ALOAD_0
                frame.push_ref(frame.get_local_ref(idx))
            elif op == OP.ASTORE:
                idx = code_bytes[pc]; pc += 1
                r = frame.pop_ref()
                frame.set_local_ref(idx, r)
            elif op in (OP.ASTORE_0, OP.ASTORE_1, OP.ASTORE_2, OP.ASTORE_3):
                idx = op - OP.ASTORE_0
                r = frame.pop_ref()
                frame.set_local_ref(idx, r)

            # ===== Pilha: dup/pop =====
            elif op == OP.DUP:
                top = frame.pop_slot()
                frame.ostack.append(top)
                frame.ostack.append(top)
            elif op == OP.POP:
                top = frame.pop_slot()
                if getattr(top, "__class__", None).__name__ == "VMTop":
                    # pop erroneamente sobre 2-slot; remover também o valor
                    frame.pop_slot()

            # ===== Aritmética =====
            elif op == OP.IADD:
                b = frame.pop_int(); a = frame.pop_int()
                frame.push_int(a + b)
            elif op == OP.ISUB:
                b = frame.pop_int(); a = frame.pop_int()
                frame.push_int(a - b)
            elif op == OP.IMUL:
                b = frame.pop_int(); a = frame.pop_int()
                frame.push_int(a * b)
            elif op == OP.IDIV:
                b = frame.pop_int(); a = frame.pop_int()
                frame.push_int(self._idiv(a, b))
            elif op == OP.IREM:
                b = frame.pop_int(); a = frame.pop_int()
                frame.push_int(self._irem(a, b))
            elif op == OP.IINC:
                idx = code_bytes[pc]; const = self._s1(code_bytes[pc+1]); pc += 2
                cur = frame.get_local_int(idx)
                frame.set_local_int(idx, cur + const)
            elif op == OP.INEG:
                v = frame.pop_int()
                frame.push_int(-v)

            # ===== Condicionais =====
            elif op in (OP.IFEQ, OP.IFNE, OP.IFLT, OP.IFGE, OP.IFGT, OP.IFLE):
                hi = code_bytes[pc]; lo = code_bytes[pc+1]; pc += 2
                off = self._s2(hi, lo)
                v = frame.pop_int()
                cond = (
                    (op == OP.IFEQ and v == 0) or
                    (op == OP.IFNE and v != 0) or
                    (op == OP.IFLT and v <  0) or
                    (op == OP.IFGE and v >= 0) or
                    (op == OP.IFGT and v >  0) or
                    (op == OP.IFLE and v <= 0)
                )
                if cond:
                    pc = pc + off - 3
            elif op in (OP.IF_ICMPEQ, OP.IF_ICMPNE, OP.IF_ICMPLT, OP.IF_ICMPGE, OP.IF_ICMPGT, OP.IF_ICMPLE):
                hi = code_bytes[pc]; lo = code_bytes[pc+1]; pc += 2
                off = self._s2(hi, lo)
                b = frame.pop_int(); a = frame.pop_int()
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
                hi = code_bytes[pc]; lo = code_bytes[pc+1]; pc += 2
                off = self._s2(hi, lo)
                pc = pc + off - 3

            # ===== Campos estáticos =====
            elif op == OP.GETSTATIC:
                idx = (code_bytes[pc] << 8) | code_bytes[pc+1]; pc += 2
                owner, name, desc = self._resolve_fieldref(cp, idx)
                decl_rc, _ = self._lookup_field_in_hierarchy(owner, name, desc, expect_static=True)
                val = decl_rc.statics[(name, desc)]
                t = parse_field_descriptor(desc)
                if isinstance(t, BaseType) and t.code == "I":
                    frame.push_int(val.value)
                else:
                    # array/obj
                    frame.push_ref(val.value)
            elif op == OP.PUTSTATIC:
                idx = (code_bytes[pc] << 8) | code_bytes[pc+1]; pc += 2
                owner, name, desc = self._resolve_fieldref(cp, idx)
                decl_rc, _ = self._lookup_field_in_hierarchy(owner, name, desc, expect_static=True)
                t = parse_field_descriptor(desc)
                if isinstance(t, BaseType) and t.code == "I":
                    v = frame.pop_int()
                else:
                    v = frame.pop_ref()
                decl_rc.statics[(name, desc)].value = v

            # ===== Campos de instância =====
            elif op == OP.GETFIELD:
                idx = (code_bytes[pc] << 8) | code_bytes[pc+1]; pc += 2
                owner, name, desc = self._resolve_fieldref(cp, idx)
                ref = frame.pop_ref()
                if ref is None:
                    raise RuntimeError("NullPointerException (getfield)")
                obj = self.loader.heap.get(ref)
                decl_rc, _ = self._lookup_field_in_hierarchy(owner, name, desc, expect_static=False)
                val = obj.fields[(decl_rc.name, name, desc)]
                t = parse_field_descriptor(desc)
                if isinstance(t, BaseType) and t.code == "I":
                    frame.push_int(val.value)
                else:
                    frame.push_ref(val.value)
            elif op == OP.PUTFIELD:
                idx = (code_bytes[pc] << 8) | code_bytes[pc+1]; pc += 2
                owner, name, desc = self._resolve_fieldref(cp, idx)
                t = parse_field_descriptor(desc)
                if isinstance(t, BaseType) and t.code == "I":
                    v = frame.pop_int()
                else:
                    v = frame.pop_ref()
                ref = frame.pop_ref()
                if ref is None:
                    raise RuntimeError("NullPointerException (putfield)")
                obj = self.loader.heap.get(ref)
                decl_rc, _ = self._lookup_field_in_hierarchy(owner, name, desc, expect_static=False)
                obj.fields[(decl_rc.name, name, desc)].value = v

            # ===== Invocações =====
            elif op == OP.INVOKESTATIC:
                idx_hi = code_bytes[pc]; idx_lo = code_bytes[pc+1]; pc += 2
                index = (idx_hi << 8) | idx_lo
                owner, name, desc = self._resolve_methodref(cp, index)
                target_rc, code_attr = self._lookup_static_in_hierarchy(owner, name, desc)
                params, ret = parse_method_descriptor(desc)
                arg_vals: List[int] = []
                for p in reversed(params):
                    if isinstance(p, BaseType) and p.code == "I":
                        arg_vals.append(frame.pop_int())
                    else:
                        raise NotImplementedError("apenas parâmetros int neste passo")
                arg_vals.reverse()
                callee = Frame(max_locals=code_attr.max_locals, max_stack=code_attr.max_stack)
                for i, v in enumerate(arg_vals):
                    callee.set_local_int(i, v)
                res = self._run_frame(target_rc, code_attr, callee)
                if isinstance(ret, BaseType) and ret.code == "I":
                    frame.push_int(res.int_value if res.int_value is not None else 0)
                elif isinstance(ret, BaseType) and ret.code == "V":
                    pass
                else:
                    raise NotImplementedError("retornos não-int/void virão depois")

            elif op == OP.INVOKESPECIAL:
                idx = (code_bytes[pc] << 8) | code_bytes[pc+1]; pc += 2
                owner, name, desc = self._resolve_methodref(cp, idx)
                # construtores e super chamadas: usa classe resolvida (owner)
                target_rc = self.loader.load_class(owner)

                params, ret = parse_method_descriptor(desc)
                # coletar args (direita->esquerda) e 'this'
                arg_vals: List[int] = []
                for p in reversed(params):
                    if isinstance(p, BaseType) and p.code == "I":
                        arg_vals.append(frame.pop_int())
                    else:
                        raise NotImplementedError("apenas parâmetros int neste passo")
                arg_vals.reverse()
                this_ref = frame.pop_ref()
                if this_ref is None:
                    raise RuntimeError("NullPointerException (invokespecial)")

                # localizar Code do método na hierarquia do owner
                _, code_attr = self._lookup_instance_in_hierarchy(target_rc, name, desc)

                callee = Frame(max_locals=code_attr.max_locals, max_stack=code_attr.max_stack)
                callee.set_local_ref(0, this_ref)
                for i, v in enumerate(arg_vals, start=1):
                    callee.set_local_int(i, v)

                res = self._run_frame(target_rc, code_attr, callee)
                # construtor/void -> nada a empilhar

            elif op == OP.INVOKEVIRTUAL:
                idx = (code_bytes[pc] << 8) | code_bytes[pc+1]; pc += 2
                owner, name, desc = self._resolve_methodref(cp, idx)
                params, ret = parse_method_descriptor(desc)
                arg_vals: List[int] = []
                for p in reversed(params):
                    if isinstance(p, BaseType) and p.code == "I":
                        arg_vals.append(frame.pop_int())
                    else:
                        raise NotImplementedError("apenas parâmetros int neste passo")
                arg_vals.reverse()
                this_ref = frame.pop_ref()
                if this_ref is None:
                    raise RuntimeError("NullPointerException (invokevirtual)")
                this_obj = self.loader.heap.get(this_ref)
                dyn_rc = self.loader.load_class(this_obj.class_name)

                # despacho dinâmico
                _, code_attr = self._lookup_instance_in_hierarchy(dyn_rc, name, desc)

                callee = Frame(max_locals=code_attr.max_locals, max_stack=code_attr.max_stack)
                callee.set_local_ref(0, this_ref)
                for i, v in enumerate(arg_vals, start=1):
                    callee.set_local_int(i, v)

                res = self._run_frame(dyn_rc, code_attr, callee)
                if isinstance(ret, BaseType) and ret.code == "I":
                    frame.push_int(res.int_value if res.int_value is not None else 0)
                elif isinstance(ret, BaseType) and ret.code == "V":
                    pass
                else:
                    raise NotImplementedError("retornos não-int/void virão depois")

            # ===== Alocação =====
            elif op == OP.NEW:
                idx = (code_bytes[pc] << 8) | code_bytes[pc+1]; pc += 2
                e = cp.get(idx); assert isinstance(e, CpClass)
                class_name = cp.get_utf8(e.name_index)
                rc_new = self.loader.load_class(class_name)
                oid = self.loader.heap.new_object(rc_new, self.loader)
                frame.push_ref(oid)

            # ===== Retornos =====
            elif op == OP.IRETURN:
                v = frame.pop_int()
                return ExecResult("int", v)
            elif op == OP.RETURN:
                return ExecResult("void")

            else:
                raise NotImplementedError(f"Opcode 0x{op:02x} não suportado neste passo")

        return ExecResult("void")

    # ===== API externa =====
    def execute_method(self, rc: RuntimeClass, name: str, desc: str) -> ExecResult:
        m = rc.find_method(name, desc)
        if not m:
            raise LookupError(f"método não encontrado: {rc.name}.{name}{desc}")
        code: CodeAttribute | None = None
        for a in m.attributes:
            if isinstance(a, CodeAttribute):
                code = a
                break
        if not code:
            raise RuntimeError("método sem atributo Code")
        frame = Frame(max_locals=code.max_locals, max_stack=code.max_stack)
        return self._run_frame(rc, code, frame)

    def execute_static_entry(self, main_bin: str, name: str, desc: str) -> ExecResult:
        rc = self.loader.load_class(main_bin)
        return self.execute_method(rc, name, desc)
