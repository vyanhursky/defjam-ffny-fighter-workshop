"""Invented move database; no retail labels, assets or profile bytes."""
from types import SimpleNamespace

import pytest

from defjam_caf.blazin import Catalog, TABLE, CHOICE, DISPLAY_NAME, PREFIX
from defjam_caf import projects
from defjam_caf.container import Container, SaveError
from defjam_caf.editor import Editor
from defjam_caf.fields import apply_fields, read_fields
from test_projects import fields


class Database:
    def __init__(self):
        self.shop = self
        self.schema = {TABLE ^ CHOICE: (4, 2), TABLE ^ DISPLAY_NAME: (3, 1)}
    def mapping(self, offset, tag):
        return self.schema
    def records(self, table):
        assert table == TABLE
        return [(ident, (100 + i * 24,)) for i, ident in enumerate((77, 88, 99, 111))]
    def word(self, offset):
        if offset == 12:
            return 24
        i, member = divmod(offset - 100, 24)
        return 3 - i if member == 16 else i
    def string(self, index):
        return ('Zulu', 'Alpha', 'Gamma', 'Beta')[index]
    def value_for(self, table, identity):
        assert table == TABLE
        return 0x02000000 + (77, 88, 99, 111).index(identity)


def catalog():
    return Catalog(Database())


def move_keys():
    return [PREFIX + f'{n:08x}' for n in (77, 88, 99, 111)]


def test_catalog_names_sort_independently_from_native_order_and_identity():
    c = catalog()
    assert [r['label'] for r in c.options] == ['Alpha', 'Beta', 'Gamma', 'Zulu']
    assert [r['choice'] for r in c.select(move_keys())] == [3, 2, 1, 0]
    assert [r['value'] for r in c.select(move_keys())] == list(range(0x02000000, 0x02000004))
    assert len(c.select([move_keys()[1]] * 4)) == 4  # Retail CAFs may repeat moves.
    c.database.schema[TABLE ^ DISPLAY_NAME] = (2, 1)
    with pytest.raises(SaveError, match='schema'):
        Catalog(c.database)


@pytest.mark.parametrize('selection', [[], move_keys()[:3], move_keys() + ['extra'],
    ['custom/future-move'] * 4, ['retail/blazin-deadbeef'] * 4, [True] * 4])
def test_unknown_incomplete_or_future_unsupported_selections_fail_closed(selection):
    with pytest.raises(SaveError, match='four available'):
        catalog().select(selection)


def test_profile_patch_changes_only_four_reference_words():
    original = Container(bytes(64), fields()[1])
    values = [row['value'] for row in catalog().select(move_keys())]
    result = apply_fields(original, {'blazin_values': values})
    assert result.payload[:0x120] == original.payload[:0x120]
    assert result.payload[0x130:] == original.payload[0x130:]
    assert result.metadata == original.metadata
    assert read_fields(result.payload)['blazin_values'] == values
    for bad in ([1] * 3, [True] * 4, [0xFFFFFFFF] * 4):
        with pytest.raises(SaveError):
            apply_fields(original, {'blazin_values': bad})


def test_profile_edits_use_normal_history_reset_and_named_change_review(tmp_path):
    editor = Editor(tmp_path); editor.blazin = catalog(); editor.blazin_error = None
    editor.profile = SimpleNamespace(container=Container(bytes(64), fields()[1]), name='DEMO')
    before = editor.current().encode()
    editor.request('blazin', {'moves': move_keys()})
    assert editor.snapshot()['dirty'] and editor.snapshot()['undo']
    assert editor.snapshot()['blazin']['selected'] == move_keys()
    assert "Blazin' slot 1: Zulu" in editor.changes()
    editor.request('undo', {})
    assert editor.current().encode() == before and not editor.snapshot()['dirty']
    editor.request('blazin', {'moves': [move_keys()[2]] * 4})
    editor.request('reset', {})
    assert editor.current().encode() == before
    with pytest.raises(SaveError):
        editor.stage({'blazin_values': [0xFFFFFFFF] * 4})
    assert editor.current().encode() == before


def test_project_selection_save_copy_variant_reopen_and_inherit_preserve_identity(tmp_path):
    project = projects.from_fields(fields()[0], 'Example')
    path = tmp_path / 'fighter.ffnyfighter'; projects.write(path, project)
    editor = Editor(tmp_path); editor.blazin = catalog(); editor.open_project(path)
    assert editor.snapshot()['blazin']['selected'] == [None] * 4
    editor.request('blazin', {'moves': move_keys()})
    assert editor.snapshot()['dirty'] and 'finishers' not in project['fighter']
    editor.request('save', {})
    updated = projects.read(path)[0]
    expected = [f'{n:08x}' for n in (77, 88, 99, 111)]
    assert updated['schema'] == projects.SCHEMA and updated['fighter']['finishers'] == expected
    assert updated['identity'] == project['identity']
    copy_path = tmp_path / 'copy.ffnyfighter'; editor.request('export', {'path': str(copy_path)})
    assert projects.read(copy_path)[0]['fighter']['finishers'] == expected
    editor.open_project(copy_path)
    editor.request('blazin', {'moves': [move_keys()[0]] * 4})
    editor.request('undo', {})
    assert editor.snapshot()['blazin']['selected'] == move_keys() and not editor.snapshot()['dirty']
    editor.create_project(tmp_path / 'variant.ffnyfighter')
    assert editor.project['fighter']['finishers'] == expected
    assert editor.project['identity'] != project['identity']
    editor.request('blazin_inherit', {})
    assert editor.snapshot()['blazin']['selected'] == [None] * 4 and editor.snapshot()['dirty']
    editor.request('save', {})
    assert 'finishers' not in editor.project['fighter']


def test_missing_assets_and_unknown_saved_selections_are_preserved(tmp_path):
    doc = projects.from_fields(fields()[0], 'Example'); doc['schema'] = projects.EARLIER_SCHEMAS[1]  # a project saved by an earlier build
    doc['fighter']['finishers'] = ['deadbeef'] * 4
    path = tmp_path / 'fighter.ffnyfighter'; projects.write(path, doc)
    editor = Editor(tmp_path); editor.open_project(path)
    with pytest.raises(SaveError, match='Load original'):
        editor.request('blazin', {'moves': move_keys()})
    assert not editor.snapshot()['dirty'] and projects.read(path)[0] == doc
    editor.blazin = catalog()
    assert editor.snapshot()['blazin']['selected'] == [PREFIX + 'deadbeef'] * 4
    editor.request('blazin', {'moves': move_keys()})
    editor.request('reset', {})
    assert editor.project_document() == doc


def test_blazin_changes_do_not_stale_outfit_bound_textures(tmp_path):
    from test_project_atlases import png
    doc = projects.with_atlas(projects.from_fields(fields()[0], 'Example'), 'a', png())
    path = tmp_path / 'fighter.ffnyfighter'; projects.write(path, doc)
    editor = Editor(tmp_path); editor.blazin = catalog(); editor.open_project(path)
    editor.request('blazin', {'moves': move_keys()})
    assert editor.project_document()['textures'] == doc['textures']
