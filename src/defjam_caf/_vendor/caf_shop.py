"""Read retail wardrobe labels and fittings from the owner's SODB/localization.

No retail catalogue or text is bundled. The private CAF cache stores this
metadata alongside its source hashes; existing outfit/texture IDs are unchanged.
"""
from collections import defaultdict
from pathlib import Path
import struct

from .hd_assets import archive_entries
from .caf_assets import expanded, sha


class Binary:
    def __init__(self, data):
        self.data = data

    def cut(self, offset, size):
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise ValueError("Shop metadata pointer outside source")
        return self.data[offset:offset + size]

    def words(self, offset, count=1):
        if not 0 <= count <= 100000:
            raise ValueError("Shop metadata count exceeds limit")
        return struct.unpack("<" + "I" * count, self.cut(offset, count * 4))

    def word(self, offset):
        return self.words(offset)[0]

    def text(self, offset, wide=False):
        step = 2 if wide else 1
        for end in range(offset, offset + 4096, step):
            if self.cut(end, step) == b"\0" * step:
                return self.cut(offset, end - offset).decode("utf-16le" if wide else "ascii")
        raise ValueError("Unterminated shop metadata string")

    def mapping(self, offset, tag=None):
        if tag is not None:
            if self.cut(offset, 4) != tag:
                raise ValueError("Unexpected shop metadata table")
            offset += 4
        count, stride = self.words(offset, 2)
        if stride not in (1, 2):
            raise ValueError("Unsupported shop metadata table stride")
        keys = self.words(offset + 8, count)
        values = self.words(offset + 8 + count * 4, count * stride)
        if len(set(keys)) != count:
            raise ValueError("Duplicate shop metadata keys")
        return {key: values[i * stride:(i + 1) * stride] for i, key in enumerate(keys)}


def text_hash(value):
    """Retail's DJB2 key includes its terminating NUL."""
    result = 5381
    for byte in value.encode("ascii") + b"\0":
        result = (result * 33 + byte) & 0xffffffff
    return result


class Locale(Binary):
    def __init__(self, data):
        super().__init__(data)
        if self.cut(0, 4) != b"LOCH" or self.word(4) != 20 or self.word(12) != 1:
            raise ValueError("Unsupported shop localization header")
        self.base = self.word(16)
        if self.cut(20, 4) != b"LOCT" or self.word(24) != 16 or (self.base - 36) % 8:
            raise ValueError("Unsupported shop localization index")
        if self.cut(self.base, 4) != b"LOCL":
            raise ValueError("Missing shop localization strings")
        count = self.word(self.base + 12)
        pairs = self.words(36, (self.base - 36) // 4)
        self.index = dict(zip(pairs[::2], pairs[1::2]))
        if len(self.index) != count or set(self.index.values()) != set(range(count)):
            raise ValueError("Invalid shop localization index")
        self.offsets = self.words(self.base + 16, count)
        self.cut(self.base, self.word(self.base + 4))

    def get(self, key):
        index = self.index.get(key)
        return None if index is None else self.text(self.base + self.offsets[index], wide=True)


class ShopDatabase(Binary):
    CLOTHING = 0x912016dd

    def __init__(self, data, locale):
        super().__init__(data)
        if self.cut(0, 4) != b"SODB" or self.word(4) != 2:
            raise ValueError("Unsupported shop database")
        self.locale = locale
        schema = self.mapping(self.word(12), b"SKMA")
        fields = {0x9f891e31: 1, 0x965e3fb9: 2, 0xac3e66a4: 3, 0x0cfa401e: 4,
                  0xca10191c: 5, 0x7c853fa8: 6, 0xc86e0a21: 7, 0x0e334dc7: 8}
        if any(schema.get(self.CLOTHING ^ key, (None,))[0] != word for key, word in fields.items()):
            raise ValueError("Unsupported clothing record schema")
        tables = self.mapping(self.word(16), b"DATA")
        start = self.word(20)
        if self.cut(start, 4) != b"STRT":
            raise ValueError("Unsupported shop string table")
        count = self.word(start + 4)
        pairs = self.words(start + 8, count * 2)
        self.strings = list(zip(pairs[::2], pairs[1::2]))
        header = tables.get(self.CLOTHING)
        if not header or len(header) != 1:
            raise ValueError("Missing clothing shop table")
        tag, index, _, count = self.words(header[0], 4)
        if tag != self.CLOTHING:
            raise ValueError("Invalid clothing shop table")
        indexes = self.mapping(index)
        if self.CLOTHING not in indexes:
            raise ValueError("Missing clothing primary index")
        self.records = self.mapping(indexes[self.CLOTHING][0], struct.pack("<I", self.CLOTHING))
        if len(self.records) != count:
            raise ValueError("Clothing count disagrees with index")

    def string(self, index):
        if not 0 <= index < len(self.strings):
            raise ValueError("Shop string index outside source")
        key, offset = self.strings[index]
        text = self.text(offset) if offset else self.locale.get(key)
        if text is None:
            raise ValueError("Missing localized clothing name")
        return text

    def array(self, offset):
        count = self.word(offset)
        if not 1 <= count <= 1024:
            raise ValueError("Invalid clothing option count")
        return [self.words(p, 3) for p in self.words(offset + 4, count)]

    def clothing(self):
        for ident, (offset,) in self.records.items():
            r = self.words(offset, 9)
            if r[8] >= 16:
                raise ValueError("Unknown clothing category")
            yield dict(id=str(ident), name=clean(self.string(r[5])), source_name=self.string(r[5]), internal=self.string(r[0]),
                       model=r[1], design=self.string(r[2]), order=r[7], category=r[8],
                       colors=[dict(id=str(i), name=clean(self.string(c[1])), source_name=self.string(c[1]), number=c[2])
                               for i, c in enumerate(self.array(r[3]))],
                       fits=[dict(id=str(i), offset=f[1], flags=f[2]) for i, f in enumerate(self.array(r[6]))])


def clean(value):
    # Retail @/# are text layout markers, not parts of garment names.
    return " ".join(value.replace("@", "").replace("#", " ").split())


PART_CODES = (111, 112, 113, 114, 115, 121, 122, 123, 131, 132, 133, 134, 141, 142, 143, 144)
SLOT_IDS = (12, 12, 12, 12, 12, 13, 13, 13, 14, 14, 14, 14, 15, 16, 18, 19)
CATEGORIES = ("Jackets", "Jerseys", "Shirts", "Sweaters", "T-shirts", "Jeans", "Pants", "Shorts",
              "Athletic", "Casual", "Boots", "Shoes", "Headwear", "Armbands", "Gloves", "Eyewear")


def wardrobe(database, groups):
    """Join a garment's fittings to geometry first, then actual XML textures.

    Hats share textures across orientations; some shorts and taped-finger
    meshes have authored aliases. The XML is authoritative for those links.
    """
    by_slot = {g["id"]: g for g in groups}
    result, unresolved = defaultdict(list), []
    for row in database.clothing():
        category = row["category"]
        slot, part = str(SLOT_IDS[category]), PART_CODES[category]
        colors = []
        for color in row["colors"]:
            choices = []
            for fit in row["fits"]:
                number = row["model"] + fit["offset"]
                # The shipped XML assigns taped fingers to the 142 meshes.
                mesh_part = 142 if part == 143 and number in (11, 12, 13) else part
                model_name = f"V2CP_{mesh_part:03}_{number:04}_C"
                suffix = f"_{row['design']}_{color['number']:02}"
                candidates = []
                for item in by_slot.get(slot, {}).get("items", []):
                    if item["model"] != model_name and item["model"] != "NON_GEOM":
                        continue
                    for ti, style in enumerate(item["styles"]):
                        for ci, resource in enumerate(style["variants"]):
                            # NON_GEOM armband entries still identify the part in the texture name.
                            if item["model"] == "NON_GEOM" and not resource.startswith(f"V2CP_{part:03}_{number:04}_"):
                                continue
                            if resource.endswith(suffix):
                                candidates.append((item, ti, ci, resource))
                if not candidates:
                    unresolved.append(dict(item=row["id"], color=color["id"], fitting=fit["id"]))
                    continue
                texture_number = row["model"] if part == 141 else 21 if part == 123 and number == 22 else number
                expected = f"V2CP_{mesh_part:03}_{texture_number:04}{suffix}"
                exact = [entry for entry in candidates if entry[3] == expected]
                if exact:
                    candidates = exact
                if len({entry[3] for entry in candidates}) != 1:
                    unresolved.append(dict(item=row["id"], color=color["id"], fitting=fit["id"], reason="Ambiguous source textures"))
                    continue
                # Only actual identical source references are aliases. A shared
                # suffix can also name distinct resources on the same model.
                item, ti, ci, resource = candidates[0]
                key = f"FIT_{part:03}_{number:04}"
                raw_label = database.locale.get(text_hash(key))
                label = clean(raw_label) if raw_label and not raw_label.startswith("FIT_") else f"Source style {int(fit['id']) + 1}"
                aliases = [dict(item=i["id"], style=t, color=c, palette="default") for i, t, c, _ in candidates[1:]]
                choices.append(dict(id=fit["id"], name=label, source_name=raw_label, key=key, flags=fit["flags"], resource=resource,
                                    aliases=aliases,
                                    selection=dict(item=item["id"], style=ti, color=ci, palette="default")))
            if choices:
                colors.append(dict(id=color["id"], name=color["name"], source_name=color.get("source_name", color["name"]), fittings=choices))
        result[slot].append(dict(id=row["id"], name=row["name"], source_name=row.get("source_name", row["name"]), category=CATEGORIES[category],
                                 order=row["order"], colors=colors))
    for rows in result.values():
        rows.sort(key=lambda r: (r["order"], r["name"].casefold(), r["id"]))
    return dict(groups=dict(result), unresolved=unresolved)


def read_shop(dump, groups):
    dump = Path(dump)
    sod = (dump / "assets/djv2.sod").read_bytes()
    locale = next((expanded(raw) for name, raw in archive_entries((dump / "assets/misc.viv").read_bytes())
                   if name.lower() == "cmusen.loc"), None)
    if locale is None:
        raise ValueError("Missing English shop localization")
    result = wardrobe(ShopDatabase(sod, Locale(locale)), groups)
    result["sources"] = dict(database=sha(sod), locale=sha(locale))
    return result
