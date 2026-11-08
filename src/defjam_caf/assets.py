"""Private original-asset cache derived directly from a local game dump."""
import base64
import hashlib
import io
import json
from pathlib import Path

from PIL import Image
import numpy as np

from ._vendor.caf_assets import build_catalog, expanded, palette_images, with_palette, sha
from ._vendor.hd_assets import archive_entries, shpx_images
from ._vendor.caf_shop import ShopDatabase, Locale
from .storage import atomic_json


def image_uri(image):
    out = io.BytesIO()
    image.save(out, format="PNG", compress_level=1)
    return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode("ascii")


def composite(canvas, image, origin, mode):
    """Retail 8-bit copy/blend with independent maximum alpha; upstream PR #5."""
    x, y = origin
    if min(x, y) < 0 or x + image.width > canvas.width or y + image.height > canvas.height:
        raise ValueError("Texture leaves the composed CAF atlas")
    if mode == "c":
        canvas.paste(image, (x, y))
        return
    if mode != "b":
        raise ValueError("Unknown CAF composite mode")
    target = (x, y, x + image.width, y + image.height)
    dst = np.array(canvas.crop(target), dtype=np.uint32)
    src = np.array(image, dtype=np.uint32)
    alpha = src[:, :, 3:4]
    rgb = (src[:, :, :3] * alpha + dst[:, :, :3] * (255 - alpha) + 128) >> 8
    rgb = np.where(alpha == 255, src[:, :, :3], np.where(alpha == 0, dst[:, :, :3], rgb))
    canvas.paste(Image.fromarray(np.concatenate((rgb, np.maximum(src[:, :, 3:4], dst[:, :, 3:4])), axis=2).astype(np.uint8)), (x, y))


class Database:
    """Bounded generic SODB row-index adapter for serialized selection IDs."""
    def __init__(self, dump):
        dump = Path(dump)
        raw = next(expanded(b) for name, b in archive_entries((dump / "assets/misc.viv").read_bytes())
                   if name.lower() == "cmusen.loc")
        self.shop = ShopDatabase((dump / "assets/djv2.sod").read_bytes(), Locale(raw))
        self.tables = self.shop.mapping(self.shop.word(16), b"DATA")
        self.cache = {}

    def records(self, table_hash):
        if table_hash not in self.cache:
            s = self.shop
            header = self.tables[table_hash][0]
            tag, index, _, count = s.words(header, 4)
            if tag != table_hash:
                raise ValueError("Invalid game database table")
            indexes = s.mapping(index)
            records = s.mapping(indexes[table_hash][0], table_hash.to_bytes(4, "little"))
            if len(records) != count:
                raise ValueError("Game database row count mismatch")
            self.cache[table_hash] = list(records.items())
        return self.cache[table_hash]

    def packed(self, value):
        table_index, row_index = value >> 24, value & 0xffff
        keys = list(self.tables)
        if not 0 <= table_index < len(keys):
            raise ValueError("Unknown saved item table")
        table_hash = keys[table_index]
        records = self.records(table_hash)
        if not 0 <= row_index < len(records):
            raise ValueError("Unknown saved item row")
        ident, (offset,) = records[row_index]
        return table_hash, row_index, ident, offset, (value >> 16) & 255

    def value_for(self, table_hash, ident, fitting=0):
        index = [key for key, _ in self.records(table_hash)].index(ident)
        if index > 65535 or not 0 <= fitting <= 255:
            raise ValueError("Unsupported game item index")
        return (list(self.tables).index(table_hash) << 24) | (fitting << 16) | index


def build_cache(dump, workspace, progress=lambda message: None):
    dump, workspace = Path(dump), Path(workspace)
    sources = [dump / "assets" / f"v2cp_{n}.viv" for n in range(4)]
    identity = sha(b"caf-customizer-cache-1" + b"".join(hashlib.sha256(p.read_bytes()).digest() for p in sources)
                   + hashlib.sha256((dump / "assets/djv2.sod").read_bytes()).digest()
                   + hashlib.sha256((dump / "assets/misc.viv").read_bytes()).digest())
    root = workspace / "assets" / identity
    if (root / "catalog" / "catalog.json").is_file():
        return AssetCache(root, dump)
    images = root / "originals"
    images.mkdir(parents=True, exist_ok=True)
    assets = {}
    for index, path in enumerate(sources):
        progress(f"Reading original CAF textures · archive {index + 1} of 4")
        for name, raw in archive_entries(path.read_bytes()):
            if not name.lower().endswith(".xsh"):
                continue
            for record, image in shpx_images(expanded(raw)):
                if record.get("error"):
                    raise ValueError(name + ": " + record["error"])
                if image is None:
                    continue
                ident = record["source_id"]
                if ident in assets:
                    continue
                dest = images / (ident + ".png")
                image.save(dest, format="PNG")
                assets[ident] = dict(id=ident, source_id=ident, original=dest.name,
                                     original_hash=sha(dest.read_bytes()))
    atomic_json(images / "corpus.json", dict(corpus_id=identity, assets=list(assets.values())))
    progress("Decoding original meshes and body fits · first run only")
    # Each build has an immutable destination; incomplete builds stay identifiable.
    catalog = root / "catalog"
    if catalog.exists():
        import uuid
        catalog.rename(root / ("incomplete-" + uuid.uuid4().hex))
    build_catalog(dump, images, catalog)
    progress("CAF assets ready")
    return AssetCache(root, dump)


class AssetCache:
    def __init__(self, root, dump):
        self.root = Path(root)
        self.catalog_root = self.root / "catalog"
        self.catalog = json.loads((self.catalog_root / "catalog.json").read_text())
        self.originals = self.root / "originals"
        index_raw = (self.originals / "corpus.json").read_bytes()
        if sha(index_raw) != self.catalog["corpus_sha256"]:
            raise ValueError("The original-asset index changed; rebuild the private cache")
        self.original_hashes = {a["id"]: a["original_hash"] for a in json.loads(index_raw)["assets"]}
        self.db = Database(dump)
        self.groups = {g["id"]: g for g in self.catalog["groups"]}
        self.items = {i["id"]: i for g in self.groups.values() for i in g["items"]}
        self._geometries = {}
        self._images = {}

    def verified(self, record):
        path = self.catalog_root / record["path"]
        if not path.resolve().is_relative_to(self.catalog_root.resolve()):
            raise ValueError("Asset path leaves the private cache")
        raw = path.read_bytes()
        if sha(raw) != record["sha256"]:
            raise ValueError("CAF cache checksum changed; rebuild the cache")
        return raw

    def original(self, ident):
        path = self.originals / (ident + ".png")
        if not all(c in "0123456789abcdef" for c in ident) or len(ident) != 64:
            raise ValueError("Invalid texture identity")
        raw = path.read_bytes()
        if sha(raw) != self.original_hashes[ident]:
            raise ValueError("An original cached texture changed; rebuild the private cache")
        return Image.open(io.BytesIO(raw)).convert("RGBA")

    def resource_image(self, resource, record, palette="default"):
        key = (resource["name"], record["index"], palette)
        if key not in self._images:
            if palette != "default":
                raw = self.verified(dict(path=resource["palette_path"], sha256=resource["sha256"]))
                image = with_palette(raw, record, palette_images(raw)[palette])
            else:
                image = self.original(record["asset"])
            self._images[key] = image
        return self._images[key].copy()

    def geometry(self, name, build, slot):
        from ._vendor.caf_assets import fit_build
        variants = self.catalog["geometry"][name]
        build = fit_build(str(slot), build)
        record = variants.get(build, variants.get("C"))
        if record["sha256"] not in self._geometries:
            self._geometries[record["sha256"]] = json.loads(self.verified(record))
        return self._geometries[record["sha256"]]

    def raw_model(self, name):
        from ._vendor.defjam_model import decode
        key = "raw:" + name
        if key not in self._geometries:
            self._geometries[key] = decode(self.verified(self.catalog["objects"][name]), name, "caf:" + name)
        return self._geometries[key]

    def face(self, outfit):
        from ._vendor.caf_assets import apply_morph
        key = "face:" + ",".join(outfit["morphs"])
        if key not in self._geometries:
            result = self.raw_model("v2cp_532_0004_c")
            for name in outfit["morphs"]:
                result = apply_morph(result, self.verified(self.catalog["objects"][name]))
            self._geometries[key] = result
        return self._geometries[key]

    def arm_pivots(self):
        """Read original bind joints; pose rotations are editor approximations.

        Skeleton header is 16 bytes; each joint is scale3/parent/quaternion4/
        translation4/inverse-bind16 (112 bytes). No game clip is decoded here.
        """
        from ._vendor.defjam_model import ElfData
        key = "preview-arm-pivots"
        if key not in self._geometries:
            source = self.catalog["objects"]["v2cp_110_0001_c"]
            elf = ElfData(self.verified(source))
            skeleton = elf.symbol("__Skeleton:::")
            count = elf.u(skeleton + 8)
            if not 1 <= count <= 256:
                raise ValueError("Unsupported preview skeleton")
            names = {s["name"].removeprefix("__Bone:::root."): elf.u(s["value"])
                     for s in elf.symbols if s["name"].startswith("__Bone:::root.")}
            result = {}
            for name in ("L_arm1", "L_arm2", "R_arm1", "R_arm2"):
                index = names[name]
                if not 0 <= index < count:
                    raise ValueError("Preview joint leaves skeleton")
                at = skeleton + 16 + index * 112
                inverse = np.array(elf.unpack("<16f", at + 48)).reshape(4, 4).T
                world = np.linalg.inv(inverse)
                pivot = world[:3, 3].tolist()
                if not all(np.isfinite(pivot)):
                    raise ValueError("Invalid preview joint")
                result[name] = pivot
            self._geometries[key] = result
        return self._geometries[key]

    def compose(self, outfit):
        meshes, layers, notices = [], [], []
        hair = outfit["slots"].get("20")
        hair_item = self.items[hair["item"]] if hair else None
        hair_model = hair_item.get("geometry") if hair_item else None
        if hair_model:
            hat = outfit["slots"].get("15")
            hat_model = self.items[hat["item"]].get("geometry") if hat else None
            if hat_model:
                number = int(hat_model[9:13])
                part = (211 if number in {*range(1, 8), *range(25, 34)} else
                        212 if number in {8, *range(15, 18), *range(19, 25)} else
                        213 if number in {*range(9, 15), 18, *range(34, 39)} else None)
                if part is None:
                    raise ValueError("This hat/hair fit is not supported by the verified preview rules")
                hair_model = hair_model[:7] + str(part - 210) + hair_model[8:]
                if part == 212 and outfit["face_type"] >= 4:
                    hair_model += "1"
            elif outfit["face_type"] >= 4:
                hair_model += "1"
        for slot, selected in outfit["slots"].items():
            item = self.items[selected["item"]]
            duplicate_ear = slot == "26" and selected == outfit["slots"].get("25")
            if item.get("geometry") and not duplicate_ear:
                if slot == "2":
                    geometry = self.face(outfit)
                elif slot in {"6", "9", "10", "11"}:
                    geometry = None  # morphs are applied to the face, never separate meshes
                elif slot == "5" and outfit["face_type"] >= 4:
                    geometry = None if hair_model else self.raw_model("v2cp_210_0001_c1")
                elif slot == "5" and hair_model:
                    geometry = None
                elif slot == "15" and outfit["face_type"] >= 4:
                    geometry = self.raw_model(item["geometry"] + "1")
                elif slot == "20" and hair_model:
                    geometry = self.raw_model(hair_model)
                elif slot == "21":
                    from ._vendor.caf_assets import fit_build
                    suffix = outfit["face_type"] % 4 + 1
                    name = item["geometry"][:-1] + fit_build("21", outfit["build"]).lower()
                    if suffix != 4:
                        name += str(suffix)
                    geometry = self.raw_model(name)
                else:
                    geometry = self.geometry(item["geometry"], outfit["build"], slot)
                if geometry is None:
                    geometry = {"meshes": []}
                for mesh in geometry["meshes"]:
                    atlas = mesh.get("texture_ref", "").split(",")[0]
                    if atlas not in {"cp_a", "cp_b", "cp_c", "cp_d"}:
                        notices.append("Unsupported material: " + mesh["name"])
                        continue
                    meshes.append(dict(mesh, slot=slot, atlas=atlas[-1]))
            if not item["styles"]:
                continue
            resource = self.catalog["resources"][item["styles"][selected["style"]]["variants"][selected["color"]].lower()]
            first = resource["records"][0] if resource["records"] else None
            companions = first["placement"]["parameters"][0] if first and first["placement"] else 0
            names = ({first["name"]} if first else set()) | {f"al{i:02d}" for i in range(1, companions + 1)}
            for record in resource["records"]:
                if record["name"] in names and record["placement"]:
                    layers.append((self.groups[slot]["stage"], int(slot), resource, record, selected.get("palette", "default")))
        layers.sort(key=lambda x: x[:2])
        textures = {}
        for atlas in "abcd":
            resource = self.catalog["resources"][f"v2cp_{atlas}_{outfit['build'].lower()}"]
            base = resource["images"].get(outfit["skin"])
            if base is None:
                raise ValueError("Unsupported skin palette")
            canvas = Image.open(io.BytesIO(self.verified(base))).convert("RGBA")
            for _, _, resource, record, palette in layers:
                instruction = record["placement"]
                if instruction["atlas"] == atlas:
                    composite(canvas, self.resource_image(resource, record, palette), instruction["origin"], instruction["mode"])
            textures[atlas] = image_uri(canvas)
        if not meshes:
            raise ValueError("No renderable fighter geometry")
        points = [p for m in meshes for p in m["positions"]]
        return dict(meshes=meshes, textures=textures, notices=notices, arm_pivots=self.arm_pivots(),
                    bounds=[[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]])
