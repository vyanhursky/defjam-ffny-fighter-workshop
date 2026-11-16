import base64
import io
import wave

from defjam_caf.audition_cache import AuditionCache
from defjam_caf import audition_cache


def wav():
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24000)
        output.writeframes(b"\x10\0" * 240)
    return stream.getvalue()


def test_cache_reuses_valid_audio_refuses_corruption_and_tracks_source_changes(tmp_path):
    source = tmp_path / "game/audio/speech2.viv"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"invented speech archive")
    cache = AuditionCache(tmp_path / "runtime", tmp_path / "game", tmp_path / "work")
    calls = []
    result = dict(mime="audio/wav", data=base64.b64encode(wav()).decode("ascii"), bytes=len(wav()))

    def load(request):
        calls.append(request)
        return result

    request = dict(category="Character", voice=1, index=0)
    assert cache.voice(request, load) == cache.voice(request, load) == result
    assert len(calls) == 1
    next(cache.root.glob("speech-*.wav")).write_bytes(b"corrupted")
    assert cache.voice(request, load) == result and len(calls) == 2
    source.write_bytes(b"new invented speech archive")
    cache.voice(request, load)
    assert len(calls) == 3


def test_retention_is_bounded_and_preserves_unowned_files(tmp_path, monkeypatch):
    cache = AuditionCache(tmp_path, tmp_path, tmp_path / "work")
    cache.root.mkdir(parents=True)
    unknown = cache.root / "my-recording.wav"
    unknown.write_bytes(b"keep")
    old = cache.root / ("speech-" + "a" * 64 + ".wav")
    new = cache.root / ("speech-" + "b" * 64 + ".wav")
    old.write_bytes(b"12345")
    new.write_bytes(b"12345")
    import os

    os.utime(old, (1, 1))
    monkeypatch.setattr(audition_cache, "MAX_CACHE_BYTES", 5)
    cache.prune()
    assert unknown.exists() and new.exists() and not old.exists()
