from __future__ import annotations
from dataclasses import dataclass
from typing import List
from capivara.util.bytesio import ByteStream
from capivara.classfile.constant_pool import ConstantPool
from capivara.classfile.attributes import AttributeInfo, parse_attributes

@dataclass
class FieldInfo:
    access_flags: int
    name_index: int
    descriptor_index: int
    attributes: List[AttributeInfo]

@dataclass
class MethodInfo:
    access_flags: int
    name_index: int
    descriptor_index: int
    attributes: List[AttributeInfo]

def parse_field_info(bs: ByteStream, cp: ConstantPool) -> FieldInfo:
    af = bs.read_u2()
    name_index = bs.read_u2()
    desc_index = bs.read_u2()
    ac = bs.read_u2()
    attrs = parse_attributes(bs, cp, ac)
    return FieldInfo(af, name_index, desc_index, attrs)

def parse_method_info(bs: ByteStream, cp: ConstantPool) -> MethodInfo:
    af = bs.read_u2()
    name_index = bs.read_u2()
    desc_index = bs.read_u2()
    ac = bs.read_u2()
    attrs = parse_attributes(bs, cp, ac)
    return MethodInfo(af, name_index, desc_index, attrs)

def parse_fields(bs: ByteStream, cp: ConstantPool, count: int) -> List[FieldInfo]:
    return [parse_field_info(bs, cp) for _ in range(count)]

def parse_methods(bs: ByteStream, cp: ConstantPool, count: int) -> List[MethodInfo]:
    return [parse_method_info(bs, cp) for _ in range(count)]