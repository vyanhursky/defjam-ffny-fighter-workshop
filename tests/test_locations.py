from pathlib import Path

from defjam_caf.locations import default_data_directory, initial_data_directory
from test_profiles import invented_profile


def test_mac_installer_default_opens_existing_saves_without_writing(tmp_path):
    data = tmp_path / 'Library/Application Support/DefJamRecompiled/data'
    assert default_data_directory(platform='darwin', home=tmp_path) == data
    assert initial_data_directory(platform='darwin', home=tmp_path) is None
    assert not data.exists()
    title = data / 'save/UserData/45410049'
    invented_profile(title)
    before = {p.relative_to(data): p.read_bytes() for p in data.rglob('*') if p.is_file()}
    assert initial_data_directory(platform='darwin', home=tmp_path) == data
    assert {p.relative_to(data): p.read_bytes() for p in data.rglob('*') if p.is_file()} == before


def test_explicit_data_path_always_wins_over_mac_default(tmp_path):
    data = default_data_directory(platform='darwin', home=tmp_path)
    invented_profile(data / 'save/UserData/45410049')
    explicit = tmp_path / 'my other data'
    assert initial_data_directory(explicit, platform='darwin', home=tmp_path) == explicit
    assert not explicit.exists()


def test_other_platforms_keep_manual_data_selection(tmp_path):
    for platform in ('linux', 'win32'):
        assert default_data_directory(platform=platform, home=tmp_path) is None
        assert initial_data_directory(platform=platform, home=tmp_path) is None
        assert initial_data_directory(Path('chosen'), platform=platform, home=tmp_path) == Path('chosen')
