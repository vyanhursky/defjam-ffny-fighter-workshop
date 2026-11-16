"""Game-free geometry encoding benchmark; source values emulate native float32."""

import json
import statistics
import time
import numpy as np
from defjam_caf.preview_transport import pack_preview


def main():
    rng = np.random.default_rng(7)
    mesh = {
        name: rng.random((12000, width), dtype=np.float32).tolist()
        for name, width in [("positions", 3), ("normals", 3), ("uv", 2)]
    }
    mesh["indices"] = list(range(12000))
    source = {"meshes": [mesh]}

    def measure(operation):
        times = []
        for _ in range(5):
            start = time.perf_counter()
            raw = operation()
            times.append((time.perf_counter() - start) * 1000)
        return len(raw.encode()), round(statistics.median(times), 2)

    before = measure(lambda: json.dumps(source))
    after = measure(lambda: json.dumps(pack_preview(source)))
    print(
        json.dumps(
            dict(
                fixture="12000 invented vertices, 12000 indices",
                list_json=dict(bytes=before[0], encode_ms=before[1]),
                typed_json=dict(bytes=after[0], pack_and_encode_ms=after[1]),
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
