"""Bounds-checked Recomp MC02 reader; no game bytes or console keys."""
from dataclasses import dataclass
import hashlib
import hmac
import struct

HEADER_SIZE = 76
MAX_SAVE_SIZE = 4 * 1024 * 1024
MAGIC = 0x4D433032
# Recomp's Xbox kernel initializes XboxSignatureKey to zero.
RECOMP_KEY = bytes(16)


class SaveError(ValueError):
    pass


def digest(data: bytes) -> bytes:
    return hmac.new(RECOMP_KEY, data, hashlib.sha1).digest()


@dataclass(frozen=True)
class Container:
    metadata: bytes
    payload: bytes

    @classmethod
    def read(cls, raw: bytes) -> "Container":
        if not HEADER_SIZE <= len(raw) <= MAX_SAVE_SIZE:
            raise SaveError("Save is truncated or exceeds the supported size limit")
        magic, length, size0, size1 = struct.unpack_from("<4I", raw)
        if magic != MAGIC:
            raise SaveError("Not a supported little-endian Recomp MC02 save")
        if length != len(raw) or HEADER_SIZE + size0 + size1 != length:
            raise SaveError("Save length and chunk lengths disagree")
        if not size0 or not size1:
            raise SaveError("Save chunks must not be empty")
        chunks = (raw[HEADER_SIZE:HEADER_SIZE + size0], raw[HEADER_SIZE + size0:])
        checks = ((raw[16:36], digest(chunks[0])), (raw[36:56], digest(chunks[1])),
                  (raw[56:76], digest(raw[:56])))
        if not all(hmac.compare_digest(stored, expected) for stored, expected in checks):
            raise SaveError("Invalid Recomp integrity signatures; unsupported or damaged save")
        return cls(*chunks)

    def encode(self) -> bytes:
        if not self.metadata or not self.payload:
            raise SaveError("Save chunks must not be empty")
        length = HEADER_SIZE + len(self.metadata) + len(self.payload)
        if length > MAX_SAVE_SIZE:
            raise SaveError("Save exceeds the supported size limit")
        head = struct.pack("<4I", MAGIC, length, len(self.metadata), len(self.payload))
        head += digest(self.metadata) + digest(self.payload)
        return head + digest(head) + self.metadata + self.payload
