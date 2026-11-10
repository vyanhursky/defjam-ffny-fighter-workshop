"""Named retail Blazin' catalog and explicit four-slot selection adapters.

UI keys identify a provider and a stable record, never a menu ordinal. Future
providers can supply options to the same menu; unsupported provider keys fail
closed until their project/runtime capability exists.
"""
import re
import struct

from ._vendor.caf_shop import clean
from .container import SaveError

TABLE = 0x47D305FD
CHOICE = 0x6FC83815
DISPLAY_NAME = 0xCA10191C
PREFIX = "retail/blazin-"


class Catalog:
    def __init__(self, database):
        self.database = database
        shop = database.shop
        schema = shop.mapping(shop.word(12), b"SKMA")
        if schema.get(TABLE ^ CHOICE) != (4, 2) or schema.get(TABLE ^ DISPLAY_NAME) != (3, 1):
            raise SaveError("Unsupported Blazin' move database schema")
        rows, choices = [], set()
        for identity, (offset,) in database.records(TABLE):
            choice = shop.word(offset + 16)
            label = clean(shop.string(shop.word(offset + 12)))
            if not label or not 0 <= choice < 82 or choice in choices:
                raise SaveError("Unsupported or ambiguous retail Blazin' move")
            choices.add(choice)
            record = f"{identity:08x}"
            rows.append(dict(key=PREFIX + record, label=label, source="Original game", record=record,
                             value=database.value_for(TABLE, identity), choice=choice))
        if not rows:
            raise SaveError("No verified Blazin' moves in the original game database")
        self.options = sorted(rows, key=lambda row: (row["label"].casefold(), row["key"]))
        self.by_key = {row["key"]: row for row in rows}
        self.by_value = {row["value"]: row for row in rows}

    def select(self, keys):
        if type(keys) is not list or len(keys) != 4 or any(type(k) is not str or k not in self.by_key for k in keys):
            raise SaveError("Choose four available Blazin' moves from the loaded catalog")
        return [self.by_key[key] for key in keys]

    def profile_keys(self, payload):
        return [self.by_value[value]["key"] if value in self.by_value else
                None if value == 0xFFFFFFFF else f"unavailable/{value:08x}"
                for value in struct.unpack_from("<4I", payload, 0x120)]

    def validate_values(self, values):
        if type(values) is not list or len(values) != 4 or any(type(v) is not int or v not in self.by_value for v in values):
            raise SaveError("Unsupported saved Blazin' move reference")

    def label(self, key):
        return self.by_key[key]["label"] if key in self.by_key else "Inherited / unassigned" if key is None else "Unavailable move"


def project_keys(identities):
    if identities is not None and (type(identities) is not list or len(identities) != 4 or
            any(type(v) is not str or re.fullmatch('[0-9a-f]{8}', v) is None for v in identities)):
        raise SaveError("Choose four retail Blazin' record identities")
    return [PREFIX + identity for identity in identities] if identities is not None else [None] * 4
