"""Typed, little-endian geometry for WebChannel only; editor/script APIs retain lists."""

import base64
import numpy as np
from .container import SaveError

MAX_ATTRIBUTE_BYTES = 32 * 1024**2


def attribute(array, components, kind):
    if array.nbytes > MAX_ATTRIBUTE_BYTES:
        raise SaveError("The preview geometry exceeds its supported size.")
    return dict(
        kind=kind, components=components, count=int(array.size), data=base64.b64encode(array.tobytes()).decode("ascii")
    )


def pack_preview(value):
    if not isinstance(value, dict) or "meshes" not in value:
        return value
    result = dict(value)
    result["meshes"] = []
    for mesh in value["meshes"]:
        attributes = {}
        count = None
        for name, components in (("positions", 3), ("normals", 3), ("uv", 2)):
            array = np.asarray(mesh[name], dtype="<f4")
            if array.ndim != 2 or array.shape[1] != components or not np.isfinite(array).all():
                raise SaveError("The preview geometry is invalid.", detail="Invalid " + name + " attribute")
            if count is None:
                count = len(array)
            if len(array) != count:
                raise SaveError("The preview geometry is invalid.", detail="Mismatched vertex attribute counts")
            attributes[name] = attribute(array, components, "f32le")
        indices = np.asarray(mesh["indices"])
        if indices.ndim != 1 or (
            indices.size and (indices.dtype.kind not in "iu" or indices.min() < 0 or indices.max() >= count)
        ):
            raise SaveError("The preview geometry is invalid.", detail="Index leaves vertex buffer")
        wide = indices.size and indices.max() > 65535
        attributes["indices"] = attribute(indices.astype("<u4" if wide else "<u2"), 1, "u32le" if wide else "u16le")
        result["meshes"].append(
            {
                **{k: v for k, v in mesh.items() if k not in attributes},
                "geometry": dict(encoding="typed-geometry-1", attributes=attributes),
            }
        )
    return result
