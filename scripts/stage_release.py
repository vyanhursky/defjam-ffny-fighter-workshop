"""Audit exact green native CI artifacts and stage an owner-authorized beta draft.

No network calls and no publication. The staging workflow fetches authenticated
metadata; this script verifies its source binding, packages and uploaded hashes.
"""
import argparse
from pathlib import Path, PurePosixPath
import hashlib,json,os,re,stat,tarfile,tomllib,zipfile

TARGETS={'windows-x64':'zip','macos-arm64':'zip','macos-x64':'zip','linux-x64':'tar.gz'}

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def prepare(REPO, ROOT, EXPECTED_SHA, RUN_ID, TAG):
    assert re.fullmatch(r"[0-9a-f]{40}",EXPECTED_SHA)
    assert RUN_ID>0
    VERSION=tomllib.loads((REPO/'pyproject.toml').read_text())['project']['version']
    match=re.fullmatch(r"(\d+\.\d+\.\d+)b(\d+)",VERSION)
    assert match and TAG==f"v{match[1]}-beta.{match[2]}", 'Tag must match the beta package version'
    run=json.loads((ROOT/'ci-run.json').read_text())
    jobs=json.loads((ROOT/'ci-jobs.json').read_text())['jobs']
    artifacts=json.loads((ROOT/'ci-artifacts.json').read_text())['artifacts']
    assert run['id']==RUN_ID and run['head_sha']==EXPECTED_SHA
    assert run['repository']['full_name']=='vyanhursky/defjam-ffny-fighter-workshop'
    assert run['status']=='completed' and run['conclusion']=='success'
    assert run['path']=='.github/workflows/desktop.yml' and run['event']=='push'
    assert run['head_branch']=='develop/0.1'
    assert len(jobs)==4 and all(j['conclusion']=='success' for j in jobs)
    assert all(sum(target in j['name'] for j in jobs)==1 for target in TARGETS)
    artifact_index={a['name']:a for a in artifacts}
    media={name:sha for sha,name in (line.split() for line in (REPO/'docs/media/SHA256SUMS').read_text().splitlines())}
    output=ROOT/'assets'
    output.mkdir(exist_ok=False)
    records=[]
    for target,extension in TARGETS.items():
        name=f'defjam-ffny-fighter-workshop-{VERSION}-{target}.{extension}'
        folder=ROOT/'artifacts'/('workshop-'+target)
        archive=folder/name
        sidecar=folder/(name+'.sha256')
        expected,filename=sidecar.read_text().split()
        assert filename==name
        actual=digest(archive)
        assert actual==expected
        receipt=json.loads((ROOT/'artifacts'/('startup-'+target)/'startup.json').read_text())
        assert receipt['passed'] and receipt['frozen'] and receipt['icon_loaded']
        assert receipt['details']['webchannel'] and 'WebGL 2' in receipt['details']['webgl']
        assert receipt['details']['profiles']==0 and receipt['details']['selected'] is None
        expected_platform='darwin' if target.startswith('macos') else 'win32' if target.startswith('windows') else 'linux'
        assert receipt['platform']==expected_platform
        names=[]
        approved_seen=set()
        notices_seen=False
        entrypoint_seen=False
        app='defjam-ffny-fighter-workshop'
        entrypoint=(f'{app}.app/Contents/MacOS/{app}' if target.startswith('macos')
                    else f'{app}/{app}.exe' if target.startswith('windows') else f'{app}/{app}')
        def check_name(entry):
            nonlocal notices_seen
            path=PurePosixPath(entry)
            assert not path.is_absolute() and '..' not in path.parts and '\\' not in entry,entry
            assert path.suffix.lower() not in {'.xbe','.viv','.mad','.xsh','.xbx','.djprofile','.glb'},entry
            assert 'defjam_recomp' not in path.name.lower(),entry
            assert '.caf-disposable-test-data' not in path.name,entry
            assert '/save/UserData/' not in '/'+entry,entry
            if 'documentation/dependency-licenses/' in entry:notices_seen=True
            names.append(entry)
        if extension=='zip':
            with zipfile.ZipFile(archive) as bundle:
                assert bundle.testzip() is None
                for member in bundle.infolist():
                    check_name(member.filename)
                    if member.is_dir() or stat.S_ISLNK(member.external_attr>>16):continue
                    if member.filename==entrypoint:
                        with bundle.open(member) as stream:header=stream.read(4)
                        assert header.startswith(b'MZ') if target.startswith('windows') else header in (b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe'),target
                        entrypoint_seen=True
                    for image,sha in media.items():
                        if member.filename.endswith('/documentation/docs/media/'+image):
                            assert hashlib.sha256(bundle.read(member)).hexdigest()==sha
                            approved_seen.add(image)
        else:
            with tarfile.open(archive,'r:gz') as bundle:
                for member in bundle:
                    check_name(member.name)
                    if member.issym() or member.islnk():
                        assert not PurePosixPath(member.linkname).is_absolute(),member.name
                    if not member.isfile():continue
                    if member.name==entrypoint:
                        assert bundle.extractfile(member).read(4)==b'\x7fELF' and member.mode&stat.S_IXUSR
                        entrypoint_seen=True
                    for image,sha in media.items():
                        if member.name.endswith('/documentation/docs/media/'+image):
                            assert hashlib.sha256(bundle.extractfile(member).read()).hexdigest()==sha
                            approved_seen.add(image)
        assert approved_seen==set(media), (target,'Missing approved offline README images',approved_seen)
        assert notices_seen,(target,'Missing dependency license notices')
        assert entrypoint_seen,(target,'Missing native workshop executable')
        for source in (archive,sidecar):
            try:os.link(source,output/source.name)
            except OSError:
                import shutil
                shutil.copy2(source,output/source.name)
        records.append({'target':target,'filename':name,'sha256':actual,'size':archive.stat().st_size,
                        'ci_artifact_id':artifact_index['workshop-'+target]['id'],
                        'archive_entries':len(names),'startup':receipt,
                        'audit':{'no_save_dump_or_compiled_game_files':True,'approved_readme_images_verified':True,'dependency_notices_present':True}})
        print(target,'verified',archive.stat().st_size,'bytes;',len(names),'archive entries',flush=True)

    (output/'SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['filename']+'\n' for r in sorted(records,key=lambda r:r['filename'])))
    provenance={'schema':1,'project':'defjam-ffny-fighter-workshop','tag':TAG,'package_version':VERSION,
                'source_repository':'https://github.com/vyanhursky/defjam-ffny-fighter-workshop',
                'source_commit':EXPECTED_SHA,'ci_run_id':RUN_ID,'ci_run_url':run['html_url'],
                'workflow':'.github/workflows/desktop.yml','publisher_commit':os.environ.get('GITHUB_SHA'),'packages':records,'approved_readme_images':media,
                'scope':'Standalone workshop editor packages, not game executables. Game artwork in icons and approved documentation captures is outside the project MIT license.'}
    (output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print('Release assets assembled:',output,flush=True)


def verify_uploaded(assets, metadata, tag):
    release=json.loads(metadata.read_text())
    assert release['tag_name']==tag and release['draft'] and release['prerelease']
    expected={p.name:p for p in assets.iterdir() if p.is_file()}
    uploaded={a['name']:a for a in release['assets']}
    assert len(uploaded)==len(release['assets']) and set(uploaded)==set(expected)
    for name,path in expected.items():
        asset=uploaded[name]
        assert asset['state']=='uploaded' and asset['size']==path.stat().st_size,name
        assert asset.get('digest')=='sha256:'+digest(path),name
    print('All uploaded GitHub asset digests match:',len(expected))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--staging',type=Path,required=True)
    ap.add_argument('--source-sha',required=True)
    ap.add_argument('--run-id',type=int,required=True)
    ap.add_argument('--tag',required=True)
    ap.add_argument('--verify-upload',type=Path)
    args=ap.parse_args()
    if args.verify_upload:
        verify_uploaded(args.staging/'assets',args.verify_upload,args.tag)
    else:
        prepare(args.source,args.staging,args.source_sha,args.run_id,args.tag)


if __name__=='__main__':
    main()
