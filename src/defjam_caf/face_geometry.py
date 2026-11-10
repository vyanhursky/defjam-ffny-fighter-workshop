"""Template-based head sculpts. No imported rig, material or executable data.

Coordinates use the original CAF bind space: X right, Y up, Z forward.
Version 1 retains original render-mesh/vertex order, UVs and triangles.
"""
import copy
import hashlib
import json
import math

from .container import SaveError

SCHEMA = 'ffny-face-sculpt-1'
MAX_OBJ = 2 * 1024 * 1024
MAX_DELTA = 0.6
BASIS_SLOTS = (0, 5, 6, 9, 10, 11)
CONTROLS = (
    ('face_width', 'Face width'), ('jaw_width', 'Jaw width'),
    ('chin_length', 'Chin length'), ('nose_width', 'Nose width'),
    ('nose_projection', 'Nose projection'), ('eye_spacing', 'Eye spacing'),
    ('eye_size', 'Eye size'), ('brow_height', 'Brow height'),
    ('ear_size', 'Ear size'),
)


def require(ok, message):
    if not ok:
        raise SaveError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def basis(fields):
    return [fields['caf_values'][slot] for slot in BASIS_SLOTS]


def template(cache, appearance, fields):
    outfit = appearance.outfit(fields)
    model = cache.face(outfit)
    meshes = [dict(rm=m['rm'], positions=m['positions'], uvs=m['uv'], indices=m['indices'])
              for m in model['meshes']]
    identity = dict(schema='ffny-face-template-1', basis=basis(fields), meshes=meshes)
    return dict(identity, sha256=digest(identity))


def frozen(reference):
    points = [p for mesh in reference['meshes'] for p in mesh['positions']]
    bottom, top = min(p[1] for p in points), max(p[1] for p in points)
    # Preserve the bottom collar region shared with the original neck.
    cutoff = bottom + (top - bottom) * 0.12
    return {(m['rm'], i) for m in reference['meshes'] for i, p in enumerate(m['positions']) if p[1] <= cutoff}


def validate(value, fields=None, reference=None):
    require(type(value) is dict and set(value) == {'schema', 'template_sha256', 'basis', 'meshes', 'sliders'}, 'Invalid face sculpt fields')
    require(value['schema'] == SCHEMA, 'Unsupported face sculpt version')
    import re
    require(type(value['template_sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['template_sha256']), 'Face sculpt needs a template fingerprint')
    require(type(value['basis']) is list and len(value['basis']) == 6 and all(type(n) is int and 0 <= n <= 8 for n in value['basis']), 'Invalid face sculpt basis')
    if fields is not None:
        require(value['basis'] == basis(fields), 'Face/body presets changed; clear the sculpt or restore its presets')
    require(type(value['sliders']) is dict and set(value['sliders']) <= {k for k, _ in CONTROLS}
            and all(type(n) in (int, float) and math.isfinite(n) and -1 <= n <= 1 for n in value['sliders'].values()), 'Face sliders must be between -1 and 1')
    require(type(value['meshes']) is list and 0 < len(value['meshes']) <= 16, 'Invalid face mesh collection')
    seen, total = set(), 0
    for row in value['meshes']:
        require(type(row) is dict and set(row) == {'rm', 'deltas'} and type(row['rm']) is int
                and 0 <= row['rm'] <= 15 and row['rm'] not in seen, 'Invalid or duplicate face render mesh')
        seen.add(row['rm'])
        require(type(row['deltas']) is list and 0 < len(row['deltas']) <= 1024, 'Invalid face vertex count')
        total += len(row['deltas'])
        for p in row['deltas']:
            require(type(p) is list and len(p) == 3 and all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= MAX_DELTA for v in p), 'Face displacement exceeds the supported finite bounds')
    require(total <= 4096, 'Face sculpt exceeds the vertex budget')
    if reference is not None:
        require(value['template_sha256'] == reference['sha256'] and value['basis'] == reference['basis'], 'Face template does not match these original game assets/presets')
        require([(r['rm'], len(r['deltas'])) for r in value['meshes']] == [(r['rm'], len(r['positions'])) for r in reference['meshes']], 'Face sculpt changes the original render-mesh topology')
        locked = frozen(reference)
        require(all(max(map(abs, p)) <= 1e-6 for row in value['meshes'] for i, p in enumerate(row['deltas']) if (row['rm'], i) in locked), 'Face sculpt moves the protected neck seam')
    return value


def empty(reference):
    return dict(schema=SCHEMA, template_sha256=reference['sha256'], basis=reference['basis'][:],
                meshes=[dict(rm=m['rm'], deltas=[[0., 0., 0.] for _ in m['positions']]) for m in reference['meshes']], sliders={})


def obj(reference, sculpt=None):
    sculpt = validate(sculpt, reference=reference) if sculpt else empty(reference)
    lines = ['# ffny-face-template ' + reference['sha256'], '# Native bind units: X right, Y up, Z forward. Preserve order, UVs and triangles.']
    for mesh, delta in zip(reference['meshes'], sculpt['meshes']):
        for p, d in zip(mesh['positions'], delta['deltas']):
            lines.append('v ' + ' '.join(format(a+b, '.9g') for a, b in zip(p, d)))
    for mesh in reference['meshes']:
        for uv in mesh['uvs']:
            lines.append('vt ' + ' '.join(format(v, '.9g') for v in uv))
    offset = 1
    for mesh in reference['meshes']:
        lines.append('g rm_' + str(mesh['rm']))
        for i in range(0, len(mesh['indices']), 3):
            lines.append('f ' + ' '.join(f'{v+offset}/{v+offset}' for v in mesh['indices'][i:i+3]))
        offset += len(mesh['positions'])
    return ('\n'.join(lines) + '\n').encode()


def import_obj(raw, reference):
    require(type(raw) is bytes and len(raw) <= MAX_OBJ, 'Face OBJ exceeds the 2 MiB limit')
    try:
        text = raw.decode('utf-8-sig')
        points, uvs, triangles = [], [], []
        for line in text.splitlines():
            words = line.split('#', 1)[0].split()
            if not words:
                continue
            kind, args = words[0], words[1:]
            if kind in ('v', 'vt'):
                require(len(args) == (3 if kind == 'v' else 2), 'Use XYZ vertices and two-component UVs')
                p = list(map(float, args))
                require(all(math.isfinite(v) and abs(v) < 1000 for v in p), 'OBJ contains invalid coordinates')
                (points if kind == 'v' else uvs).append(p)
            elif kind == 'f':
                require(len(args) == 3, 'Keep the original triangulation')
                indices = [a.split('/') for a in args]
                require(all(len(a) in (2, 3) and a[0] and a[1] and int(a[0]) > 0 and int(a[0]) == int(a[1]) for a in indices), 'Keep original vertex/UV indexing; disable vertex welding/reordering')
                triangles.extend(int(a[0])-1 for a in indices)
            else:
                require(kind in ('vn', 'g', 'o', 's', 'usemtl', 'mtllib'), 'Unsupported OBJ record: ' + kind)
        expected_uvs = [p for m in reference['meshes'] for p in m['uvs']]
        expected_indices, offset = [], 0
        for m in reference['meshes']:
            expected_indices.extend(i + offset for i in m['indices'])
            offset += len(m['positions'])
        require(len(points) == offset and len(uvs) == offset and triangles == expected_indices, 'OBJ topology/order differs from the exported head template')
        require(all(abs(a-b) <= 1e-6 for p, q in zip(uvs, expected_uvs) for a, b in zip(p, q)), 'OBJ changed the original UVs')
        result, offset = empty(reference), 0
        for m, r in zip(reference['meshes'], result['meshes']):
            r['deltas'] = [[a-b for a, b in zip(p, base)] for p, base in zip(points[offset:offset+len(m['positions'])], m['positions'])]
            offset += len(m['positions'])
        return validate(result, reference=reference)
    except (UnicodeError, ValueError, OverflowError) as exc:
        raise SaveError('Invalid face OBJ: ' + str(exc)) from exc


def sliders(reference, values):
    result = empty(reference)
    result['sliders'] = copy.deepcopy(values)
    validate(result, reference=reference)
    result['sliders'] = {key: values.get(key,0) for key,_ in CONTROLS}
    points = [p for m in reference['meshes'] for p in m['positions']]
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    mid = [(a+b)/2 for a,b in zip(lo,hi)]
    span = [b-a for a,b in zip(lo,hi)]
    locked = frozen(reference)
    def gaussian(x,y,z,cx,cy,cz,sx,sy,sz):
        return math.exp(-((x-cx)/sx)**2-((y-cy)/sy)**2-((z-cz)/sz)**2)
    for mesh, row in zip(reference['meshes'], result['meshes']):
        for i, (px,py,pz) in enumerate(mesh['positions']):
            if (mesh['rm'],i) in locked:
                continue
            x,y,z = (px-mid[0])/span[0], (py-lo[1])/span[1], (pz-lo[2])/span[2]
            nose = gaussian(x,y,z,0,.52,.9,.16,.2,.35)
            eye = gaussian(abs(x),y,z,.25,.76,.7,.18,.12,.3)
            brow = gaussian(abs(x),y,z,.25,.85,.7,.22,.08,.3)
            jaw = gaussian(x,y,z,0,.22,.65,.6,.2,.6)
            ear = gaussian(abs(x),y,z,.47,.63,.25,.1,.25,.35)
            v = lambda key: values.get(key,0)
            dx = px*.12*v('face_width') + px*.18*jaw*v('jaw_width')
            dx += px*.3*nose*v('nose_width') + (1 if x>=0 else -1)*.12*eye*v('eye_spacing')
            dx += (abs(px)-span[0]*.25)*(1 if x>=0 else -1)*.2*eye*v('eye_size') + px*.15*ear*v('ear_size')
            dy = -.15*jaw*v('chin_length') + .12*brow*v('brow_height') + (y-.76)*span[1]*.25*eye*v('eye_size')
            dz = .2*nose*v('nose_projection')
            # Fade every edit continuously toward the protected collar.
            fade = min(1., max(0., (y-.12)/.15))
            row['deltas'][i] = [dx*fade,dy*fade,dz*fade]
    return validate(result, reference=reference)


def apply(model, value):
    result = copy.deepcopy(model)
    rows = {r['rm']: r['deltas'] for r in value['meshes']}
    for mesh in result['meshes']:
        if mesh['rm'] in rows:
            mesh['positions'] = [[a+b for a,b in zip(p,d)] for p,d in zip(mesh['positions'],rows[mesh['rm']])]
    return result
