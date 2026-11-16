"""Invented bind-space points; parity oracle is the actual export generator."""

import json
from defjam_caf import face_geometry as fg

points = [
    [x, y, z] for x in (-1.0, -0.5, 0.0, 0.5, 1.0) for y in (19.0, 19.4, 20.0, 20.6, 21.0) for z in (0.0, 1.0, 2.0)
]
meshes = [dict(rm=0, positions=points, uvs=[[0.0, 0.0] for _ in points], indices=[0, 1, 2])]
ref = dict(schema="ffny-face-template-1", basis=[0, 1, 1, 1, 1, 1], meshes=meshes)
ref["sha256"] = fg.digest(ref)
cases = [
    {},
    {key: 1 for key, _ in fg.CONTROLS},
    {key: -1 for key, _ in fg.CONTROLS},
    dict(face_width=0.73, nose_projection=-0.49, eye_size=0.22, brow_height=0.16, jaw_width=-0.64),
]
print(
    json.dumps(
        dict(
            basis=fg.preview_basis(ref),
            cases=[dict(values=v, expected=fg.apply(dict(meshes=meshes), fg.sliders(ref, v))["meshes"]) for v in cases],
        )
    )
)
