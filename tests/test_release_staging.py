"""Invented packages exercise release integrity gates, never native acceptance."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import zipfile

import pytest

spec=importlib.util.spec_from_file_location('stage_release',Path(__file__).resolve().parents[1]/'scripts/stage_release.py')
release=importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
SHA='a'*40
TAG='v0.1.0-beta.1'


@pytest.fixture
def staged(tmp_path):
    source=tmp_path/'source'; staging=tmp_path/'staging'
    (source/'docs/media').mkdir(parents=True);staging.mkdir()
    (source/'pyproject.toml').write_text('[project]\nversion="0.1.0b1"\n')
    image=b'invented approved capture'
    (source/'docs/media/SHA256SUMS').write_text(hashlib.sha256(image).hexdigest()+'  workshop-overview.png\n')
    run={'id':123,'head_sha':SHA,'repository':{'full_name':'vyanhursky/defjam-ffny-fighter-workshop'},
         'status':'completed','conclusion':'success','path':'.github/workflows/desktop.yml',
         'event':'push','head_branch':'develop/0.1','html_url':'https://example.invalid/invented-ci'}
    (staging/'ci-run.json').write_text(json.dumps(run))
    (staging/'ci-jobs.json').write_text(json.dumps({'jobs':[{'name':t,'conclusion':'success'} for t in release.TARGETS]}))
    (staging/'ci-artifacts.json').write_text(json.dumps({'artifacts':[{'name':'workshop-'+t,'id':i} for i,t in enumerate(release.TARGETS)]}))
    for target,extension in release.TARGETS.items():
        app='defjam-ffny-fighter-workshop'
        base=app+'.app/Contents/Resources' if target.startswith('macos') else app
        files={base+'/documentation/docs/media/workshop-overview.png':image,
               base+'/documentation/dependency-licenses/invented/LICENSE.txt':b'invented notice'}
        exe=app+'.app/Contents/MacOS/'+app if target.startswith('macos') else app+'/'+app+('.exe' if target.startswith('windows') else '')
        files[exe]=(b'MZ\x00\x00' if target.startswith('windows') else b'\xcf\xfa\xed\xfe' if target.startswith('macos') else b'\x7fELF')+b'invented executable header'
        folder=staging/'artifacts'/('workshop-'+target);folder.mkdir(parents=True)
        archive=folder/f'{app}-0.1.0b1-{target}.{extension}'
        if extension=='zip':
            with zipfile.ZipFile(archive,'w') as z:
                for name,data in files.items():z.writestr(name,data)
        else:
            with tarfile.open(archive,'w:gz') as z:
                for name,data in files.items():
                    info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o755 if name==exe else 0o644
                    z.addfile(info,io.BytesIO(data))
        Path(str(archive)+'.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
        receipt=staging/'artifacts'/('startup-'+target);receipt.mkdir()
        platform='darwin' if target.startswith('macos') else 'win32' if target.startswith('windows') else 'linux'
        (receipt/'startup.json').write_text(json.dumps({'passed':True,'frozen':True,'icon_loaded':True,'platform':platform,
            'details':{'webchannel':True,'webgl':'WebGL 2 synthetic fixture','profiles':0,'selected':None}}))
    return source,staging


def test_stages_exact_native_packages_with_checksums_and_source_provenance(staged):
    source,staging=staged
    release.prepare(source,staging,SHA,123,TAG)
    provenance=json.loads((staging/'assets/provenance.json').read_text())
    assert provenance['source_commit']==SHA and len(provenance['packages'])==4
    assert len((staging/'assets/SHA256SUMS').read_text().splitlines())==4
    assert len(list((staging/'assets').iterdir()))==10


def test_rejects_successful_ci_for_another_commit(staged):
    source,staging=staged
    with pytest.raises(AssertionError):release.prepare(source,staging,'b'*40,123,TAG)
    assert not (staging/'assets').exists()


def test_rejects_modified_archive_despite_successful_ci_metadata(staged):
    source,staging=staged
    archive=next((staging/'artifacts/workshop-windows-x64').glob('*.zip'))
    archive.write_bytes(archive.read_bytes()+b'tampered')
    with pytest.raises(AssertionError):release.prepare(source,staging,SHA,123,TAG)


def test_rejects_game_executable_even_with_recomputed_checksum(staged):
    source,staging=staged
    archive=next((staging/'artifacts/workshop-windows-x64').glob('*.zip'))
    with zipfile.ZipFile(archive,'a') as z:z.writestr('defjam_recomp.exe',b'invented forbidden game executable')
    Path(str(archive)+'.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
    with pytest.raises(AssertionError):release.prepare(source,staging,SHA,123,TAG)


def test_rejects_an_unapproved_capture_in_an_otherwise_valid_archive(staged):
    source,staging=staged
    (source/'docs/media/SHA256SUMS').write_text(hashlib.sha256(b'new capture').hexdigest()+'  workshop-overview.png\n')
    with pytest.raises(AssertionError):release.prepare(source,staging,SHA,123,TAG)


def test_checks_uploaded_digests_and_keeps_a_failed_draft_unpublished(staged):
    source,staging=staged
    release.prepare(source,staging,SHA,123,TAG)
    assets=staging/'assets'
    metadata={'tag_name':TAG,'draft':True,'prerelease':True,'assets':[
        {'name':p.name,'state':'uploaded','size':p.stat().st_size,'digest':'sha256:'+release.digest(p)} for p in assets.iterdir()]}
    report=staging/'upload.json';report.write_text(json.dumps(metadata))
    release.verify_uploaded(assets,report,TAG)
    metadata['assets'][0]['digest']='sha256:'+'0'*64
    report.write_text(json.dumps(metadata))
    with pytest.raises(AssertionError):release.verify_uploaded(assets,report,TAG)


def test_draft_lookup_resumes_only_the_same_unpublished_source(tmp_path):
    path=tmp_path/'releases.json'
    path.write_text('[]')
    assert release.find_draft(path,TAG,SHA) is None
    draft={'id':42,'tag_name':TAG,'draft':True,'prerelease':True,'target_commitish':SHA}
    path.write_text(json.dumps([[draft]]))
    assert release.find_draft(path,TAG,SHA)==42
    with pytest.raises(AssertionError):release.find_draft(path,TAG,'b'*40)
    draft['draft']=False
    path.write_text(json.dumps([draft]))
    with pytest.raises(AssertionError):release.find_draft(path,TAG,SHA)
