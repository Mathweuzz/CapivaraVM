from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional

from capivara.runtime.values import VMValue
from capivara.runtime.klass import RuntimeClass, _default_static_value
from capivara.util import flags as FL

@dataclass
class VMObject:
    class_name: str
    fields: Dict[Tuple[str, str, str], VMValue] = field(default_factory=dict)
    # chave = (declaringClass, fieldName, fieldDesc)

class Heap:
    def __init__(self):
        self._next_id: int = 1
        self._objs: Dict[int, VMObject] = {}

    def get(self, obj_id: int) -> VMObject:
        return self._objs[obj_id]

    def new_object(self, rc: RuntimeClass, loader) -> int:
        """
        Aloca objeto da classe 'rc', inicializando todos os campos de instância
        (da classe e superclasses) com valor default.
        """
        oid = self._next_id
        self._next_id += 1
        obj = VMObject(class_name=rc.name)

        cur: Optional[RuntimeClass] = rc
        while cur is not None:
            cp = cur.cf.constant_pool
            for f in cur.cf.fields:
                if (f.access_flags & FL.ACC_STATIC) != 0:
                    continue
                name = cp.get_utf8(f.name_index)
                desc = cp.get_utf8(f.descriptor_index)
                obj.fields[(cur.name, name, desc)] = _default_static_value(desc)
            cur = loader.load_class(cur.super_name) if cur.super_name else None

        self._objs[oid] = obj
        return oid