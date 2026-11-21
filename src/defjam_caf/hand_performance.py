"""Portable closed left-finger document validation; no binary animation input."""

import math
from .cinematics import require

FORMAT = "fighter-native-left-hand-1"


def validate_hand(value, template):
    require(template == "CE_113A", "Left fingers require the reviewed CE_113A hand controller")
    require(
        type(value) is dict and set(value) == {"format", "pose", "envelope"} and value["format"] == FORMAT,
        "Unsupported left-hand document",
    )
    pose = value["pose"]
    require(type(pose) is list and len(pose) == 15, "Left hand needs exactly fifteen native finger quaternions")
    for q in pose:
        require(
            type(q) is list
            and len(q) == 4
            and all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= 1 for v in q)
            and abs(sum(v * v for v in q) - 1) < 0.0002,
            "Finger quaternion must be finite and unit length",
        )
    rows = value["envelope"]
    require(type(rows) is list and 2 <= len(rows) <= 16, "Hand envelope exceeds budget")
    previous = -1
    for row in rows:
        require(
            type(row) is list
            and len(row) == 2
            and type(row[0]) is int
            and previous < row[0] <= 106
            and type(row[1]) in (int, float)
            and math.isfinite(row[1])
            and 0 <= row[1] <= 1,
            "Hand envelope requires bounded increasing source ticks and weights",
        )
        previous = row[0]
    require(
        (rows[0] == [0, 0] and rows[-1] == [106, 0]) or rows == [[0, 1], [106, 1]],
        "Hand requires neutral endpoints or an explicit constant full-clip pose",
    )
    return value
