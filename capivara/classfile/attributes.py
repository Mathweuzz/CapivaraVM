from __future__ import annotations
from dataclasses import dataclass
from typing import List
from capivara.util.bytesio import ByteStream
from capivara.classfile.constant_pool import ConstantPool

@dataclass
class AttributeInfo:
    name_index: int
    length: int

@dataclass
class ExceptionTableEntry:
    start_pc: int
    end_pc: int
    handler_pc: int
    catch_type: int  # 0 => catch-all (finally)

@dataclass
class CodeAttribute(AttributeInfo):
    max_stack: int
    max_locals: int
    code: bytes
    exception_table: List[ExceptionTableEntry]
    attributes: List[AttributeInfo]

@dataclass
class LineNumberEntry:
    start_pc: int
    line_number: int

@dataclass
class LineNumberTableAttribute(AttributeInfo):
    line_numbers: List[LineNumberEntry]

@dataclass
class SourceFileAttribute(AttributeInfo):
    sourcefile_index: int

@dataclass
class ConstantValueAttribute(AttributeInfo):
    constantvalue_index: int

@dataclass
class UnknownAttribute(AttributeInfo):
    info: bytes

def _parse_LineNumberTable(bs: ByteStream, name_index: int, length: int) -> LineNumberTableAttribute:
    table_len = bs.read_u2()
    entries: List[LineNumberEntry] = []
    for _ in range(table_len):
        entries.append(LineNumberEntry(bs.read_u2(), bs.read_u2()))
    return LineNumberTableAttribute(name_index, length, entries)

def _parse_Code(bs: ByteStream, cp: ConstantPool, name_index: int, length: int) -> CodeAttribute:
    max_stack = bs.read_u2()
    max_locals = bs.read_u2()
    code_length = bs.read_u4()
    code = bs.read_bytes(code_length)

    ex_len = bs.read_u2()
    ex_table: List[ExceptionTableEntry] = []
    for _ in range(ex_len):
        ex_table.append(ExceptionTableEntry(
            start_pc=bs.read_u2(),
            end_pc=bs.read_u2(),
            handler_pc=bs.read_u2(),
            catch_type=bs.read_u2(),
        ))

    attrs_count = bs.read_u2()
    nested: List[AttributeInfo] = []
    for _ in range(attrs_count):
        nested.append(parse_attribute(bs, cp))
    return CodeAttribute(name_index, length, max_stack, max_locals, code, ex_table, nested)

def _parse_SourceFile(bs: ByteStream, name_index: int, length: int) -> SourceFileAttribute:
    return SourceFileAttribute(name_index, length, sourcefile_index=bs.read_u2())

def _parse_ConstantValue(bs: ByteStream, name_index: int, length: int) -> ConstantValueAttribute:
    return ConstantValueAttribute(name_index, length, constantvalue_index=bs.read_u2())

def parse_attribute(bs: ByteStream, cp: ConstantPool) -> AttributeInfo:
    name_index = bs.read_u2()
    length = bs.read_u4()
    name = cp.get_utf8(name_index)

    if name == "Code":
        return _parse_Code(bs, cp, name_index, length)
    if name == "LineNumberTable":
        return _parse_LineNumberTable(bs, name_index, length)
    if name == "SourceFile":
        return _parse_SourceFile(bs, name_index, length)
    if name == "ConstantValue":
        return _parse_ConstantValue(bs, name_index, length)

    info = bs.read_bytes(length)
    return UnknownAttribute(name_index, length, info)

def parse_attributes(bs: ByteStream, cp: ConstantPool, count: int) -> List[AttributeInfo]:
    return [parse_attribute(bs, cp) for _ in range(count)]