"""Own-dump Create-a-Fighter catalogue, attachment reader and static shape deltas.

All derived data is private. Existing fighter decoder/cache formats are untouched.
"""
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

from .defjam_model import ElfData, ModelError, decode
from .hd_assets import archive_entries, shpx_images, unpack_refpack
from .paths import require_private_output

VERSION = 2
BUILDS = tuple("ABCDEF")
MORPH_SLOTS = {"12", "13", "14", "16", "17", "18", "22", "23", "24", "28"}


def fit_build(slot, build):
    """The retail fitting tables share the A/C/F fits for these slots."""
    if slot in ("14", "18", "21", "28"):
        return {"A": "A", "B": "A", "C": "C", "D": "C", "E": "F", "F": "F"}[build]
    return build


def face_fits(model, objects):
    """Default face_type=0: slot 4's build fit targets the slot 2 face.

    Retail 98820 chooses 531/532/533 by build//2; 9A910 applies that
    separate blend shape to the base face, including the default C build.
    Keep this distinct from clothing morph eligibility and full neck models.
    """
    variants = {}
    for index, pair in enumerate(("AB", "CD", "EF"), 1):
        name = f"v2cp_53{index}_0001_c"
        if name not in objects:
            raise ModelError("Missing default CAF face fit: " + name)
        fitted = apply_morph(model, objects[name][1])
        fitted["caf_face_fit"] = name
        for build in pair:
            variants[build] = fitted
    return variants

# Original slot order and composite stages, from the game's CAF table. Geometry
# labels come from the XML processing instructions, not filename guesses.
TEXTURE_STAGES = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 3,
                  2, 2, 2, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1)
LABELS = {"Template": "Skeleton template", "Facial": "Face palette", "ShortFace": "Face base",
          "Neck": "Neck", "Face": "Face shape", "Head": "Scalp", "Eye": "Eyes",
          "Eye Colour": "Eye color", "Brow": "Eyebrows", "Nose": "Nose", "Lip": "Lips",
          "Ear": "Ears", "Ubody": "Tops", "Lbody": "Pants & shorts", "Foot": "Shoes",
          "Cap": "Hats", "LeftWristb": "Left wristbands", "RightWristb": "Right wristbands",
          "Hand": "Hands", "Eyew": "Eyewear", "Hair": "Hair", "Fhair": "Facial hair",
          "Neckls": "Necklaces", "Breace": "Bracelets", "Watch": "Watches",
          "LeftEarr": "Left earrings", "RightEarr": "Right earrings", "Teeth": "Grills & teeth",
          "Ring": "Rings"}
SLOTS = ("Template", "Facial", "ShortFace", "Neck", "Face", "Head", "Eye", "Eye Colour", "Brow", "Nose", "Lip", "Ear",
         "Ubody", "Lbody", "Foot", "Cap", "LeftWristb", "RightWristb", "Hand", "Eyew", "Hair", "Fhair", "Neckls", "Breace",
         "Watch", "LeftEarr", "RightEarr", "Teeth", "Ring", "Tattoo_HeadNeck", "Tattoo_Chest_Stomach", "Tattoo_Back",
         "Tattoo_LeftArm", "Tattoo_LeftForeArm", "Tattoo_RightArm", "Tattoo_RightForeArm", "Tattoo_LeftLeg", "Tattoo_RightLeg")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def expanded(raw):
    return unpack_refpack(raw) if int.from_bytes(raw[:2], "big") & 0x3eff == 0x10fb else raw


def attachments(blob, offset):
    """Follow bounded FSH attachments; 0x6f is text, 0x7c contains placement."""
    result, seen = {}, set()
    while True:
        if offset in seen or len(seen) >= 64 or offset < 16 or offset + 8 > len(blob):
            raise ValueError("Invalid CAF attachment chain")
        seen.add(offset)
        header = struct.unpack_from("<I", blob, offset)[0]
        kind, size = header & 255, header >> 8
        end = offset + size if size else len(blob)
        if end > len(blob) or end < offset + 8:
            raise ValueError("CAF attachment outside SHPX")
        if kind == 0x6f:
            count = struct.unpack_from("<I", blob, offset + 4)[0]
            if not 1 <= count <= 256 or offset + 8 + count > end:
                raise ValueError("Invalid CAF placement string")
            result["text"] = blob[offset + 8:offset + 8 + count].split(b"\0", 1)[0].decode("ascii")
        if kind == 0x7c:
            if offset + 16 > end:
                raise ValueError("Truncated CAF coordinates")
            result["origin"] = list(struct.unpack_from("<2i", blob, offset + 8))
        if not size:
            return result
        offset = end


def placement(blob, record):
    a = attachments(blob, record["offset"])
    if "text" not in a or "origin" not in a:
        return None
    match = re.fullmatch(r"([a-d]),([bc])((?:,-?\d+){0,3})", a["text"])
    if not match:
        raise ValueError("Unknown CAF composition instruction: " + a["text"])
    x, y = a["origin"]
    if min(x, y) < 0 or x + record["width"] > 256 or y + record["height"] > 256:
        raise ValueError("CAF texture leaves its 256-space atlas")
    return dict(atlas=match[1], mode=match[2], origin=[x, y],
                parameters=([int(n) for n in match[3].lstrip(",").split(",")] if match[3] else []) +
                           [0] * (3 - match[3].count(",")), text=a["text"])


def parts_xml(raw):
    if len(raw) > 4 * 1024 * 1024 or b"<!" in raw:
        raise ValueError("Unsafe CAF parts XML")
    root = ET.fromstring(raw, parser=ET.XMLParser(target=ET.TreeBuilder(insert_pis=True)))
    if root.tag != "partslist":
        raise ValueError("Expected CAF partslist")
    groups = []
    for i, node in enumerate(root):
        if node.tag != "head":
            continue
        if i == 0 or i + 1 >= len(root) or root[i - 1].tag is not ET.ProcessingInstruction:
            raise ValueError("CAF category is missing its type instruction")
        match = re.search(r'Type(\w+)\s*=\s*"([^"]+)"', root[i - 1].text or "")
        if not match:
            raise ValueError("Unknown CAF category instruction")
        kind, slot = match.groups()
        index = len(groups)
        label = LABELS.get(slot, re.sub(r"([a-z])([A-Z])", r"\1 \2", slot.removeprefix("Tattoo_").replace("_", " ")))
        section = ("Tattoos" if slot.startswith("Tattoo_") else "Hair & grooming" if slot in ("Hair", "Fhair")
                   else "Jewelry" if 22 <= index <= 28 else "Clothing" if 12 <= index <= 19 else "Body & face")
        group = dict(id=str(index), slot=slot, label=label, section=section, kind=kind, head=node.text,
                     stage=TEXTURE_STAGES[index] if index < len(TEXTURE_STAGES) else 0, items=[])
        for j, model in enumerate(root[i + 1].findall("./contents/model")):
            styles = []
            for ti, texture in enumerate(model.findall("texture")):
                names = [texture.findtext("name")] + [c.findtext("name") for c in texture.findall("colour")]
                if any(not n or not re.fullmatch(r"[A-Za-z0-9_]+", n) for n in names):
                    raise ValueError("Invalid CAF resource name")
                styles.append(dict(id=str(ti), variants=names))
            name = model.findtext("name")
            if not name or not re.fullmatch(r"[A-Za-z0-9_]+", name):
                raise ValueError("Invalid CAF model name")
            group["items"].append(dict(id=f"{index}:{j}", model=name, styles=styles))
        groups.append(group)
    if not groups or len(groups) > 128:
        raise ValueError("Invalid CAF category count")
    return groups


def apply_morph(model, blob, weight=0.9999):
    """Apply audited float3 Coordinates chunks by original render-mesh index.

    Chunk byte count includes packed component/scalar flags. Reject other
    semantics instead of treating normals, bone poses or arbitrary data as xyz.
    """
    if not math.isfinite(weight) or not 0 <= weight <= 1:
        raise ModelError("Invalid CAF morph weight")
    e = ElfData(blob)
    start = e.symbol("__Morph:::")
    groups = e.u(start + 16)
    if not 1 <= groups <= 8:
        raise ModelError("Unsupported CAF morph groups")
    meshes = {m["rm"]: m for m in model["meshes"]}
    result = copy.deepcopy(model)
    targets = {m["rm"]: m for m in result["meshes"]}
    p = start + 20
    changed = set()
    omissions = []
    for _ in range(groups):
        label = e.string(e.data, e.ptr(p))
        channels = e.u(p + 4)
        p += 8
        if label not in ("Coordinates", "Colours") or channels != 1:
            raise ModelError("Unsupported CAF morph semantic")
        channel, chunks = e.unpack("<2I", p)
        p += 8
        if channel != 0 or not 1 <= chunks <= 1024:
            raise ModelError("Unsupported CAF morph channels")
        for _ in range(chunks):
            packed, count, offset, rm = e.unpack("<4I", p)
            p += 16
            size = packed & 0x0fffffff
            if label == "Colours":
                if packed >> 28 != 1 or size != count * 4 or not 1 <= count <= 65535 or offset:
                    raise ModelError("Unsupported CAF vertex-color morph layout")
                e.cut(e.data, p, size)
                # RGB inspection deliberately excludes source vertex colors,
                # just like the existing fighter viewer. Retain that omission.
                omissions.append("Vertex-color shape changes omitted from texture RGB inspection")
                p += size
                continue
            if packed >> 28 != 12 or size != count * 12 or not 1 <= count <= 65535 or offset:
                raise ModelError("Unsupported CAF float3 morph layout")
            e.cut(e.data, p, size)
            if rm in changed:
                raise ModelError("Duplicate CAF morph target")
            changed.add(rm)
            if rm in meshes:
                if len(meshes[rm]["positions"]) != count:
                    raise ModelError("CAF morph vertex count changed")
                values = e.unpack("<" + str(count * 3) + "f", p)
                if any(not math.isfinite(v) or abs(v) > 100 for v in values):
                    raise ModelError("Invalid CAF morph delta")
                targets[rm]["positions"] = [[v + weight * values[i * 3 + axis] for axis, v in enumerate(xyz)]
                                             for i, xyz in enumerate(meshes[rm]["positions"])]
            p += size
    bounds(result)
    result["morph_sha256"] = sha(blob)
    result["caf_omissions"] = sorted(set(omissions))
    return result


def bounds(model):
    xyz = [p for mesh in model["meshes"] for p in mesh["positions"]]
    model["bounds"] = [[min(p[i] for p in xyz) for i in range(3)], [max(p[i] for p in xyz) for i in range(3)]]


def palette_images(blob):
    """Extract named palette alternatives without mutating source identities."""
    count = struct.unpack_from("<I", blob, 8)[0]
    if count > 65536 or 16 + count * 8 > len(blob):
        raise ValueError("Invalid SHPX directory")
    result = {}
    for i in range(count):
        name, off = struct.unpack_from("<4sI", blob, 16 + i * 8)
        if re.fullmatch(b"pl[0-9]{2}", name):
            if off + 16 > len(blob) or blob[off] != 0x2a:
                raise ValueError("Invalid named CAF palette")
            n = struct.unpack_from("<H", blob, off + 4)[0]
            if not 1 <= n <= 256 or off + 16 + n * 4 > len(blob):
                raise ValueError("CAF palette outside SHPX")
            result[name.decode()] = blob[off + 16:off + 16 + n * 4]
    return result


def with_palette(blob, record, palette):
    """Decode through the existing pixel reader with an explicitly named palette."""
    p, seen = record["offset"], set()
    while p not in seen:
        seen.add(p)
        if len(seen) > 64 or p + 16 > len(blob):
            raise ValueError("Invalid palette chain")
        if blob[p] == 0x2a:
            n = struct.unpack_from("<H", blob, p + 4)[0]
            if n * 4 != len(palette):
                raise ValueError("Incompatible CAF palette size")
            edited = bytearray(blob)
            edited[p + 16:p + 16 + len(palette)] = palette
            matches = list(shpx_images(bytes(edited), indices={record["index"]}))
            if len(matches) != 1 or matches[0][1] is None:
                raise ValueError("Unable to decode CAF palette")
            return matches[0][1]
        delta = int.from_bytes(blob[p + 1:p + 4], "little")
        if not delta:
            break
        p += delta
    raise ValueError("Missing CAF source palette")


def build_catalog(dump, corpus, output):
    from ..storage import atomic_json
    output = require_private_output(output)
    if output.exists():
        raise ValueError("Build into a new private directory; existing CAF caches are immutable")
    corpus = Path(corpus).resolve()
    dump = Path(dump).resolve()
    if output.is_relative_to(corpus) or output.is_relative_to(dump):
        raise ValueError("Keep CAF output outside the accepted corpus and source dump")
    corpus_raw = (corpus / "corpus.json").read_bytes()
    corpus_data = json.loads(corpus_raw)
    source_ids = {a["source_id"]: a["id"] for a in corpus_data["assets"] if not a.get("error")}
    resources, objects, xmls = {}, {}, []
    for index in range(4):
        arc = f"v2cp_{index}.viv"
        for name, raw in archive_entries((Path(dump) / "assets" / arc).read_bytes()):
            if not name.lower().endswith((".o", ".xsh", ".xml")):
                continue
            raw = expanded(raw)
            if name.lower() == "createplayer_parts.xml":
                xmls.append(raw)
            elif name.lower().endswith(".o"):
                objects[name[:-2].lower()] = (name, raw)
            elif name.lower().endswith(".xsh"):
                records = []
                for rec, _ in shpx_images(raw, decode=False):
                    if rec.get("error"):
                        raise ValueError(name + ": " + rec["error"])
                    rec = dict(rec)
                    rec["asset"] = source_ids.get(rec["source_id"])
                    rec["placement"] = placement(raw, rec)
                    records.append(rec)
                resources[name[:-4].lower()] = dict(name=name[:-4], archive=arc, records=records,
                                                     sha256=sha(raw), raw=raw)
    if not xmls or len({sha(x) for x in xmls}) != 1:
        raise ValueError("CAF parts XML missing or copies disagree")
    groups = parts_xml(xmls[0])
    if tuple(g["slot"] for g in groups) != SLOTS:
        raise ValueError("Unknown CAF slot order; do not apply this game's stage/fit tables to another layout")
    output.mkdir(parents=True)
    (output / "geometry").mkdir()
    (output / "palettes").mkdir()
    (output / "bases").mkdir()
    (output / "objects").mkdir()
    raw_objects = {}
    for name, (_, blob) in objects.items():
        path = f"objects/{name}.o"
        (output / path).write_bytes(blob)
        raw_objects[name] = dict(path=path, sha256=sha(blob))
    geometries, errors, build_counts = {}, [], Counter()
    try:
        # Independent cache: no corpus/workshop writes and no existing model cache changes.
        for group in groups:
            for item in group["items"]:
                name = item["model"].lower()
                if name == "non_geom" or group["kind"] in ("Template", "Palette", "BlendShape"):
                    continue
                if name in geometries:
                    continue
                if name not in objects:
                    errors.append(dict(model=name, reason="Missing source mesh"))
                    continue
                source_name, blob = objects[name]
                try:
                    # Default face_type=0 selects the first full facial-hair fit.
                    if group["id"] == "21" and name + "1" in objects:
                        source_name, blob = objects[name + "1"]
                    model = decode(blob, source_name, "caf:" + name)
                    variants = {"C": model}
                    if group["id"] == "2" and name == "v2cp_532_0004_c":
                        variants = face_fits(model, objects)
                    if name.endswith("_c") and group["id"] in MORPH_SLOTS | {"3", "21"}:
                        for letter in "ABDEF":
                            morph_name = name[:-1] + letter.lower()
                            if group["id"] == "21":
                                morph_name = name[:-1] + fit_build("21", letter).lower() + "1"
                            if morph_name in objects:
                                try:
                                    if group["id"] in ("3", "21"):
                                        variants[letter] = decode(objects[morph_name][1], objects[morph_name][0], "caf:" + name)
                                    else:
                                        variants[letter] = apply_morph(model, objects[morph_name][1])
                                except ModelError as ex:
                                    errors.append(dict(model=name, build=letter, reason=str(ex)))
                    paths = {}
                    for letter, variant in variants.items():
                        raw = json.dumps(variant, separators=(",", ":"), allow_nan=False).encode()
                        file = f"geometry/{name}-{letter}.json"
                        (output / file).write_bytes(raw)
                        paths[letter] = dict(path=file, sha256=sha(raw), bounds=variant["bounds"])
                        build_counts[letter] += 1
                    geometries[name] = paths
                except (ValueError, KeyError, struct.error) as ex:
                    errors.append(dict(model=name, reason=str(ex)))
        for name, resource in resources.items():
            raw = resource.pop("raw")
            alternatives = palette_images(raw)
            if alternatives:
                # Keep only indexed source data needed to reproduce named palette views.
                path = f"palettes/{name}.xsh"
                (output / path).write_bytes(raw)
                resource["palette_path"] = path
                resource["palettes"] = list(alternatives)
            if re.fullmatch(r"v2cp_[a-d]_[a-f]", name):
                base = next(r for r in resource["records"] if r["index"] == 0)
                ims = dict(default=next(im for r, im in shpx_images(raw, indices={0}) if im is not None))
                ims.update({pal: with_palette(raw, base, colors) for pal, colors in alternatives.items()})
                resource["images"] = {}
                for pal, image in ims.items():
                    path = f"bases/{name}-{pal}.png"
                    image.save(output / path)
                    resource["images"][pal] = dict(path=path, sha256=sha((output / path).read_bytes()))
        for group in groups:
            for item in group["items"]:
                item["geometry"] = item["model"].lower() if item["model"].lower() in geometries else None
                item["limitation"] = ("Face blend-shape editing is not yet supported" if group["kind"] == "BlendShape"
                                       else "" if item["geometry"] or item["model"] == "NON_GEOM"
                                       else "No supported static mesh")
        from .caf_shop import read_shop
        shop = read_shop(dump, groups)
        result = dict(schema=1, decoder=VERSION, corpus_id=corpus_data["corpus_id"],
                      corpus_sha256=sha(corpus_raw), parts_sha256=sha(xmls[0]), groups=groups,
                      resources=resources, geometry=geometries, objects=raw_objects, errors=errors, shop=shop,
                      builds=[dict(id=c, label="Source build " + c, meshes=build_counts[c]) for c in BUILDS],
                      limitations=["Static source rest pose; game lighting/reflections are approximated or omitted",
                                   "Source A–F builds are exposed without guessing retail size labels",
                                   "Default face build fit is applied; facial feature editing and game animation are not reproduced",
                                   "Shop styles select source geometry; automatic outfit compatibility and paired wrist rules are not reproduced"])
        atomic_json(output / "catalog.json", result)
        return dict(path=str(output), groups=len(groups), items=sum(len(g["items"]) for g in groups),
                    models=len(geometries), resources=len(resources), builds=dict(build_counts), errors=errors)
    except Exception:
        # Leave failed private output for diagnosis; no valid catalogue is published.
        raise
