from __future__ import annotations
import os
from typing import List, Optional

class ClassPath:
    """
    Classpath por diretórios. Dado um nome binário (ex.: 'pkg/Classe'),
    retorna os bytes do .class se existir.
    """
    def __init__(self, entries: List[str]):
        self.entries = entries

    def _candidate_paths(self, binary_name: str):
        rel = f"{binary_name}.class"
        for base in self.entries:
            yield os.path.join(base, rel)

    def read_class_bytes(self, binary_name: str) -> Optional[bytes]:
        for p in self._candidate_paths(binary_name):
            if os.path.isfile(p):
                with open(p, "rb") as f:
                    return f.read()
        return None