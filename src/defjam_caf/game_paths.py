"""Read Xbox asset paths on case-sensitive hosts without changing the dump."""
from pathlib import Path, PurePosixPath


def game_file(dump, relative):
    parts = PurePosixPath(relative).parts
    if not parts or PurePosixPath(relative).is_absolute() or ".." in parts or "\\" in relative:
        raise ValueError("Expected a relative Xbox asset path")
    current = Path(dump)
    for part in parts:
        matches = [p for p in current.iterdir() if p.name.casefold() == part.casefold()]
        if len(matches) > 1:
            raise ValueError("Ambiguous Xbox asset path: " + relative)
        if not matches:
            raise FileNotFoundError("Missing Xbox asset: " + relative)
        current = matches[0]
    if not current.is_file():
        raise FileNotFoundError("Expected Xbox asset file: " + relative)
    return current
