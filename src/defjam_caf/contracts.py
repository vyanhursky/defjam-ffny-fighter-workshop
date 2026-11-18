"""Internal document contracts, after admission by the existing validators.

These are static types, not an alternative schema or a JSON deserializer.
Opaque runtime catalog/resource rows remain JSON until their own validators run.
"""

from typing import Literal, NotRequired, Required, TypedDict

JSON = None | bool | int | float | str | list["JSON"] | dict[str, "JSON"]


class Identity(TypedDict):
    pack: str
    fighter: str


class Metadata(TypedDict):
    name: str
    author: str
    version: str
    description: str
    license: str
    donor: str


class TrainingStats(TypedDict):
    upper: int
    lower: int
    speed: int
    toughness: int
    health: int


class AppearanceFields(TypedDict):
    caf_values: list[int]
    caf_colors: list[int]


class FighterFields(AppearanceFields):
    stats: TrainingStats
    styles: list[int]
    finishers: NotRequired[list[str]]
    retail_moveset: NotRequired[str]


class ProfileFields(FighterFields):
    cash: int
    development: int
    combined_style: int
    blazin_values: list[int]
    has_fighter: bool


class FighterSource(FighterFields, total=False):
    has_fighter: bool
    combined_style: int


class Textures(TypedDict):
    appearance_sha256: str
    atlases: dict[str, str]


class UIArt(TypedDict):
    images: dict[str, str]
    donor: NotRequired[str]
    hd_scale: NotRequired[int]


class FaceMesh(TypedDict):
    rm: int
    deltas: list[list[float]]


class FaceSculpt(TypedDict):
    schema: str
    template_sha256: str
    basis: list[int]
    meshes: list[FaceMesh]
    sliders: dict[str, float]
    neck_normals: NotRequired[list[dict[str, JSON]]]


class AppearanceAssets(TypedDict, total=False):
    textures: Textures
    portrait: str
    ui_art: UIArt
    face_sculpt: FaceSculpt


class Outfit(AppearanceAssets, AppearanceFields):
    id: str
    name: str


class Voice(TypedDict):
    preset: str
    banks: dict[str, int]
    clips: dict[str, str]


class AI(TypedDict):
    preset: str
    tendencies: dict[str, list[dict[str, int]]]


class Performance(TypedDict, total=False):
    voice: Voice
    intro: str
    victory: str
    ai: AI


class FighterProject(AppearanceAssets):
    schema: str
    identity: Identity
    metadata: Metadata
    fighter: FighterFields
    outfit_name: NotRequired[str]
    outfits: NotRequired[list[Outfit]]
    performance: NotRequired[Performance]


class OutfitEntry(TypedDict):
    id: str
    name: str


class RetailDefinition(TypedDict):
    inherits: str
    components: dict[str, JSON]


class RetailProject(TypedDict):
    schema: str
    identity: Identity
    metadata: Metadata
    definition: RetailDefinition
    resources: list[dict[str, JSON]]
    assets: dict[str, dict[str, str]]
    textures: dict[str, str]
    ui_art: UIArt
    deployment: NotRequired[dict[str, str]]
    performance: NotRequired[Performance]
    outfit_name: NotRequired[str]
    outfits: NotRequired[list[dict[str, JSON]]]


class ProjectSummary(TypedDict):
    schema: str
    identity: Identity
    metadata: Metadata
    fighter: FighterFields
    outfit_name: NotRequired[str]


class ProfileEntry(TypedDict):
    name: str
    has_fighter: bool
    legacy: bool


class Snapshot(TypedDict, total=False):
    data: Required[str | None]
    profiles: Required[list[ProfileEntry]]
    selected: Required[str | None]
    fields: Required[ProfileFields | None]
    changes: Required[list[str]]
    dirty: Required[bool]
    undo: Required[bool]
    version: str
    setup: dict[str, JSON]
    limits: dict[str, int]
    style_names: tuple[str, ...]
    preview_error: str | None
    preview_detail: str | None
    preview_available: bool
    groups: list[dict[str, JSON]]
    skins: list[int]
    issues: list[str]
    retail_moveset_save: str | None
    backups: list[dict[str, JSON]]
    project: ProjectSummary | None
    project_path: str | None
    project_origin: str | None
    portrait_available: bool
    outfits: list[OutfitEntry]
    active_outfit: str
    face_sculpt: dict[str, JSON]
    ui_art: dict[str, JSON] | None
    atlas_slots: list[str]
    blazin: dict[str, JSON]
    retail_movesets: dict[str, JSON]
    performance: dict[str, JSON]
    appearance_selected: dict[str, JSON]
    face_presets: list[dict[str, JSON]]
    appearance_key: str


AppearanceKey = Literal["caf_values", "caf_colors"]
AssetKey = Literal["textures", "portrait", "ui_art", "face_sculpt"]
