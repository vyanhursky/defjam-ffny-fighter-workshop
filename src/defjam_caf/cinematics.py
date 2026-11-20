"""Closed CAF voice documents retained with portable Workshop projects."""

import hashlib
import math
from .container import SaveError

DURATIONS = {"CI_132A": 65, "CI_113A": 106, "CE_113A": 106}


def require(ok, message):
    if not ok:
        raise SaveError(message)


def validate(settings):
    from .performance import audio_bytes, wav_info

    documents = settings.get("cinematics", {})
    require(type(documents) is dict and set(documents) <= {"intro", "victory"}, "Unsupported authored cinematic role")
    for role, envelope in documents.items():
        require(type(envelope) is dict and set(envelope) == {"source", "voice_sha256"}, "Invalid authored performance")
        source = envelope["source"]
        require(
            type(source) is dict
            and set(source) == {"format", "template", "edits", "mouth", "speech_tick"}
            and source["format"] == "fighter-cinematic-caf-performance-2"
            and type(source["template"]) is str
            and source["template"] in DURATIONS
            and source["template"] == settings.get(role)
            and source["template"].startswith("CI_" if role == "intro" else "CE_"),
            "Authored cinematic requires its original donor; change the donor in Blender",
        )
        duration = DURATIONS[source["template"]]
        edits = source["edits"]
        require(type(edits) is list and len(edits) <= 16, "Too many expression edits")
        occupied = set()
        for edit in edits:
            require(
                type(edit) is dict
                and set(edit) == {"selector", "key", "expected", "sample"}
                and all(type(n) is int for n in edit.values())
                and edit["selector"] == 0
                and 0 <= edit["key"] < 4096
                and 0 <= edit["expected"] < 13
                and 0 <= edit["sample"] < 13
                and edit["key"] not in occupied,
                "Invalid authored brow edit",
            )
            occupied.add(edit["key"])
        mouth = source["mouth"]
        require(type(mouth) is dict and set(mouth) == {"jaw", "lips"}, "Invalid native mouth tracks")
        for name, limit in (("jaw", 1), ("lips", 14)):
            rows = mouth[name]
            require(type(rows) is list and 2 <= len(rows) <= 256, "Mouth key population exceeds budget")
            previous = -1
            for row in rows:
                require(
                    type(row) is list
                    and len(row) == 2
                    and type(row[0]) is int
                    and previous < row[0] <= duration
                    and type(row[1]) in ((int, float) if name == "jaw" else (int,))
                    and 0 <= row[1] <= limit
                    and math.isfinite(row[1]),
                    "Invalid native mouth key",
                )
                previous = row[0]
            require(rows[0] == [0, 0] and rows[-1] == [duration, 0], "Mouth endpoints must be neutral")
        tick = source["speech_tick"]
        require(type(tick) is int and 0 <= tick < duration, "Invalid speech start")
        audio_role = "intro" if role == "intro" else "extro"
        encoded = settings.get("voice", {}).get("clips", {}).get(audio_role)
        require(encoded is not None, "Authored mouth timing requires its imported voice")
        raw = audio_bytes(encoded)
        require(
            hashlib.sha256(raw).hexdigest() == envelope["voice_sha256"],
            "Voice changed; regenerate or retime mouth keys in Blender",
        )
        info = wav_info(raw)
        require(tick + 5 + math.ceil(info["seconds"] * 30) <= duration, "Voice exceeds authored cinematic")
        require(
            57 + 16 * math.ceil(info["samples"] / 4096) + 2 * info["samples"]
            <= (153600 if role == "intro" else 512000),
            "Encoded cinematic voice exceeds native preload; use a lower sample rate",
        )
