import base64
import copy
import io

import pytest
from PIL import Image

from defjam_caf import projects
from defjam_caf.container import SaveError
from defjam_caf.editor import Editor
from test_projects import fields


def png(size=(256, 256), color=(200, 80, 30, 7)):
    stream = io.BytesIO()
    Image.new('RGBA', size, color).save(stream, format='PNG')
    return stream.getvalue()


def test_import_upgrades_copy_preserves_exact_source_and_v1_parent(tmp_path):
    original = projects.from_fields(fields()[0], 'Example')
    before = projects.encoded(original)
    restored = projects.with_atlas(original, 'a', png())
    assert restored['schema'] == projects.SCHEMA2 and projects.encoded(original) == before
    assert projects.atlas_bytes(restored['textures']['atlases']['a']) == png()
    assert restored['identity'] == original['identity']
    path = tmp_path / 'art.ffnyfighter'
    projects.write(path, restored)
    assert projects.read(path)[0] == restored


def test_outfit_change_refuses_stale_atlas_but_training_and_styles_remain_editable():
    restored = projects.with_atlas(projects.from_fields(fields()[0], 'Example'), 'd', png())
    changed = copy.deepcopy(restored)
    changed['fighter']['stats']['health'] = 42
    changed['fighter']['styles'] = [1, 0, 3]
    assert projects.validate(changed) is changed
    changed['fighter']['caf_values'][0] = 1
    with pytest.raises(SaveError, match='Appearance changed'):
        projects.validate(changed)


@pytest.mark.parametrize('slot,image', [('unknown', png()), ('a', png((128, 128))), ('a', b'not PNG')])
def test_invalid_atlas_does_not_change_parent(slot, image):
    original = projects.from_fields(fields()[0], 'Example')
    before = projects.encoded(original)
    with pytest.raises(SaveError):
        projects.with_atlas(original, slot, image)
    assert projects.encoded(original) == before


def test_editor_tracks_assets_for_close_reset_save_reopen_and_copy(tmp_path):
    document = projects.from_fields(fields()[0], 'Example')
    document['schema'] = projects.SCHEMA2
    document['fighter']['finishers'] = ['00000001', '00000002', '00000003', '00000004']
    path = tmp_path / 'fighter.ffnyfighter'
    projects.write(path, document)
    editor = Editor(tmp_path / 'work')
    editor.open_project(path)
    staged = editor.request('project_atlas', {'slot': 'd1', 'png': base64.b64encode(png()).decode()})
    assert staged['dirty'] and staged['atlas_slots'] == ['d1'] and 'Project texture atlases changed' in editor.changes()
    assert 'textures' not in projects.read(path)[0]
    assert not editor.request('reset', {})['dirty']
    editor.request('project_atlas', {'slot': 'd', 'png': base64.b64encode(png()).decode()})
    editor.stage({'stats': {'health': 42}})
    editor.request('save', {})
    assert not editor.snapshot()['dirty']
    editor.open_project(path)
    assert editor.snapshot()['atlas_slots'] == ['d']
    assert projects.read(path)[0]['fighter']['finishers'] == document['fighter']['finishers']
    editor.create_project(tmp_path / 'variant.ffnyfighter')
    assert editor.project['textures'] == projects.read(path)[0]['textures']
    assert editor.project['fighter']['finishers'] == document['fighter']['finishers']
    editor.request('project_atlas_clear', {})
    editor.request('save', {})
    assert not editor.snapshot()['atlas_slots'] and not editor.snapshot()['dirty']


def test_preview_uses_imported_rgb_with_exact_original_material_alpha(tmp_path):
    document = projects.with_atlas(projects.from_fields(fields()[0], 'Example'), 'a', png())
    path = tmp_path / 'fighter.ffnyfighter'
    projects.write(path, document)
    editor = Editor(tmp_path / 'work')
    editor.open_project(path)
    from types import SimpleNamespace
    native = 'data:image/png;base64,' + base64.b64encode(png(color=(1, 2, 3, 219))).decode()
    editor.appearance = SimpleNamespace(outfit=lambda _: {})
    editor.cache = SimpleNamespace(compose=lambda _: {'textures': {'a': native}, 'notices': []})
    preview = editor.preview()
    result = Image.open(io.BytesIO(base64.b64decode(preview['textures']['a'].split(',')[1])))
    assert result.getpixel((128, 128)) == (200, 80, 30, 219)
    assert projects.atlas_bytes(editor.project['textures']['atlases']['a']) == png()


def test_stale_assets_can_be_cleared_after_outfit_edit(tmp_path):
    document = projects.with_atlas(projects.from_fields(fields()[0], 'Example'), 'a', png())
    path = tmp_path / 'fighter.ffnyfighter'; projects.write(path, document)
    editor = Editor(tmp_path / 'work'); editor.open_project(path)
    values = document['fighter']['caf_values'][:]; values[0] = 1
    editor.stage({'caf_values': values})
    with pytest.raises(SaveError, match='Appearance changed'):
        editor.request('save', {})
    editor.request('project_atlas_clear', {})
    editor.request('save', {})
    assert projects.read(path)[0]['fighter']['caf_values'][0] == 1


def test_profile_conversion_resolves_finishers_and_never_silently_discards_them():
    import struct
    payload = bytearray(fields()[1])
    values = [0x06000000 + i for i in range(4)]
    struct.pack_into('<4I', payload, 0x120, *values)
    class Shop:
        def word(self, offset):
            return 24 if offset == 12 else offset // 4
        def mapping(self, offset, tag):
            return {0x47D305FD ^ 0x6FC83815: (4, 2)}
    class Database:
        shop = Shop()
        def packed(self, value):
            return 0x47D305FD, value & 65535, 123 + (value & 65535), (value & 65535) * 4, 0
    result = projects.from_profile(bytes(payload), 'Example', Database())
    assert result['fighter']['finishers'] == ['0000007b', '0000007c', '0000007d', '0000007e']
    with pytest.raises(SaveError, match='preserve saved'):
        projects.from_profile(bytes(payload), 'Example')
    class Unknown(Database):
        def packed(self, value):
            raise ValueError('Unknown saved item row')
    with pytest.raises(SaveError, match='Unsupported saved finisher.*Unknown'):
        projects.from_profile(bytes(payload), 'Example', Unknown())
    struct.pack_into('<I', payload, 0x120, 0xFFFFFFFF)
    with pytest.raises(SaveError, match='Partial saved'):
        projects.from_profile(bytes(payload), 'Example', Database())
    struct.pack_into('<4I', payload, 0x120, *([0xFFFFFFFF] * 4))
    assert projects.from_profile(bytes(payload), 'Example')['schema'] == projects.SCHEMA


@pytest.mark.parametrize('version2', [False, True])
def test_export_declares_matching_runtime_and_unchanged_atlas_bytes(tmp_path, monkeypatch, version2):
    import hashlib
    import json
    import zipfile
    from defjam_caf import fighter_mod
    runtime = tmp_path / 'runtime'
    (runtime / 'setup').mkdir(parents=True); (runtime / 'scripts').mkdir()
    (runtime / 'setup/fighter_caf.py').touch(); (runtime / 'scripts/fighter-contract.py').touch()
    data = tmp_path / 'data'; (data / 'extracted').mkdir(parents=True)
    document = projects.from_fields(fields()[0], 'Example')
    if version2:
        document = projects.with_atlas(document, 'a', png())
    monkeypatch.setattr(fighter_mod, 'contract', lambda *a, **k: {'ok': True, 'native_compilation': True})
    destination = tmp_path / 'export.zip'
    fighter_mod.export_mod(document, destination, runtime, data, tmp_path / 'work')
    prefix = document['identity']['pack'] + '/'
    capability = 'caf-fighter-2' if version2 else 'caf-fighter-1'
    with zipfile.ZipFile(destination) as archive:
        manifest = json.loads(archive.read(prefix + 'fighters.json'))
        assert manifest['resources'][0]['source']['format'] == capability
        assert (capability + ' support') in archive.read(prefix + 'README.md').decode()
        if version2:
            recipe = json.loads(archive.read(prefix + 'fighter.json'))
            assert recipe['atlases']['a']['sha256'] == hashlib.sha256(png()).hexdigest()
            assert archive.read(prefix + 'atlases/a.png') == png()
