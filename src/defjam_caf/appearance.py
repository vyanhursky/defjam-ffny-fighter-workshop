"""Translate retail CAF profile references to original source parts."""
import copy
from .container import SaveError

EMPTY = 0xffffffff
CLOTHING = 0x912016dd
HAIR = 0x7450591a
JEWELRY = 0x426b8667
TATTOO = 0x30948ea0


class Appearance:
    def __init__(self, cache):
        self.cache = cache
        self.db = cache.db
        self.options = {str(i): [] for i in range(12, 38)}
        self.by_key = {}
        self._make_options()

    def find(self, slot, model, resource, palette="default"):
        model = model.upper() if model else None
        resource = resource.upper() if resource else None
        if model is None and resource is None:
            return None
        group = self.cache.groups[str(slot)]
        for item in group["items"]:
            if model is not None and item["model"] != model:
                continue
            for ti, style in enumerate(item["styles"]):
                for ci, name in enumerate(style["variants"]):
                    if name == resource:
                        return dict(item=item["id"], style=ti, color=ci, palette=palette)
            if resource is None and item["model"] == model:
                return dict(item=item["id"], style=0, color=0, palette=palette)
        raise SaveError(f"Saved {group['label'].lower()} source part is not supported by this cache")

    def _add(self, slot, value, color, label, selection, **extra):
        key = f"{slot}:{value}:{color}"
        if key in self.by_key:
            return
        record = dict(key=key, value=value, color=color, label=label, selection=selection, **extra)
        self.options[str(slot)].append(record)
        self.by_key[key] = record

    def _label(self, table, offset, fallback):
        schema = self.db.shop.mapping(self.db.shop.word(12), b"SKMA")
        field = schema.get(table ^ 0xca10191c)
        try:
            if field:
                return self.db.shop.string(self.db.shop.word(offset + field[0] * 4)).replace("@", "").replace("#", "").strip()
        except (ValueError, KeyError, UnicodeError):
            pass
        return fallback

    def _make_options(self):
        for slot, garments in self.cache.catalog["shop"]["groups"].items():
            for garment in garments:
                for color in garment["colors"]:
                    for fitting in color["fittings"]:
                        value = self.db.value_for(CLOTHING, int(garment["id"]), int(color["id"]))
                        self._add(slot, value, int(fitting["id"]),
                                  f"{garment['name']} · {color['name']} · {fitting['name']}",
                                  fitting["selection"], garment=garment["name"],
                                  color_name=color["name"], fitting=fitting["name"])
        # Match source resources to their exact XML group rather than guessing a
        # garment from its filename or assigning an arbitrary same-suffix part.
        for row_index, (ident, (offset,)) in enumerate(self.db.records(HAIR)):
            words = self.db.shop.words(offset, 8)
            model, resource = self.db.shop.string(words[3]), self.db.shop.string(words[7])
            if resource[9:13] == "0001":
                for slot in (20, 21):
                    self._add(slot, self.db.value_for(HAIR, ident), 0,
                              "Bald" if slot == 20 else "Clean shaven", None,
                              garment="Bald" if slot == 20 else "Clean shaven", color_name="", fitting="")
                continue
            model = None if model[9:10] == "9" else model + "_C"
            for slot in (20, 21):
                try:
                    selection = self.find(slot, model, resource)
                except SaveError:
                    continue
                value = self.db.value_for(HAIR, ident)
                res = self.cache.catalog["resources"][resource.lower()]
                palettes = res.get("palettes", [])
                for color in range(max(1, len(palettes))):
                    sel = dict(selection, palette=f"pl{color + 1:02}" if palettes else "default")
                    label = self._label(HAIR, offset, "Grooming " + str(row_index + 1))
                    self._add(slot, value, color, f"{label} · Color {color + 1}", sel,
                              garment=label, color_name=f"Color {color + 1}", fitting="")
        for row_index, (ident, (offset,)) in enumerate(self.db.records(JEWELRY)):
            words = self.db.shop.words(offset, 4)
            stem = self.db.shop.string(words[1])
            colors = self.db.shop.word(words[3])
            if not 0 <= colors <= 64:
                raise SaveError("Unsupported jewelry color table")
            pointers = self.db.shop.words(words[3] + 4, colors)
            for color, pointer in enumerate(pointers):
                values = self.db.shop.words(pointer, 4)
                resource = f"V2CP_{stem}_{values[3]:02}"
                model = resource[:14] + "C"
                for slot in (22, 23, 24, 25, 26, 28):
                    try:
                        selection = self.find(slot, model, resource)
                    except SaveError:
                        continue
                    label = self._label(JEWELRY, offset, "Jewelry " + str(row_index + 1))
                    self._add(slot, self.db.value_for(JEWELRY, ident), color,
                              f"{label} · Finish {color + 1}", selection,
                              garment=label, color_name=f"Finish {color + 1}", fitting="")
        for row_index, (ident, (offset,)) in enumerate(self.db.records(TATTOO)):
            words = self.db.shop.words(offset, 4)
            for slot in range(29, 38):
                resource = f"V2CP_4{slot - 28}{words[2] + 1}_{words[3]:04}_A01_01"
                try:
                    selection = self.find(slot, None, resource)
                except SaveError:
                    continue
                label = self._label(TATTOO, offset, "Tattoo " + str(row_index + 1))
                self._add(slot, self.db.value_for(TATTOO, ident), 255, label, selection,
                          garment=label, color_name="", fitting="")
        for value in range(42):
            resource = f"V2CP_35{value // 7 + 1}_000{value % 7 + 1}_A01_01"
            try:
                selection = self.find(27, None, resource)
            except SaveError:
                continue
            self._add(27, value, 0, f"Teeth {value + 1}", selection,
                      garment=f"Teeth {value + 1}", color_name="", fitting="")
        for slot in range(15, 38):
            if slot == 18:
                continue
            self._add(slot, EMPTY, 255 if slot >= 29 else 0, "None", None,
                      garment="None", color_name="", fitting="")
        for slot, model, resource in ((12, "V2CP_110_0001_C", None),
                                       (13, "V2CP_120_0001_C", "V2CP_120_0001_A01_01"),
                                       (14, "V2CP_130_0001_C", None),
                                       (18, "V2CP_140_0001_C", None)):
            self._add(slot, EMPTY, 0, "None", self.find(slot, model, resource),
                      garment="None", color_name="", fitting="")

    def outfit(self, fields):
        values, colors = fields["caf_values"], fields["caf_colors"]
        build, face_type = values[0], values[5] - 1
        if build not in range(6) or face_type not in range(8):
            raise SaveError("Unsupported saved body or face type; profile fields remain available")
        result = dict(build="ABCDEF"[build], skin=f"pl{values[1]:02}", slots={},
                      face_type=face_type, morphs=[])
        slots = result["slots"]
        slots["1"] = self.find(1, f"V2CP_532_000{2 if face_type % 2 else 1}_C_F", None)
        slots["2"] = self.find(2, "V2CP_532_0004_C", None)
        slots["3"] = self.find(3, "V2CP_530_0001_C", None)
        slots["5"] = self.find(5, "V2CP_210_0001_C", None)
        if not (build // 2 == 1 and face_type in (3, 7)):
            result["morphs"].append(f"v2cp_53{build // 2 + 1}_{face_type % 4 + 1:04}_c")
        for slot, prefix in ((6, 541), (7, 542), (8, 551), (9, 561), (10, 571), (11, 581)):
            value = values[slot]
            if slot in (6, 9, 10, 11) and value == 1:
                continue
            if slot == 11 and value == 4:
                value = 2
            resource = f"V2CP_{prefix}_{value:04}_A01_01"
            model = f"v2cp_{prefix}_{value:04}_c" if slot in (6, 9, 10, 11) else None
            if model:
                result["morphs"].append(model)
            if slot == 11 and value % 2 == 0:
                continue
            slots[str(slot)] = self.find(slot, None, resource,
                                        f"pl{colors[slot] + 1:02}" if slot == 8 else
                                        f"pl{values[1]:02}" if slot in (6, 9, 10, 11) and values[1] else "default")
        for slot in range(12, 38):
            if slot == 26:
                continue  # right earring is reconstructed from the left item
            value, color = values[slot], colors[slot]
            if value == EMPTY:
                if slot in (12, 13, 14, 18):
                    slots[str(slot)] = copy.deepcopy(self.by_key[f"{slot}:{EMPTY}:0"]["selection"])
                elif slot == 27:
                    slots["27"] = self.find(27, None, "V2CP_354_0001_A01_01")
                continue
            key = f"{slot}:{value}:{color}"
            option = self.by_key.get(key)
            # Unused color bytes are preserved; tattoo builder ignores them.
            if option is None and slot >= 29:
                option = self.by_key.get(f"{slot}:{value}:255")
            if option is None:
                raise SaveError(f"Saved {self.cache.groups[str(slot)]['label'].lower()} selection is not mapped")
            if option["selection"]:
                slots[str(slot)] = copy.deepcopy(option["selection"])
        if "25" in slots:
            left = slots["25"]
            item = self.cache.items[left["item"]]
            resource = item["styles"][left["style"]]["variants"][left["color"]]
            pieces = resource.split("_")
            part, model = int(pieces[1]), int(pieces[2])
            if part == 341 and model % 10 in (1, 4):
                model += 4
            elif part in (342, 343):
                model += 11
            pieces[2] = f"{model:04}"
            right = "_".join(pieces)
            # The retail paired builder reuses names for some designs whose XML
            # also lists unused counterparts. Follow the builder, never invent
            # a remap merely to select a matching right-ear XML row.
            slots["26"] = copy.deepcopy(left) if right == resource else self.find(26, right[:14] + "C", right)
        return result

    def selected(self, fields):
        result = {}
        for slot in range(12, 38):
            value, color = fields["caf_values"][slot], fields["caf_colors"][slot]
            key = f"{slot}:{value}:{color}"
            if key not in self.by_key and slot >= 29:
                key = f"{slot}:{value}:255"
            result[str(slot)] = key if key in self.by_key else None
        return result

    def change(self, fields, changes):
        values, colors = fields["caf_values"][:], fields["caf_colors"][:]
        if "build" in changes:
            if changes["build"] not in "ABCDEF" or len(changes["build"]) != 1:
                raise SaveError("Invalid body build")
            values[0] = "ABCDEF".index(changes["build"])
        if "skin" in changes:
            number = int(changes["skin"])
            if f"pl{number:02}" not in self.cache.catalog["resources"][f"v2cp_a_{'abcdef'[values[0]]}"]["images"]:
                raise SaveError("Invalid skin palette")
            values[1] = number
        if "part" in changes:
            option = self.by_key.get(changes["part"])
            if option is None:
                raise SaveError("Unknown retail item choice")
            slot = int(option["key"].split(":")[0])
            values[slot], colors[slot] = option["value"], option["color"]
        return dict(caf_values=values, caf_colors=colors)
