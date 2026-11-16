"""Repeatable, game-free HD project validation and snapshot benchmark."""

import base64
import io
import json
import random
import statistics
import time

from PIL import Image
from defjam_caf import projects, outfits, ui_art
from defjam_caf.editor import Editor


def invented_project():
    rng = random.Random(7)

    def png(size):
        image = Image.frombytes("RGB", (size, size), rng.randbytes(size * size * 3))
        output = io.BytesIO()
        image.save(output, format="PNG", compress_level=0)
        return base64.b64encode(output.getvalue()).decode("ascii")

    fighter = dict(
        has_fighter=True,
        stats=dict.fromkeys(("health", "upper", "lower", "speed", "toughness"), 20),
        styles=[0],
        caf_values=[0, 0, 0, 0, 0, 1] + [0] * 6 + [0xFFFFFFFF] * 26,
        caf_colors=[0] * 38,
    )
    document = projects.from_fields(fighter, "Invented benchmark")
    document["textures"] = dict(
        appearance_sha256=projects.appearance_hash(document["fighter"]),
        atlases={slot: png(1024) for slot in projects.ATLAS_SLOTS},
    )
    document, _ = outfits.add(document)
    document, _ = outfits.add(document)
    document["ui_art"] = {"images": {role: png(128) for role in ui_art.ROLES}}
    return document


def main():
    document = invented_project()
    projects.validate(document)
    elapsed = []
    for _ in range(5):
        started = time.perf_counter()
        projects.validate(document)
        elapsed.append((time.perf_counter() - started) * 1000)
    editor = Editor("build/benchmark-workspace")
    editor.project = document
    snapshot_bytes = len(json.dumps(editor.snapshot()).encode())
    print(
        json.dumps(
            dict(
                fixture="3 outfits, 6 x 1024 RGB sheets, 30 x 128 RGB UI images",
                median_validation_ms=round(statistics.median(elapsed), 2),
                snapshot_json_bytes=snapshot_bytes,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
