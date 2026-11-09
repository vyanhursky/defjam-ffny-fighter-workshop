"""Verified payload fields; patch only explicitly edited bytes."""
from dataclasses import dataclass, field
import struct

from .container import Container, SaveError
from .profiles import PROFILE_SIZE

STAT_NAMES = ("Upper power", "Lower power", "Speed", "Toughness", "Health")
STAT_KEYS = ("upper", "lower", "speed", "toughness", "health")
STYLE_NAMES = ("Streetfighting", "Kickboxing", "Submissions", "Wrestling", "Martial Arts")
# Deliberately conservative beta ceilings, based on retail developer grants.
# These are editor policy limits, not claims about the game's maximum balances.
CASH_LIMIT = 10_000_000
DEV_LIMIT = 100_000


def combine_styles(styles):
    if not 1 <= len(styles) <= 3 or any(type(s) is not int or not 0 <= s <= 4 for s in styles):
        raise SaveError("Choose one to three retail fighting styles")
    if len(set(styles)) != len(styles):
        raise SaveError("Fighting styles must be distinct")
    primary = styles[0]
    a, b, c, d = [s for s in range(5) if s != primary]
    subsets = ((), (a,), (a, b), (a, c), (a, d), (b,), (b, c), (b, d), (c,), (c, d), (d,))
    return 87 + 11 * primary + subsets.index(tuple(sorted(styles[1:])))


def read_fields(payload):
    if len(payload) != PROFILE_SIZE:
        raise SaveError("Unsupported character profile layout")
    styles = [s for s in payload[0x134:0x137] if s != 0xff]
    return {"cash": struct.unpack_from("<I", payload, 0x14)[0],
            "development": struct.unpack_from("<I", payload, 0x1c)[0],
            "stats": dict(zip(STAT_KEYS, struct.unpack_from("<5I", payload, 0xf0))),
            "styles": styles, "combined_style": payload[0x137],
            "blazin_values": list(struct.unpack_from("<4I", payload, 0x120)),
            "has_fighter": payload[0x4d87] != 0,
            "caf_values": list(struct.unpack_from("<38I", payload, 0x5558)),
            "caf_colors": list(payload[0x55f0:0x55f0 + 38])}


def apply_fields(save: Container, edits: dict) -> Container:
    if not isinstance(edits, dict) or set(edits) - {"cash", "development", "stats", "styles", "caf_values", "caf_colors", "blazin_values"}:
        raise SaveError("Unknown profile edit")
    payload = bytearray(save.payload)
    if len(payload) != PROFILE_SIZE:
        raise SaveError("Unsupported character profile layout")
    for key, offset, limit in (("cash", 0x14, CASH_LIMIT), ("development", 0x1c, DEV_LIMIT)):
        if key in edits:
            n = edits[key]
            if type(n) is not int or not 0 <= n <= limit:
                raise SaveError(f"{key} must be between 0 and {limit:,}")
            struct.pack_into("<I", payload, offset, n)
    if "stats" in edits:
        stats = edits["stats"]
        if not isinstance(stats, dict) or set(stats) - set(STAT_KEYS):
            raise SaveError("Unknown training statistic")
        for key, n in stats.items():
            if type(n) is not int or not 0 <= n <= 50:
                raise SaveError("Training statistics must be between 0 and 50")
            struct.pack_into("<I", payload, 0xf0 + 4 * STAT_KEYS.index(key), n)
    if "styles" in edits:
        styles = edits["styles"]
        combined = combine_styles(styles)
        old_slots = list(payload[0x134:0x137])
        old = old_slots[:old_slots.index(255)] if 255 in old_slots else old_slots
        if any(s not in range(5) for s in old) or len(set(old)) != len(old):
            raise SaveError("Existing style selection is unsupported; preserve it unchanged")
        # Retail SODB style contributions, in upper/lower/speed/tough/health/char
        # order. Apply only the style delta, preserving accomplishment bonuses.
        contributions = ((2, 0, 0, 1, 0, 0), (0, 2, 1, 0, 0, 0), (0, 1, 0, 0, 2, 0),
                         (1, 0, 0, 2, 0, 0), (0, 0, 2, 0, 1, 0))
        for index in range(6):
            offset = 0x108 + index * 4
            value = struct.unpack_from("<I", payload, offset)[0]
            value += sum(contributions[s][index] for s in styles) - sum(contributions[s][index] for s in old)
            if not 0 <= value <= 0x7fffffff:
                raise SaveError("Stored style bonuses are inconsistent; preserve styles unchanged")
            struct.pack_into("<I", payload, offset, value)
        payload[0x134:0x138] = bytes(styles + [255] * (3 - len(styles)) + [combined])
    if "blazin_values" in edits:
        values = edits["blazin_values"]
        if type(values) is not list or len(values) != 4 or any(type(n) is not int or not 0 <= n < 0xFFFFFFFF for n in values):
            raise SaveError("Choose four verified Blazin' move references")
        struct.pack_into("<4I", payload, 0x120, *values)
    # Only the validated appearance translator may supply these arrays. Preserve
    # unchanged slot values exactly, including unknown/internal values.
    for key, offset, fmt, limit in (("caf_values", 0x5558, "<38I", 0xffffffff),
                                    ("caf_colors", 0x55f0, "<38B", 255)):
        if key in edits:
            values = edits[key]
            if not isinstance(values, list) or len(values) != 38 or any(type(n) is not int or not 0 <= n <= limit for n in values):
                raise SaveError("Invalid CAF selection array")
            struct.pack_into(fmt, payload, offset, *values)
    return Container(save.metadata, bytes(payload))


def renamed(save, name):
    # The retail user-ID UI uses a small ASCII name. Seven characters keeps
    # duplicate names within the proven existing naming convention for beta.
    import re
    if not re.fullmatch(r"[A-Z0-9]{1,7}", name):
        raise SaveError("New profile names use 1–7 uppercase letters or digits")
    payload = name.encode("ascii").ljust(16, b"\0") + save.payload[16:]
    return Container(save.metadata, payload)
