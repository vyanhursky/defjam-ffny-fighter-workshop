"""Desktop-independent editor session; all mutations are explicit actions."""
import copy
from pathlib import Path

from .appearance import Appearance
from .assets import build_cache, Database
from . import blazin
from .container import SaveError
from .fields import apply_fields, read_fields, STYLE_NAMES, CASH_LIMIT, DEV_LIMIT
from .profiles import discover
from .storage import save_profile, export_profile, duplicate, read_archive, install_files
from . import projects, outfits, ui_art


class Editor:
    def group_label(self, slot):
        if slot == 25:
            return "Earrings (pair)"
        if slot >= 29:
            return "Tattoo - " + ("Head & Neck", "Chest & Stomach", "Back", "Left Arm", "Left Forearm",
                                  "Right Arm", "Right Forearm", "Left Leg", "Right Leg")[slot - 29]
        return self.cache.groups[str(slot)]["label"]

    def __init__(self, workspace, progress=lambda message: None):
        self.workspace = Path(workspace)
        self.progress = progress
        self.data = None
        self.discovery = None
        self.profile = None
        self.edits = {}
        self.history = []
        self.cache = None
        self.appearance = None
        self.blazin = None
        self.blazin_error = "Load original game assets to choose Blazin' moves."
        self.preview_error = None
        self.project = self.project_path = self.project_hash = None
        self.portrait_edit = None
        self.metadata_edit = None
        self.texture_edit = None
        self.outfit_draft = None
        self.active_outfit = outfits.DEFAULT
        self._project_base_document = self._project_base = None

    def base(self):
        if self.project is not None:
            source = self.outfit_draft if self.outfit_draft is not None else self.project
            key = (id(source), self.active_outfit)
            if self._project_base_document != key:
                view = outfits.view(source, self.active_outfit)
                self._project_base = apply_fields(projects.empty_container(), {k: view["fighter"][k] for k in projects.FIGHTER_FIELDS})
                self._project_base_document = key
            return self._project_base
        if self.profile is None:
            raise SaveError("Choose a profile or open a fighter project first")
        return self.profile.container

    def project_source(self):
        return self.outfit_draft if self.outfit_draft is not None else self.project

    def active_view(self):
        return outfits.view(self.project_source(), self.active_outfit) if self.project is not None else None

    def remember(self):
        self.history.append(copy.deepcopy(dict(edits=self.edits, active_outfit=self.active_outfit,
            outfit_draft=self.outfit_draft, portrait_edit=self.portrait_edit,
            texture_edit=self.texture_edit, metadata_edit=self.metadata_edit)))
        self.history = self.history[-100:]

    def flush_outfit(self):
        document = self.project_document(validate=False)
        self.outfit_draft = None if document == self.project else document
        self.edits = {}
        self.portrait_edit = self.texture_edit = self.metadata_edit = None

    def project_document(self, validate=True):
        source = self.project_source()
        document = outfits.view(source, self.active_outfit)
        if self.metadata_edit is not None:
            document.update(copy.deepcopy(self.metadata_edit))
        fields = read_fields(self.current().payload)
        document["fighter"].update({k: copy.deepcopy(fields[k]) for k in projects.FIGHTER_FIELDS})
        if "finishers" in self.edits:
            if self.edits["finishers"] is None:
                document["fighter"].pop("finishers", None)
            else:
                document["schema"] = projects.SCHEMA2
                document["fighter"]["finishers"] = self.edits["finishers"][:]
        if self.portrait_edit is not None:
            document["portrait"] = self.portrait_edit
        if self.texture_edit is not None:
            document.update(schema=projects.SCHEMA2, textures=copy.deepcopy(self.texture_edit))
        document = outfits.replace_view(source, self.active_outfit, document)
        return projects.validate(document) if validate else document

    def create_project(self, path):
        fields = read_fields(self.current().payload)
        document = (projects.from_profile(self.current().payload, self.profile.name, self.blazin.database if self.blazin else self.cache.db if self.cache else None)
                    if self.profile else projects.from_fields(fields, self.project["metadata"]["name"]))
        if self.project is not None:
            source = self.project_document()
            identity = document["identity"]
            document = copy.deepcopy(source)
            document["identity"] = identity
        digest = projects.write(path, document)
        self.project, self.project_path, self.project_hash = document, Path(path), digest
        self.profile = None
        self.portrait_edit = self.metadata_edit = None
        self.texture_edit = None
        self.outfit_draft = None
        self.edits, self.history = {}, []
        return self.snapshot()

    def open_project(self, path):
        document, digest = projects.read(path)
        self.project, self.project_path, self.project_hash = document, Path(path), digest
        self.active_outfit = outfits.DEFAULT
        self.outfit_draft = None
        self.profile = None
        self.portrait_edit = self.metadata_edit = None
        self.texture_edit = None
        self.edits, self.history = {}, []
        return self.snapshot()

    def open_data(self, data):
        data = Path(data).expanduser().resolve()
        result = discover(data)
        self.data, self.discovery = data, result
        self.cache = self.appearance = None
        self.blazin = None
        self.blazin_error = "Load original game assets to choose Blazin' moves."
        self.preview_error = None
        if (data / "extracted").is_dir():
            try:
                self.cache = build_cache(data / "extracted", self.workspace, self.progress)
                self.appearance = Appearance(self.cache)
            except (OSError, ValueError, KeyError) as exc:
                self.preview_error = "CAF cache could not be loaded: " + str(exc)
        else:
            self.preview_error = "Choose the Recomp data directory containing extracted game assets for the 3D preview."
        if (data / "extracted").is_dir():
            try:
                self.blazin = blazin.Catalog(self.cache.db if self.cache else Database(data / "extracted"))
                self.blazin_error = None
            except (OSError, ValueError, KeyError, SaveError) as exc:
                self.blazin_error = "Blazin' catalog could not be loaded: " + str(exc)
        candidates = [p for p in result.profiles if read_fields(p.container.payload)["has_fighter"]]
        chosen = max(candidates or result.profiles, key=lambda p: p.path.stat().st_mtime, default=None)
        if self.project is not None:
            return self.snapshot()
        if chosen:
            self.select_profile(chosen.name)
        else:
            self.profile = None
            self.edits, self.history = {}, []
        return self.snapshot()

    def select_profile(self, name):
        self.discovery = discover(self.data)
        self.profile = next((p for p in self.discovery.profiles if p.name == name), None)
        if self.profile is None:
            raise SaveError("Profile is unavailable; refresh the data directory")
        self.project = self.project_path = self.project_hash = None
        self.outfit_draft = None
        self.active_outfit = outfits.DEFAULT
        self.portrait_edit = self.metadata_edit = None
        self.texture_edit = None
        self.edits, self.history = {}, []
        return self.snapshot()

    def current(self):
        return apply_fields(self.base(), {k: v for k, v in self.edits.items() if k != "finishers"})

    def blazin_keys(self, edits=None):
        edits = self.edits if edits is None else edits
        if self.project is not None:
            return blazin.project_keys(edits.get("finishers", self.project_source()["fighter"].get("finishers")))
        if self.blazin and self.profile:
            return self.blazin.profile_keys(apply_fields(self.base(), edits).payload)
        return [None] * 4

    def stage(self, changes):
        if self.project is not None and set(changes) & {"cash", "development"}:
            raise SaveError("Fighter projects have no Story currency")
        if not read_fields(self.current().payload)["has_fighter"]:
            raise SaveError("This profile has no Story fighter. Create one in the game first")
        if "blazin_values" in changes:
            if self.project is not None or not self.blazin:
                raise SaveError("Choose Blazin' moves through the loaded catalog")
            self.blazin.validate_values(changes["blazin_values"])
        if "finishers" in changes:
            if self.project is None or not self.blazin:
                raise SaveError("Choose project Blazin' moves through the loaded catalog")
            if changes["finishers"] is not None:
                self.blazin.select(blazin.project_keys(changes["finishers"]))
        combined = copy.deepcopy(self.edits)
        if "stats" in changes:
            combined["stats"] = dict(combined.get("stats", {}), **changes["stats"])
        combined.update({k: v for k, v in changes.items() if k != "stats"})
        candidate = apply_fields(self.base(), {k: v for k, v in combined.items() if k != "finishers"})
        if candidate.payload == self.current().payload and self.blazin_keys(combined) == self.blazin_keys():
            return self.snapshot()
        self.remember()
        self.edits = combined
        return self.snapshot()

    def stage_appearance(self, changes):
        if self.appearance is None:
            raise SaveError("Load the original game assets before changing appearance")
        fields = read_fields(self.current().payload)
        edited = self.appearance.change(fields, changes)
        from .face_geometry import basis
        if (self.active_view() or {}).get('face_sculpt') and basis(fields) != basis(dict(fields, **edited)):
            raise SaveError('Clear the face sculpt before changing its body or facial geometry presets')
        # Validate a complete source outfit before any bytes can be staged.
        try:
            self.cache.compose(self.appearance.outfit(dict(fields, **edited)))
        except KeyError as exc:
            raise SaveError("This item combination cannot be previewed yet; the existing appearance was preserved") from exc
        return self.stage(edited)

    def changes(self):
        if self.profile is None and self.project is None:
            return []
        if self.project is not None and (self.outfit_draft is not None or self.project["schema"] in (projects.SCHEMA3,projects.SCHEMA4,projects.SCHEMA5)):
            return self.outfit_changes()
        before, after = read_fields(self.base().payload), read_fields(self.current().payload)
        result = []
        if self.metadata_edit is not None:
            result.append("Project details changed")
        if self.portrait_edit is not None:
            result.append("Project portrait changed")
        if self.texture_edit is not None:
            result.append("Project texture atlases changed")
        for key, label in (("cash", "Cash"), ("development", "Development points")):
            if before[key] != after[key]:
                result.append(f"{label}: {before[key]:,} → {after[key]:,}")
        for key in before["stats"]:
            if before["stats"][key] != after["stats"][key]:
                result.append(f"{key.capitalize()}: {before['stats'][key]} → {after['stats'][key]}")
        if before["styles"] != after["styles"]:
            result.append("Fighting styles: " + ", ".join(STYLE_NAMES[i] for i in after["styles"]))
        before_moves = self.blazin_keys({})
        for slot, (old, new) in enumerate(zip(before_moves, self.blazin_keys())):
            if old != new:
                result.append(f"Blazin' slot {slot + 1}: " + (self.blazin.label(new) if self.blazin else str(new)))
        for slot, (old, new, oc, nc) in enumerate(zip(before["caf_values"], after["caf_values"], before["caf_colors"], after["caf_colors"])):
            if old != new or oc != nc:
                label = {0: "Body build", 1: "Skin tone"}.get(slot)
                if not label and self.cache:
                    label = self.group_label(slot)
                result.append((label or "Appearance") + " changed")
        return result

    def outfit_changes(self):
        before, after = self.project, self.project_document(validate=False)
        result = []
        if any(before[k] != after[k] for k in ("identity", "metadata")):
            result.append("Project details changed")
        for key, label in (("stats", "Training stats"), ("styles", "Fighting styles"), ("finishers", "Blazin' assignments")):
            if before["fighter"].get(key) != after["fighter"].get(key):
                result.append(label + " changed (all outfits)")
        old, new = ({row["id"]: row["name"] for row in outfits.entries(doc)} for doc in (before, after))
        for identity in old.keys() - new.keys():
            result.append("Outfit removed: " + old[identity])
        for identity, name in new.items():
            if identity not in old:
                result.append("Outfit added: " + name)
                continue
            if old[identity] != name:
                result.append("Outfit renamed: " + name)
            left, right = outfits.view(before, identity), outfits.view(after, identity)
            if any(left["fighter"][key] != right["fighter"][key] for key in outfits.APPEARANCE):
                result.append(name + ": appearance changed")
            for key, label in (("textures", "texture atlases"), ("portrait", "portrait"), ('ui_art','UI artwork'), ('face_sculpt','face sculpt')):
                if left.get(key) != right.get(key):
                    result.append(name + ": " + label + " changed")
        if not result and before != after:
            result.append("Project outfit collection changed")
        return result

    def snapshot(self):
        result = dict(data=str(self.data) if self.data else None, profiles=[], selected=None,
                      fields=None, changes=[], dirty=False, undo=False,
                      style_names=STYLE_NAMES, limits=dict(cash=CASH_LIMIT, development=DEV_LIMIT),
                      preview_error=self.preview_error, preview_available=self.appearance is not None,
                      groups=[], skins=[], issues=self.discovery.issues if self.discovery else [])
        project_view = copy.deepcopy(self.project_source())
        if project_view is not None:
            project_view.pop("outfits", None)
            project_view.pop('ui_art',None)
            project_view.pop('face_sculpt',None)
        if project_view is not None and self.metadata_edit is not None:
            project_view.update(copy.deepcopy(self.metadata_edit))
        active = self.active_view()
        from .face_geometry import CONTROLS
        sculpt = (active or {}).get('face_sculpt')
        result['face_sculpt'] = dict(available=self.project is not None and self.appearance is not None,
            imported=bool(sculpt and not sculpt['sliders']), present=bool(sculpt),
            sliders=sculpt['sliders'] if sculpt else {}, controls=[dict(id=k,label=v) for k,v in CONTROLS])
        result.update(project=project_view, project_path=str(self.project_path) if self.project_path else None,
                      portrait_available=self.portrait_edit is not None or bool(active and "portrait" in active),
                      outfits=outfits.entries(self.project_source()) if self.project else [], active_outfit=self.active_outfit)
        result['ui_art']=ui_art.status(self.project_document(validate=False),self.active_outfit) if self.project else None
        textures = self.texture_edit if self.texture_edit is not None else (active or {}).get("textures", {})
        result["atlas_slots"] = sorted(textures.get("atlases", {}))
        result["blazin"] = dict(options=self.blazin.options if self.blazin else [], selected=self.blazin_keys(),
                                error=self.blazin_error)
        if self.discovery:
            result["profiles"] = [dict(name=p.name, has_fighter=read_fields(p.container.payload)["has_fighter"],
                                       legacy=p.directory_kind == "legacy") for p in self.discovery.profiles]
        if self.profile or self.project:
            result.update(selected=self.project["metadata"]["name"] if self.project else self.profile.name,
                          fields=read_fields(self.current().payload),
                          changes=self.changes(), dirty=(self.project_document(validate=False) != self.project if self.project else
                              self.current().encode() != self.base().encode()),
                          undo=bool(self.history))
            if self.appearance:
                fields = result["fields"]
                result["appearance_selected"] = self.appearance.selected(fields)
                from .faces import selected
                result['face_presets']=selected(fields,self.appearance.face_options)
                result["groups"] = [dict(id=str(slot), label=self.group_label(slot),
                                          section=self.cache.groups[str(slot)]["section"], count=len(self.appearance.options[str(slot)]))
                                    for slot in range(12, 38) if slot not in (17, 26)]
                build = "abcdef"[fields["caf_values"][0]] if fields["caf_values"][0] in range(6) else "c"
                result["skins"] = [int(k[2:]) for k in self.cache.catalog["resources"][f"v2cp_a_{build}"]["images"] if k.startswith("pl")]
        return result

    def preview(self, changes=None, hide_clothes=False):
        if self.appearance is None:
            raise SaveError(self.preview_error or "No preview assets")
        fields = read_fields(self.current().payload)
        if not fields["has_fighter"]:
            raise SaveError("This profile has no Story fighter yet")
        if changes:
            fields.update(self.appearance.change(fields, changes))
        # Preview overlays never pass through stage/current/save. Use the game's
        # empty clothing meshes (including underwear), retaining skin/tattoos.
        if hide_clothes:
            for slot in (*range(12, 20), *range(22, 27), 28):
                fields["caf_values"][slot] = 0xffffffff
                fields["caf_colors"][slot] = 0
        result = self.cache.compose(self.appearance.outfit(fields))
        sculpt = (self.active_view() or {}).get('face_sculpt')
        if sculpt:
            from . import face_geometry
            reference = face_geometry.template(self.cache, self.appearance, fields)
            face_geometry.validate(sculpt, fields, reference)
            head = face_geometry.apply(dict(meshes=[m for m in result['meshes'] if m['slot']=='2']), sculpt)
            heads = {m['rm']: m for m in head['meshes']}
            result['meshes'] = [heads[m['rm']] if m['slot']=='2' else m for m in result['meshes']]
            result['notices'].append('Experimental template sculpt. Original rig, UVs and normals retained; extreme edits may affect shading, eyelids, hair and accessories.')
        textures = self.texture_edit if self.texture_edit is not None else (self.active_view() or {}).get("textures")
        if textures and textures["atlases"]:
            # Try-on/No clothes uses the original temporary outfit, never the
            # final flattened artwork for a different appearance.
            if textures["appearance_sha256"] == projects.appearance_hash(fields):
                import base64, io
                from PIL import Image
                from .assets import image_uri
                for atlas in "abcd":
                    if atlas not in textures["atlases"]:
                        continue
                    native = Image.open(io.BytesIO(base64.b64decode(result["textures"][atlas].split(",", 1)[1]))).convert("RGBA")
                    imported = Image.open(io.BytesIO(projects.atlas_bytes(textures["atlases"][atlas]))).convert("RGBA")
                    imported.putalpha(native.getchannel("A"))
                    result["textures"][atlas] = image_uri(imported)
                result["notices"].append("Imported RGB atlases; original material alpha retained. Injury variants apply in-game; this preview shows the normal face.")
            else:
                result["notices"].append("Imported atlases belong to the saved outfit; this temporary appearance uses original textures.")
        result["preview_only"] = dict(changes=changes or {}, hide_clothes=hide_clothes)
        return result

    def request(self, action, args):
        if action in ('face_export', 'face_import', 'face_sliders', 'face_clear'):
            from . import face_geometry
            if self.project is None:
                raise SaveError('Create a standalone fighter project for sculpting. Story saves store original presets only.')
            if self.appearance is None:
                raise SaveError('Load original game assets before sculpting a face')
            document = self.project_document(validate=action!='face_clear')
            view = outfits.view(document, self.active_outfit)
            reference = face_geometry.template(self.cache, self.appearance, view['fighter'])
            if action == 'face_export':
                path = Path(args['path'])
                if path.exists():
                    raise SaveError('Choose a new template filename; existing files are preserved')
                from .storage import atomic_bytes
                atomic_bytes(path, face_geometry.obj(reference, view.get('face_sculpt')))
                return dict(message='Exported sculptable head OBJ. Preserve vertex order, triangulation and UVs.')
            if action == 'face_clear':
                view.pop('face_sculpt', None)
            elif action == 'face_sliders':
                if view.get('face_sculpt') and not view['face_sculpt']['sliders']:
                    raise SaveError('Clear the imported sculpt before using sliders; export it first to preserve your work')
                view['face_sculpt'] = face_geometry.sliders(reference, args['values'])
                view['schema'] = projects.SCHEMA5
            else:
                with Path(args['path']).open('rb') as stream:
                    raw = stream.read(face_geometry.MAX_OBJ+1)
                view['face_sculpt'] = face_geometry.import_obj(raw, reference)
                view['schema'] = projects.SCHEMA5
            candidate = projects.validate(outfits.replace_view(document, self.active_outfit, view))
            self.remember()
            self.outfit_draft, self.edits = candidate, {}
            self.portrait_edit = self.texture_edit = self.metadata_edit = None
            return dict(snapshot=self.snapshot(), message='Face sculpt staged; Save project preserves it')
        if action=='ui_preview':
            if self.project is None:return {'png':None}
            effective=ui_art.resolved(self.project_document(validate=False),self.active_outfit)
            value=effective['images'].get(args['role'])
            return {'png':'data:image/png;base64,'+value if value else None,'origin':effective['origins'].get(args['role'],{'source':'Retail UI donor'})}
        if action in ('ui_import','ui_clear','ui_clear_all','ui_settings','ui_retail'):
            if self.project is None:raise SaveError('Create or open a fighter project first')
            candidate=self.project_document(validate=False)
            if action=='ui_retail':
                import base64,tempfile
                from .fighter_mod import contract
                if self.data is None or not (Path(self.data)/'extracted').is_dir():
                    raise SaveError('Load original game assets before importing retail UI artwork')
                effective=ui_art.resolved(candidate,self.active_outfit)
                self.workspace.mkdir(parents=True,exist_ok=True)
                with tempfile.TemporaryDirectory(prefix='ui-reference-',dir=self.workspace) as temporary:
                    output=Path(temporary)/'reference'
                    report=contract(Path(args['runtime']),['export-ui-reference','--game',str((Path(self.data)/'extracted').resolve()),
                        '--donor',effective['donor'],'--portrait-out',str(output)],temporary,self.workspace)
                    pack={'donor':effective['donor'],'hd_scale':effective['hd_scale'],'images':{}}
                    for role,spec in report['source']['images'].items():
                        # Source paths are generated by the reviewed runtime, but
                        # still constrain reads to this private temporary folder.
                        path=(output/spec['path']).resolve()
                        if not path.is_relative_to(output.resolve()):raise SaveError('UI reference file leaves its output folder')
                        raw=path.read_bytes()
                        if len(raw)>4*1024**2:raise SaveError('UI reference PNG is too large')
                        import hashlib
                        if hashlib.sha256(raw).hexdigest()!=spec['sha256']:raise SaveError('UI reference hash changed')
                        pack['images'][role]=base64.b64encode(raw).decode('ascii')
                    ui_art.validate(pack)
                    candidate=ui_art.upgrade(candidate);ui_art.node(candidate,self.active_outfit)['ui_art']=pack
            elif action=='ui_settings':
                candidate=ui_art.edit(candidate,self.active_outfit,settings={'donor':args['donor'],'hd_scale':args['hd_scale']})
            else:
                raw=args.get('png')
                if raw and raw.startswith('data:image/png;base64,'):raw=raw.split(',',1)[1]
                candidate=ui_art.edit(candidate,self.active_outfit,role=args.get('role'),png=raw,
                                      clear_all=action=='ui_clear_all')
            ui_art.check_budget(candidate)
            self.remember();self.flush_outfit();self.outfit_draft=candidate
            return self.snapshot()
        if action in ("outfit_select", "outfit_add", "outfit_rename", "outfit_remove"):
            if self.project is None:
                raise SaveError("Create or open a fighter project before editing outfits")
            if action == "outfit_select":
                if args["id"] not in {row["id"] for row in outfits.entries(self.project_source())}:
                    raise SaveError("This outfit is unavailable")
                self.flush_outfit()
                self.active_outfit = args["id"]
            else:
                candidate = self.project_document(validate=False)
                if action == "outfit_add":
                    candidate, selected = outfits.add(candidate, self.active_outfit)
                elif action == "outfit_rename":
                    candidate = outfits.rename(candidate, self.active_outfit, args["name"])
                    selected = self.active_outfit
                else:
                    candidate = outfits.remove(candidate, self.active_outfit)
                    selected = outfits.DEFAULT
                self.remember()
                self.flush_outfit()
                self.outfit_draft, self.active_outfit = candidate, selected
            return self.snapshot()
        if action == "blazin":
            if not self.blazin:
                raise SaveError(self.blazin_error)
            rows = self.blazin.select(args["moves"])
            return self.stage({"finishers": [row["record"] for row in rows]} if self.project else
                              {"blazin_values": [row["value"] for row in rows]})
        if action == "blazin_inherit":
            return self.stage({"finishers": None})
        if action in ("project_atlas", "project_atlas_clear"):
            if self.project is None:
                raise SaveError("Create or open a fighter project first")
            if action == "project_atlas_clear":
                fields = read_fields(self.current().payload)
                textures = {"appearance_sha256": projects.appearance_hash(fields), "atlases": {}}
            else:
                raw = args["png"]
                if raw.startswith("data:image/png;base64,"):
                    raw = raw.split(",", 1)[1]
                import base64
                document = projects.with_atlas(outfits.view(self.project_document(), self.active_outfit), args["slot"], projects.atlas_bytes(raw))
                textures = document["textures"]
            self.remember()
            self.texture_edit = textures
            return self.snapshot()
        if action == "project_portrait":
            if self.project is None:
                raise SaveError("Create or open a fighter project first")
            raw = args["png"]
            if raw.startswith("data:image/png;base64,"):
                raw = raw.split(",", 1)[1]
            projects.portrait_bytes(raw)
            self.remember()
            self.portrait_edit = raw
            return self.snapshot()
        if action == "new_project":
            return self.create_project(args["path"])
        if action == "open_project":
            return self.open_project(args["path"])
        if action == "project_metadata_draft":
            if self.project is None:
                raise SaveError("Create or open a fighter project first")
            # Preserve incomplete form values; validate only when saving/exporting.
            if set(args) != {"metadata", "identity"} or not all(isinstance(args[k], dict) for k in args):
                raise SaveError("Invalid project details")
            self.metadata_edit = copy.deepcopy(args)
            if all(self.project.get(k) == v for k, v in args.items()):
                self.metadata_edit = None
            return self.snapshot()
        if action == "project_metadata":
            if self.project is None:
                raise SaveError("Create or open a fighter project first")
            document = self.project_document()
            document["metadata"].update(args["metadata"])
            if "identity" in args:
                document["identity"] = args["identity"]
            projects.validate(document)
            self.project_hash = projects.write(self.project_path, document, self.project_hash)
            self.project, self.edits, self.history = document, {}, []
            self.outfit_draft = None
            self.portrait_edit = self.metadata_edit = None
            self.texture_edit = None
            return dict(snapshot=self.snapshot(), message="Saved fighter project and pack details")
        if action == "export_mod":
            from .fighter_mod import export_mod
            if self.project is None:
                raise SaveError("Create or open a fighter project before exporting a mod")
            report = export_mod(self.project_document(), args["path"], args["runtime"], self.data,
                                  self.workspace / "fighter-exports", progress=self.progress, asset_cache=self.cache)
            return dict(message="Validated Custom Fighter Mod exported to " + args["path"], report=report)
        if action == "open_data":
            return self.open_data(args["path"])
        if action == "snapshot":
            return self.snapshot()
        if action == "select_profile":
            return self.select_profile(args["name"])
        if action == "stage":
            return self.stage(args["edits"])
        if action == "appearance":
            return self.stage_appearance(args["changes"])
        if action == "options":
            if self.appearance is None or args["slot"] not in self.appearance.options:
                raise SaveError("No appearance choices for that category")
            return [{k: v for k, v in row.items() if k not in {"selection", "value", "color"}}
                    for row in self.appearance.options[args["slot"]]]
        if action == "preview":
            return self.preview(args.get("changes"), bool(args.get("hide_clothes", False)))
        if action == "undo":
            if self.history:
                for key, value in self.history.pop().items():
                    setattr(self, key, value)
            return self.snapshot()
        if action == "reset":
            self.edits, self.history = {}, []
            self.portrait_edit = self.metadata_edit = None
            self.texture_edit = None
            self.outfit_draft = None
            if self.project and self.active_outfit not in {row["id"] for row in outfits.entries(self.project)}:
                self.active_outfit = outfits.DEFAULT
            return self.snapshot()
        if action == "save":
            if self.project is not None:
                document = self.project_document()
                self.project_hash = projects.write(self.project_path, document, self.project_hash)
                self.project, self.edits, self.history = document, {}, []
                self.outfit_draft = None
                self.portrait_edit = self.metadata_edit = None
                self.texture_edit = None
                return dict(snapshot=self.snapshot(), message="Saved fighter project")
            backup = save_profile(self.profile, self.current(), self.workspace / "backups")
            return dict(snapshot=self.select_profile(self.profile.name), message="Saved profile. Backup: " + str(backup))
        if action == "export":
            if self.project is not None:
                self.project_hash = projects.write(args["path"], self.project_document())
                self.project_path = Path(args["path"])
                self.project, self.edits, self.history = self.project_document(), {}, []
                self.outfit_draft = None
                self.portrait_edit = self.metadata_edit = None
                self.texture_edit = None
                return dict(snapshot=self.snapshot(), message="Saved project copy")
            export_profile(self.profile, self.current(), Path(args["path"]))
            return dict(message="Exported complete profile to " + args["path"])
        if action == "duplicate":
            if self.project is not None:
                raise SaveError("Use Save project as to copy a standalone fighter")
            path = duplicate(self.profile, self.current(), args["name"])
            return dict(snapshot=self.select_profile(args["name"]), message="Created profile " + args["name"])
        if action == "import":
            name, _, files = read_archive(Path(args["path"]))
            install_files(self.discovery.title_root, name, files)
            return dict(snapshot=self.select_profile(name), message="Imported complete profile " + name)
        raise SaveError("Unsupported editor action")
