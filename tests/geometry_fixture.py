"""Invented geometry for the Python-to-JavaScript wire contract."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from defjam_caf.preview_transport import pack_preview  # noqa: E402


if __name__ == "__main__":
    print(
        json.dumps(
            pack_preview(
                {
                    "meshes": [
                        dict(
                            positions=[[0.1, -2.5, 3.75], [4, 5, 6]],
                            normals=[[0, 1, 0], [0, 1, 0]],
                            uv=[[0, 0], [1, 1]],
                            indices=[0, 1],
                            atlas="a",
                        )
                    ]
                }
            )
        )
    )
