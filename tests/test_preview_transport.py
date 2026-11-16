import base64
import numpy as np
import pytest
from defjam_caf.preview_transport import pack_preview
from defjam_caf.container import SaveError


def mesh(count):
    return dict(
        positions=np.zeros((count, 3)),
        normals=np.zeros((count, 3)),
        uv=np.zeros((count, 2)),
        indices=[0, count - 1],
        atlas="a",
    )


@pytest.mark.parametrize(("count", "kind"), [(2, "u16le"), (65537, "u32le")])
def test_preview_buffers_preserve_index_width_and_little_endian_values(count, kind):
    source = mesh(count)
    packed = pack_preview({"meshes": [source]})["meshes"][0]
    assert "positions" in source and "positions" not in packed
    indices = packed["geometry"]["attributes"]["indices"]
    assert indices["kind"] == kind
    dtype = "<u4" if kind == "u32le" else "<u2"
    assert np.frombuffer(base64.b64decode(indices["data"]), dtype=dtype).tolist() == source["indices"]


def test_invalid_geometry_is_refused_before_transport():
    source = mesh(2)
    source["indices"] = [2]
    with pytest.raises(SaveError, match="invalid"):
        pack_preview({"meshes": [source]})
