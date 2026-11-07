"""Application resources and the source-only/private-output boundary."""
from pathlib import Path


def source_root():
    package = Path(__file__).resolve().parent
    for parent in package.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    return package


def require_private_output(path):
    result = Path(path).resolve()
    if result.is_relative_to(source_root()):
        raise ValueError("Keep artwork, models and review workspaces outside the tooling source tree")
    return result
