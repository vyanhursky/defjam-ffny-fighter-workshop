"""Private, bounded WAV cache. It never becomes part of a fighter project."""

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from .performance import audio_bytes, wav_info

MAX_CACHE_BYTES = 128 * 1024**2
OWNED = re.compile(r"speech-[0-9a-f]{64}\.wav\Z")


class AuditionCache:
    def __init__(self, runtime, game, workspace):
        self.runtime, self.game = Path(runtime), Path(game)
        self.root = Path(workspace) / "auditions"

    def key(self, request):
        paths = [self.game / "audio/speech2.viv", self.runtime / "config/fighter-native-baseline.json"]
        paths += [self.runtime / "scripts/fighter-contract.py"]
        paths += [
            self.runtime / "setup" / name
            for name in ("fighter_workshop.py", "fighter_voice.py", "fighter_voice_r2.py", "fighter_voice_bank.py")
        ]
        stamps = [
            (str(p.resolve()), p.stat().st_size, p.stat().st_mtime_ns) if p.is_file() else (str(p), None) for p in paths
        ]
        return hashlib.sha256(json.dumps([stamps, request], sort_keys=True).encode()).hexdigest()

    def voice(self, request, load):
        path = self.root / ("speech-" + self.key(request) + ".wav")
        try:
            if path.is_file() and not path.is_symlink():
                raw = path.read_bytes() if path.stat().st_size <= 8 * 1024**2 else b""
                wav_info(raw)
                path.touch()
                return dict(mime="audio/wav", data=base64.b64encode(raw).decode("ascii"), bytes=len(raw))
        except (OSError, ValueError):
            pass
        result = load(request)
        if result.get("mime") != "audio/wav":
            return result
        raw = audio_bytes(result["data"])
        temporary = None
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=self.root, prefix=".speech-", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(raw)
            os.replace(temporary, path)
            self.prune()
        except OSError:
            pass  # A cache failure must not prevent auditioning.
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return result

    def prune(self):
        files = [p for p in self.root.iterdir() if OWNED.fullmatch(p.name) and p.is_file() and not p.is_symlink()]
        files.sort(key=lambda p: p.stat().st_mtime_ns, reverse=True)
        used = 0
        for path in files:
            used += path.stat().st_size
            if used > MAX_CACHE_BYTES:
                path.unlink()
