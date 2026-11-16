"""Stage the existing runtime's ordinary performance resources for either project kind."""

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile

from .container import SaveError


def export_settings(runtime, game, workspace, temporary, root, pack, donor, settings):
    from .fighter_mod import contract

    with tempfile.TemporaryDirectory(prefix="performance-", dir=temporary) as folder:
        folder = Path(folder)
        request = folder / "request.json"
        request.write_text(json.dumps(dict(settings=settings, pack=pack, donor=donor)), encoding="utf-8")
        output = folder / "generated"
        generated = copy.deepcopy(
            contract(
                runtime,
                [
                    "workshop-export",
                    "--game",
                    str(game),
                    "--workshop-request",
                    str(request),
                    "--workshop-out",
                    str(output),
                ],
                folder,
                workspace,
            )
        )

        def stage(value):
            if isinstance(value, dict):
                if {"path", "sha256"} <= set(value):
                    path = PurePosixPath(value["path"])
                    if (
                        path.is_absolute()
                        or len(path.parts) < 2
                        or path.parts[0] != "performance"
                        or ".." in path.parts
                        or any(":" in part or "\\" in part for part in path.parts)
                    ):
                        raise SaveError("The game returned an invalid performance asset path")
                    with (output / Path(*path.parts[1:])).open("rb") as stream:
                        raw = stream.read(8 * 1024**2 + 1)
                    if len(raw) > 8 * 1024**2 or hashlib.sha256(raw).hexdigest() != value["sha256"]:
                        raise SaveError("The game returned an invalid performance asset")
                    relative = Path("workshop-performance", *path.parts[1:])
                    destination = Path(root) / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(raw)
                    value["path"] = relative.as_posix()
                else:
                    for child in value.values():
                        stage(child)
            elif isinstance(value, list):
                for child in value:
                    stage(child)

        stage(generated["resources"])
        return generated
