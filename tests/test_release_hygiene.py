import importlib.metadata
from pathlib import Path
import runpy
import tomllib

import pytest

from defjam_caf import __version__, projects, retail
from defjam_caf.cli import main
from defjam_caf.container import SaveError
from test_projects import fields


def test_package_version_matches_release_source():
    root = Path(__file__).resolve().parents[1]
    assert __version__ == tomllib.loads((root / 'pyproject.toml').read_text())['project']['version']


def test_uninstalled_checkout_uses_pyproject(monkeypatch):
    def missing(name):
        raise importlib.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(importlib.metadata, 'version', missing)
    import defjam_caf
    assert runpy.run_path(defjam_caf.__file__)['__version__'] == __version__


def test_cli_imports_hd_png_larger_than_one_mib(tmp_path):
    from PIL import Image
    # Deterministic invented pixels, stored without compression to exceed 1 MiB.
    png = tmp_path / 'atlas.png'
    Image.new('RGBA', (1024, 1024), (9, 18, 27, 255)).save(png, compress_level=0)
    assert 1024**2 < png.stat().st_size < projects.MAX_ATLAS_BYTES
    original, output = tmp_path / 'before.ffnyfighter', tmp_path / 'after.ffnyfighter'
    projects.write(original, projects.from_fields(fields()[0], 'Example'))
    assert main(['import-atlas', str(original), '--slot', 'a', '--png', str(png), '--out', str(output)]) == 0
    assert projects.atlas_bytes(projects.read(output)[0]['textures']['atlases']['a']) == png.read_bytes()


def test_manifest_chooser_and_import_share_bounded_reader(tmp_path):
    path = tmp_path / 'fighters.json'
    with path.open('wb') as output:
        output.truncate(retail.MAX_MANIFEST_BYTES + 1)
    for read in (lambda: retail.read_manifest(tmp_path), lambda: retail.import_pack(tmp_path, 'fighter')):
        with pytest.raises(SaveError, match='manifest exceeds'):
            read()
    path.write_bytes(b'\xef\xbb\xbf{"fighters": []}')
    assert retail.read_manifest(tmp_path) == {'fighters': []}
