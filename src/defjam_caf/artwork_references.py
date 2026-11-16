"""Bounded, read-only original UI references; never project overrides."""

import base64
from collections import OrderedDict
import copy
import hashlib
import io
from pathlib import Path
import tempfile

from PIL import Image

from . import projects, runtimes, ui_art
from .container import SaveError

MAX_BYTES = 32 * 1024**2
MAX_CACHED = 64 * 1024**2
MAX_PIXELS = 32 * 1024**2


class References:
    def __init__(self):
        self.cache = OrderedDict()

    def stage(self, runtime, game, donor, workspace, recipe_format):
        from .fighter_mod import contract

        runtime = Path(runtimes.require(runtime, "menu", recipe_format)["path"])
        game, workspace = Path(game).resolve(), Path(workspace)
        ui_art.validate(dict(donor=donor, images={}))
        paths = [game / "screens/screens.viv", game / "assets/djv2.sod", runtime / "scripts/fighter-contract.py"]
        paths.extend(sorted((runtime / "setup").glob("*.py")))
        paths.extend(sorted((runtime / "config").glob("*.json")))
        stamps = tuple((str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in paths)
        key = (str(runtime.resolve()), str(game), donor, stamps)
        if key in self.cache:
            self.cache.move_to_end(key)
            return copy.deepcopy(self.cache[key])
        workspace.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="artwork-reference-", dir=workspace) as temporary:
            output = Path(temporary) / "reference"
            report = contract(
                runtime,
                ["export-ui-reference", "--game", str(game), "--donor", donor, "--portrait-out", str(output)],
                temporary,
                workspace,
            )
            source = report["source"]
            projects.require(
                source.get("donor") == donor and set(source["images"]) == set(ui_art.PARTS),
                "Runtime did not return the complete donor artwork set",
            )
            result = dict(donor=donor, images={}, layouts={})
            used = pixels = 0
            for role, spec in source["images"].items():
                relative = spec["path"]
                path = (output / relative).resolve()
                projects.require(
                    path.is_relative_to(output.resolve())
                    and not any(
                        p.is_symlink() for p in [output / relative, *(output / relative).parents] if p != output.parent
                    ),
                    "Artwork reference file leaves its output folder",
                )
                with path.open("rb") as stream:
                    raw = stream.read(4 * 1024**2 + 1)
                projects.require(len(raw) <= 4 * 1024**2, "Artwork reference PNG is too large")
                projects.require(hashlib.sha256(raw).hexdigest() == spec["sha256"], "Artwork reference hash changed")
                try:
                    with Image.open(io.BytesIO(raw)) as image:
                        width, height = image.size
                        projects.require(
                            image.format == "PNG" and 0 < width <= 2048 and 0 < height <= 2048,
                            "Invalid original artwork dimensions",
                        )
                        image.verify()
                except (OSError, ValueError, Image.DecompressionBombError) as error:
                    raise SaveError("Invalid original artwork PNG", detail=str(error)) from error
                used += len(raw)
                pixels += width * height
                projects.require(used <= MAX_BYTES and pixels <= MAX_PIXELS, "Original artwork set exceeds its budget")
                result["images"][role] = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
                result["layouts"][role] = [width, height]
        self.cache[key] = result
        while (
            len(self.cache) > 2
            or sum(len(v) for item in self.cache.values() for v in item["images"].values()) > MAX_CACHED
        ):
            self.cache.popitem(last=False)
        return copy.deepcopy(result)
