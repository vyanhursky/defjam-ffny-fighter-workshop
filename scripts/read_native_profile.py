"""Read candidate profile records from an explicitly owned Windows game PID.

Requires both the exact expected executable path and the run's own startup log.
ReadProcessMemory only; no process memory writes or runtime patches.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import struct

from defjam_caf.fields import read_fields
from defjam_caf.profiles import PROFILE_SIZE


def scan(pid, executable, log, name):
    if os.name != "nt":
        return []
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1010, False, pid)
    if not handle:
        raise OSError(ctypes.get_last_error(), "Cannot read owned game process")
    try:
        path = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(path))
        if not kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)) or Path(path.value).resolve() != Path(executable).resolve():
            raise ValueError("PID does not match the explicitly owned executable")
        text = Path(log).read_text(errors="replace")
        match = re.search(r"mapped 65536 KB at (0x[0-9A-Fa-f]+)", text)
        if not match:
            return []
        base = int(match[1], 16)
        def read(address, length):
            buffer = ctypes.create_string_buffer(length)
            got = ctypes.c_size_t()
            kernel.ReadProcessMemory(handle, base + address, buffer, length, ctypes.byref(got))
            return buffer.raw[:got.value]
        def word(address):
            raw = read(address, 4)
            return struct.unpack("<I", raw)[0] if len(raw) == 4 else 0
        # Retail service registry and current-profile accessor, independently
        # traced from the frontend cash reader. Prefer the live manager object
        # over copies of the serialized file in loading buffers.
        service = word(0x2fb1a8)
        valid = lambda p: 0x10000 <= p < 0x4000000 or 0x80000000 <= p < 0x84000000
        manager = word(service + 4) if valid(service) else 0
        index = word(manager + 0x5ac7c) if valid(manager) else 0xffffffff
        if index < 16:
            address = manager + 0x177c + index * 0x5950 + 0xc
            payload = read(address, PROFILE_SIZE)
            if len(payload) == PROFILE_SIZE and payload[:16].split(b"\0", 1)[0] == name.encode("ascii"):
                return [dict(kind="current_profile", address=f"0x{address:08x}",
                             fields=read_fields(payload), bonuses=list(struct.unpack_from("<6I", payload, 0x108)))]
        pattern = name.encode("ascii").ljust(16, b"\0")
        results = []
        ranges = list(range(0x10000, 0x4000000, 0x100000)) + list(range(0x80000000, 0x84000000, 0x100000))
        for start in ranges:
            block = read(start, 0x100000 + len(pattern))
            offset = block.find(pattern)
            while offset >= 0:
                address = start + offset
                payload = read(address, PROFILE_SIZE)
                if len(payload) == PROFILE_SIZE:
                    fields = read_fields(payload)
                    if fields["caf_values"][0] in range(6) and all(v <= 50 for v in fields["stats"].values()) and fields["has_fighter"] and fields["styles"] and len(set(fields["styles"])) == len(fields["styles"]) and all(v in range(5) for v in fields["styles"]):
                        results.append(dict(kind="candidate", address=f"0x{address:08x}", fields=fields,
                                            bonuses=list(struct.unpack_from("<6I", payload, 0x108))))
                offset = block.find(pattern, offset + 16)
        return results
    finally:
        kernel.CloseHandle(handle)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--exe", type=Path, required=True)
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = scan(args.pid, args.exe, args.log, args.name)
    args.output.write_text(json.dumps(result, indent=2))
    print(f"Read {len(result)} candidate profile records from the owned game process")
