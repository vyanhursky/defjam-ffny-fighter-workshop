"""Cross-platform boundaries that can damage portability or profile identities."""
import importlib.util
import os
from pathlib import Path
import stat
import tarfile

import pytest

from defjam_caf.container import SaveError
from defjam_caf.game_paths import game_file
from defjam_caf.profiles import discover, directory_name
from defjam_caf.storage import install_files
from test_profiles import invented_profile


def case_sensitive(folder):
    probe = folder / 'case-probe'
    probe.write_bytes(b'')
    result = not (folder / 'CASE-PROBE').exists()
    probe.unlink()
    return result


def test_asset_lookup_uses_actual_spelling_without_mutating_dump(tmp_path):
    asset = tmp_path / 'ASSETS' / 'V2CP_0.VIV'
    asset.parent.mkdir()
    asset.write_bytes(b'invented archive')
    assert game_file(tmp_path, 'assets/v2cp_0.viv') == asset
    assert list(tmp_path.iterdir()) == [asset.parent]
    assert list(asset.parent.iterdir()) == [asset]
    with pytest.raises(FileNotFoundError, match='Missing Xbox asset'):
        game_file(tmp_path, 'assets/misc.viv')
    with pytest.raises(ValueError):
        game_file(tmp_path, '../outside')
    with pytest.raises(ValueError):
        game_file(tmp_path, '/assets/file')
    with pytest.raises(ValueError):
        game_file(tmp_path, r'assets\file')


def test_case_ambiguous_assets_refuse_even_an_exact_match(tmp_path):
    if not case_sensitive(tmp_path):
        pytest.skip('requires a case-sensitive filesystem (covered on Linux CI)')
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'ASSETS').mkdir()
    (tmp_path / 'assets' / 'misc.viv').write_bytes(b'first')
    (tmp_path / 'ASSETS' / 'misc.viv').write_bytes(b'second')
    with pytest.raises(ValueError, match='Ambiguous Xbox asset'):
        game_file(tmp_path, 'assets/misc.viv')


def test_lowercase_identity_cannot_be_installed_twice(tmp_path):
    title = tmp_path / '45410049'
    folder, original = invented_profile(title, 'ZTEST')
    lower = folder.with_name(folder.name.lower())
    folder.rename(lower)
    assert discover(title).profiles[0].path.parent.name == lower.name
    with pytest.raises(SaveError, match='already exists'):
        install_files(title, 'ZTEST', {'ZTEST': b'must not be written'})
    assert (lower / 'ZTEST').read_bytes() == original
    assert not list(title.glob('.caf-import-*'))


def test_lowercase_canonical_still_overrides_legacy(tmp_path):
    title = tmp_path / '45410049'
    folder, _ = invented_profile(title, 'ZTEST')
    folder.rename(folder.with_name(folder.name.lower()))
    assert directory_name('ZTEST') != directory_name('ZTEST', legacy=True)
    invented_profile(title, 'ZTEST', legacy=True)
    result = discover(title)
    assert len(result.profiles) == 1
    assert result.profiles[0].directory_kind == 'canonical'
    assert len(result.issues) == 1


def test_case_duplicate_profile_directories_are_read_only(tmp_path):
    if not case_sensitive(tmp_path):
        pytest.skip('requires a case-sensitive filesystem (covered on Linux CI)')
    title = tmp_path / '45410049'
    folder, _ = invented_profile(title, 'ZTEST')
    other = folder.with_name(folder.name.lower())
    other.mkdir()
    result = discover(title)
    assert not result.profiles
    assert len(result.issues) == 2
    assert all('Case-colliding' in issue['error'] for issue in result.issues)


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX executable modes and symlinks")
def test_linux_archive_preserves_executables_symlinks_and_checksum(tmp_path):
    import hashlib
    spec = importlib.util.spec_from_file_location('package_desktop',
        Path(__file__).resolve().parents[1] / 'scripts/package_desktop.py')
    package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    app = tmp_path / 'application'
    app.mkdir()
    executable = app / 'workshop'
    executable.write_bytes(b'invented executable')
    executable.chmod(0o755)
    (app / 'runtime').symlink_to('workshop')
    archive = package.archive_package(app, 'linux', 'x86_64', '0.1.0b1')
    assert archive.name.endswith('-linux-x64.tar.gz')
    with tarfile.open(archive) as bundle:
        assert bundle.getmember('application/workshop').mode & stat.S_IXUSR
        assert bundle.getmember('application/runtime').issym()
        assert bundle.getmember('application/runtime').linkname == 'workshop'
    assert Path(str(archive) + '.sha256').read_text().split()[0] == hashlib.sha256(archive.read_bytes()).hexdigest()
