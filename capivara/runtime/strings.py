from __future__ import annotations
from typing import Dict

class StringPool:
    """
    Pool de strings (intern). Para agora, mapeia texto -> id inteiro estável.
    Em passos futuros, retornaremos objetos reais da heap Java.
    """
    def __init__(self):
        self._s2id: Dict[str, int] = {}
        self._id2s: Dict[int, str] = {}
        self._next_id: int = 1

    def intern(self, s: str) -> int:
        if s in self._s2id:
            return self._s2id[s]
        i = self._next_id
        self._next_id += 1
        self._s2id[s] = i
        self._id2s[i] = s
        return i

    def get(self, sid: int) -> str:
        return self._id2s[sid]
