from __future__ import annotations
import struct

class ByteStream:
    """
    Leitor binário big-endian para .class.
    Mantém um cursor interno (self.pos) e expõe métodos u1/u2/u4/u8/bytes.
    """
    __slots__ = ("data", "pos", "size")

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.size = len(data)

    def _need(self, n: int) -> None:
        if self.pos + n > self.size:
            raise EOFError(f"ByteStream: tentativa de ler {n} bytes além do fim (pos={self.pos}, size={self.size})")

    def read_u1(self) -> int:
        self._need(1)
        b = self.data[self.pos]
        self.pos += 1
        return b

    def read_u2(self) -> int:
        self._need(2)
        v = struct.unpack_from(">H", self.data, self.pos)[0]
        self.pos += 2
        return v

    def read_u4(self) -> int:
        self._need(4)
        v = struct.unpack_from(">I", self.data, self.pos)[0]
        self.pos += 4
        return v

    def read_u8(self) -> int:
        self._need(8)
        hi, lo = struct.unpack_from(">II", self.data, self.pos)
        self.pos += 8
        return (hi << 32) | lo

    def read_f4(self) -> float:
        self._need(4)
        v = struct.unpack_from(">f", self.data, self.pos)[0]
        self.pos += 4
        return v

    def read_f8(self) -> float:
        self._need(8)
        v = struct.unpack_from(">d", self.data, self.pos)[0]
        self.pos += 8
        return v

    def read_bytes(self, n: int) -> bytes:
        self._need(n)
        b = self.data[self.pos:self.pos+n]
        self.pos += n
        return b

    def tell(self) -> int:
        return self.pos

    def seek(self, new_pos: int) -> None:
        if not (0 <= new_pos <= self.size):
            raise ValueError("seek fora do range")
        self.pos = new_pos