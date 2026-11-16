import { createTabs } from "./tabs.mjs";
import { mountPerformancePanels } from "./performance-panels.mjs";
import { performanceEditor } from "./performance.mjs";
import { createExportWorkflow, mountExportDialog } from "./project-workflow.mjs";
import { unpackPreview, geometryFor } from "./geometry.mjs";
import { createStage, disposeModel, frameStage } from "./three-stage.mjs";
import { createBridge } from "./bridge.mjs";
import * as THREE from "three";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { gameSetup } from "./setup.mjs";
import { workshopVersion } from "./version.mjs";
import { attachDetails } from "./errors.mjs";
const $ = (id) => document.getElementById(id);
mountPerformancePanels($("performance-panels"), { retail: true });
mountExportDialog();
const client = createBridge({
  onBusy(count, label) {
    $("busy").hidden = count <= 0;
    if (label) $("busy-label").textContent = label;
  },
});
const pending = client.pending;
let state,
  shapeRows = [],
  epoch = 0,
  detailDraft = null,
  draftTimer,
  renderedPack,
  renderedRuntime,
  renderedOutfit;
let sceneData = null;
// Home chooses the workflow: retail-new (a new fighter from a retail fighter) or retail-edit (change a retail fighter).
const params = new URLSearchParams(location.hash.slice(1)),
  workflow = params.get("mode") === "retail-edit" ? "retail-edit" : "retail-new",
  startKind = params.get("start") || "",
  startPath = params.get("path") || "";
document.body.dataset.mode = workflow;
function applyWorkflow() {
  const edit = workflow === "retail-edit",
    purpose = $("deployment-mode");
  $("mode-title").textContent = edit ? "RETAIL FIGHTER EDITOR" : "FIGHTER FROM A RETAIL FIGHTER";
  document.querySelector(".retail-left .eyebrow").textContent = edit
    ? "CHANGE A RETAIL FIGHTER"
    : "START A NEW FIGHTER";
  $("base-donor").closest("label").firstChild.textContent = edit ? "Fighter to change" : "Start from this fighter";
  purpose.closest("label").firstChild.textContent = "What do you want to do?";
  for (const option of purpose.options) {
    option.hidden = option.disabled = edit ? option.value === "add" : option.value !== "add";
    option.textContent = {
      add: "New standalone fighter",
      override: "Replace how it looks",
      outfit: "Add an extra outfit",
    }[option.value];
  }
  purpose.closest("label").hidden = !edit;
  $("new").textContent = edit ? "Start changing this fighter" : "Start new fighter";
  for (const node of [$("deployment-target").closest("label"), $("apply-deployment"), $("deployment-status")])
    node.hidden = !edit || !state?.document;
}
async function startFlow() {
  if (state?.document) await act("retail_close");
  if (startKind === "open") {
    if (startPath) await act("retail_open", { path: startPath }, "Opening fighter project…");
    else await act("choose_retail_open");
  }
}
const call = (action, args = {}, label = null) => client.call(action, args, label);

function status(text, error = false) {
  client.record(text, error);
  $("status-message").textContent = text;
  $("toast").textContent = text;
  $("toast").classList.toggle("error", error);
  $("toast").hidden = false;
  clearTimeout(status.timer);
  status.timer = setTimeout(() => ($("toast").hidden = true), 10000);
}
async function act(action, args = {}, label = "Updating fighter…") {
  return client.enqueue(async () => {
    try {
      if (detailDraft) {
        await call("retail_draft", detailDraft);
        detailDraft = null;
      }
      const result = await call(action, args, label);
      if (result?.retail) render(result);
      if (result?.snapshot?.retail) render(result.snapshot);
      if (result?.message) status(result.message);
      return result;
    } catch (e) {
      if (/Game setup/.test(e.message)) setup.open(state?.setup);
      status(e.message, true);
      attachDetails($("toast"), e.detail);
      if (e.detail) clearTimeout(status.timer);
      return null;
    }
  });
}
// Game setup is shared with the fighter editor; after it changes, the studio reloads its own catalog.
const setup = gameSetup({
  call,
  act: async (action, args, label) => {
    const result = await act(action, args, label);
    if (["setup_use", "choose_data", "cache_clear"].includes(action)) await act("retail_snapshot");
    return result;
  },
});
$("setup-open").onclick = () => setup.open(state?.setup);
const discard = () => !state?.dirty || confirm("Discard unsaved retail fighter changes?");
function options(id, rows, value) {
  const previous = value ?? $(id).value;
  $(id).replaceChildren(...rows.map((r) => new Option(r.name, r.id)));
  if (rows.some((r) => r.id === previous)) $(id).value = previous;
}
function render(s) {
  state = s;
  window.__retailState = s;
  const d = s.document,
    selected = d?.definition.inherits;
  const refreshRuntime = (renderedRuntime !== s.runtime || renderedOutfit !== s.active_outfit) && Boolean(sceneData);
  renderedRuntime = s.runtime;
  renderedOutfit = s.active_outfit;
  document.body.dataset.hasProject = String(Boolean(d));
  if (renderedPack !== d?.identity.pack) {
    renderedPack = d?.identity.pack;
    $("retail-start").open = !d;
    clearPreview();
  }
  $("empty-body").disabled = $("empty-preview").disabled = !d;
  {
    const chip = setup.chip(s.setup);
    $("setup-open").textContent = chip.text;
    $("setup-open").className = "chip " + chip.state;
    setup.offer(s.setup);
  }
  $("workshop-version").textContent = workshopVersion(s.setup.version);
  $("connection").textContent = s.data || "No game data chosen yet";
  $("saved").textContent = s.dirty ? "● Unsaved changes" : d ? "● Saved project" : "No project";
  for (const id of ["base-donor", "body-donor", "combat-donor", "ui-donor", "deployment-target"])
    options(
      id,
      s.donors,
      id === "combat-donor"
        ? selected
        : id === "ui-donor"
          ? d?.ui_art.donor
          : id === "deployment-target"
            ? d?.deployment?.target || selected
            : null,
    );
  $("new").disabled = !s.donors.length;
  if (d && !$("body-donor").value) $("body-donor").value = d.metadata.donor;
  donorSummary();
  $("import").disabled = !s.runtime;
  $("fighter-name").textContent = d?.metadata.name || "YOUR FIGHTER";
  $("project-path").textContent = s.path || "Save a portable .ffnyfighter project.";
  $("retail-project-name").textContent = s.path ? s.path.split(/[\\/]/).pop() : d?.metadata.name || "No project open";
  $("retail-changes").textContent = s.dirty ? "Pending project changes" : "No pending changes";
  for (const id of ["name", "author", "version", "description", "license"]) {
    $(id).value = d?.metadata[id] || "";
    $(id).disabled = !d;
  }
  for (const id of ["pack", "fighter"]) {
    $(id).value = d?.identity[id] || "";
    $(id).disabled = !d;
  }
  for (const id of [
    "save",
    "copy",
    "details",
    "combat",
    "body",
    "apply-stats",
    "ui-import",
    "ui-clear",
    "ui-settings",
    "preview",
    "export",
    "texture",
    "clear-texture",
  ])
    $(id).disabled = !d;
  $("deployment-mode").value = d?.deployment?.mode || (workflow === "retail-edit" ? "override" : "add");
  applyWorkflow();
  $("apply-deployment").disabled = !d;
  const appearanceOnly = d?.deployment && d.deployment.mode !== "add";
  $("outfit-controls").hidden = !d || appearanceOnly;
  $("preview-outfit").closest("label").hidden = !d || appearanceOnly;
  const outfits = s.outfits || [];
  options(
    "preview-outfit",
    outfits.map((row, index) => ({ ...row, name: `${index + 1}. ${row.name}` })),
    s.active_outfit,
  );
  $("outfit-list").replaceChildren(
    ...outfits.map((row, index) => {
      const button = document.createElement("button");
      button.textContent = `${index + 1}. ${row.name}`;
      button.className = "outfit-card";
      button.setAttribute("aria-pressed", String(row.id === s.active_outfit));
      button.onclick = () => act("retail_outfit_select", { id: row.id });
      return button;
    }),
  );
  $("outfit-name").value = outfits.find((row) => row.id === s.active_outfit)?.name || "";
  $("outfit-copy").disabled = !d || outfits.length >= 3;
  $("outfit-remove").disabled = !d || s.active_outfit === "default";
  $("deployment-status").textContent =
    d?.deployment?.mode === "override"
      ? "Replaces the existing retail appearance. No extra roster cell is created."
      : d?.deployment?.mode === "outfit"
        ? "Adds this appearance to the target’s clothing selector. Original outfit stays available; combat, voice and stats remain shared."
        : "Creates a separate fighter in the roster.";
  for (const id of ["combat", "apply-stats"]) $(id).disabled = !d || appearanceOnly;
  if (d?.deployment?.mode === "override")
    for (const id of ["ui-import", "ui-clear", "ui-settings"]) $(id).disabled = true;
  $("undo").disabled = !s.undo;
  $("reset").disabled = !d || !s.path;
  $("ui-scale").value = String(d?.ui_art.hd_scale || 4);
  options("role", s.roles);
  options("shape", shapeRows.length ? shapeRows : [{ id: "", name: "Load the 3D preview to list the shapes" }]);
  $("shape").disabled = !shapeRows.length;
  const components = $("components");
  components.replaceChildren();
  for (const key of ["appearance", "voice", "blazin", "intro", "victory", "portrait"]) {
    const label = document.createElement("label");
    label.textContent =
      key === "appearance"
        ? "Model resource"
        : key === "blazin"
          ? "Blazin’ resource"
          : key[0].toUpperCase() + key.slice(1) + " resource";
    const select = document.createElement("select");
    select.id = "resource-" + key;
    const kind = { intro: "cinematic", victory: "cinematic", blazin: "blazin" }[key] || key;
    const rows = (d?.resources || []).filter((r) => r.kind === kind);
    select.append(new Option("Inherit from donor", ""));
    for (const row of rows) select.append(new Option(row.id, (d?.identity.pack || "") + "/" + row.id));
    const chosen = d?.definition.components[key];
    select.value =
      chosen && !chosen.startsWith("retail/") ? d.identity.pack + "/" + chosen.split("/")[1] : chosen || "";
    select.disabled =
      !d ||
      (appearanceOnly && !["appearance", "portrait"].includes(key)) ||
      (key === "portrait" && d?.deployment?.mode === "override");
    select.onchange = () => act("retail_component", { component: key, resource: select.value });
    label.append(select);
    components.append(label);
  }
  const inherited = s.donors.find((r) => r.id === selected)?.stats || {},
    stats = d?.definition.components.stats || {};
  $("stats").replaceChildren();
  for (const key of ["health", "speed", "toughness", "charisma"]) {
    const line = document.createElement("label");
    line.className = "stat-line";
    line.textContent = key[0].toUpperCase() + key.slice(1);
    const input = document.createElement("input");
    input.id = "stat-" + key;
    input.type = "number";
    input.min = 0;
    input.max = 100;
    input.step = 1;
    input.value = stats[key] ?? inherited[key] ?? 0;
    input.disabled = !d;
    line.append(input);
    $("stats").append(line);
  }
  showArt();
  $("texture-status").textContent = d ? Object.keys(d.textures).length + " texture overrides staged." : "";
  performance.render(performanceState());
  if (refreshRuntime) {
    clearPreview();
    if (d) queueMicrotask(() => $("preview").click());
  }
}

function performanceState() {
  const independent = state?.document && (state.document.deployment?.mode || "add") === "add";
  return {
    ...state,
    project: independent
      ? { ...state.document, metadata: { ...state.document.metadata, donor: state.document.definition.inherits } }
      : null,
    appearance_key: JSON.stringify([
      state?.document?.identity.pack,
      state?.active_outfit,
      state?.document?.definition.components.appearance,
    ]),
    performance: {
      ...state?.performance,
      unavailable_reason:
        state?.document && !independent
          ? "Appearance-only projects share the original fighter's voice, AI and presentation. Start a standalone fighter for independent performance."
          : "Create or open a standalone fighter project to author performance.",
    },
    retail_movesets: { selected: state?.document?.definition.inherits },
  };
}
const performance = performanceEditor({
  $,
  state: performanceState,
  call: (action, args, label) => call("retail_" + action, args, label),
  act: (action, args, label) =>
    act(action === "choose_voice_clip" ? "choose_retail_voice_clip" : "retail_" + action, args, label),
  applyState: render,
  fail: (error) => {
    status(error.message, true);
    attachDetails($("toast"), error.detail);
  },
  parts: () => sceneData?.meshes || [],
  meshes: () => [...model.children],
  repose: () => {},
  canAnimate: () => Boolean(state?.setup?.runtime?.extensions?.includes("retail-animation-preview-1")),
});
function showArt() {
  const d = state?.document,
    role = $("role").value,
    raw = d?.ui_art.images[role];
  $("art-image").hidden = !raw;
  if (raw) $("art-image").src = "data:image/png;base64," + raw;
  else $("art-image").removeAttribute("src");
  $("art-status").textContent = d
    ? Object.keys(d.ui_art.images).length + " imported roles · missing art inherits the UI donor."
    : "";
}
$("role").onchange = showArt;
for (const id of ["name", "author", "version", "description", "license", "pack", "fighter"])
  $(id).oninput = () => {
    const metadata = {};
    for (const key of ["name", "author", "version", "description", "license"]) metadata[key] = $(key).value;
    detailDraft = { metadata, identity: { pack: $("pack").value, fighter: $("fighter").value } };
    if (state) {
      state.dirty = true;
      $("saved").textContent = "● Unsaved changes";
    }
    clearTimeout(draftTimer);
    const send = async () => {
      if (!detailDraft) return;
      if (pending.size) {
        draftTimer = setTimeout(send, 150);
        return;
      }
      const draft = detailDraft;
      try {
        await call("retail_draft", draft);
        if (detailDraft === draft) detailDraft = null;
      } catch (e) {
        status(e.message, true);
      }
    };
    draftTimer = setTimeout(send, 120);
  };
const sectionTabs = createTabs({
  root: document.querySelector(".retail-right"),
  buttons: "[data-panel]",
  panels: "[data-content]",
  key: "panel",
  panelKey: "content",
  onSelect(name) {
    if (["voice", "presentation", "ai"].includes(name)) performance.ensureConnected();
    if (
      name === "textures" &&
      !shapeRows.length &&
      state?.document?.definition.components.appearance &&
      !$("preview").disabled
    )
      $("preview").click();
  },
});
try {
  $("retail-workflow").open = !localStorage.getItem("retail-guide-seen");
  localStorage.setItem("retail-guide-seen", "1");
} catch {
  $("retail-workflow").open = true;
}
$("new-open").onclick = () => {
  $("retail-start").open = true;
  $("base-donor").focus();
};
$("base-donor").onchange = () => {
  for (const id of ["deployment-target", "combat-donor", "body-donor", "ui-donor"]) $(id).value = $("base-donor").value;
  donorSummary();
};
function donorSummary() {
  const label = (id) => $(id).selectedOptions[0]?.textContent || "Not connected";
  $("donor-summary").textContent =
    `Combat: ${label("combat-donor")} · Body to import: ${label("body-donor")} · UI: ${label("ui-donor")}`;
}
for (const id of ["combat-donor", "body-donor", "ui-donor"]) $(id).onchange = donorSummary;
document.addEventListener("keydown", (event) => {
  if (!(event.ctrlKey || event.metaKey) || event.altKey) return;
  const id = event.key.toLowerCase() === "s" ? "save" : event.key.toLowerCase() === "z" ? "undo" : null;
  if (id) {
    event.preventDefault();
    if (!$(id).disabled) $(id).click();
  }
});
$("home").onclick = () => act("open_home");
window.__retailAct = (...args) => act(...args);
$("new").onclick = () => {
  if (discard()) {
    const donor = $("base-donor").value;
    $("body-donor").value = donor;
    act("retail_new", { donor, mode: $("deployment-mode").value });
  }
};
$("open").onclick = () => {
  if (discard()) act("choose_retail_open");
};
$("import").onclick = () => {
  if (discard()) act("choose_retail_import", {}, "Importing fighter assets…");
};
$("save").onclick = () => act("choose_retail_save");
$("copy").onclick = () => act("choose_retail_copy");
$("preview-outfit").onchange = () => act("retail_outfit_select", { id: $("preview-outfit").value });
$("outfit-name").onchange = () => act("retail_outfit_rename", { name: $("outfit-name").value });
$("outfit-copy").onclick = () => act("retail_outfit_copy");
$("outfit-remove").onclick = () => {
  if (confirm("Remove this outfit? You can undo this change.")) act("retail_outfit_remove");
};
$("undo").onclick = () => act("retail_undo");
$("reset").onclick = () => {
  if (discard()) act("retail_reset");
};
$("details").onclick = () => {
  const metadata = {};
  for (const k of ["name", "author", "version", "description", "license"]) metadata[k] = $(k).value;
  act("retail_details", { metadata, identity: { pack: $("pack").value, fighter: $("fighter").value } });
};
$("apply-deployment").onclick = () =>
  act("retail_deployment", { mode: $("deployment-mode").value, target: $("deployment-target").value });
$("combat").onclick = () => act("retail_moveset", { donor: $("combat-donor").value });
$("body").onclick = async () => {
  const result = await act(
    "retail_appearance",
    { donor: $("body-donor").value },
    "Importing original model resources…",
  );
  if (result?.retail) {
    clearPreview();
    $("preview").click();
  }
};
$("empty-body").onclick = () => $("body").click();
$("empty-preview").onclick = () => $("preview").click();
$("apply-stats").onclick = () =>
  act("retail_stats", {
    stats: Object.fromEntries(
      ["health", "speed", "toughness", "charisma"].map((k) => [k, Number($("stat-" + k).value)]),
    ),
  });
$("ui-settings").onclick = () =>
  act("retail_ui_settings", { donor: $("ui-donor").value, hd_scale: Number($("ui-scale").value) });
$("ui-import").onclick = () => act("choose_retail_ui", { role: $("role").value });
$("ui-clear").onclick = () => act("retail_ui", { role: $("role").value });
$("texture").onclick = () => act("choose_retail_texture", { shape: $("shape").value });
$("clear-texture").onclick = () => act("retail_texture", { shape: $("shape").value });
const exportWorkflow = createExportWorkflow({
  $,
  state: () => state,
  call: (action, args) => call("retail_" + action, args),
  act: (action, args, label) => act(action === "save" ? "choose_retail_save" : "choose_retail_export", args, label),
  fail: (error) => status(error.message, true),
  hasFaceDraft: () => false,
  hasTryOn: () => false,
  jump: (tab) =>
    tab === "setup"
      ? setup.open(state?.setup)
      : sectionTabs.show(tab === "project" ? "details" : tab === "outfits" ? "appearance" : tab),
});
$("export").onclick = exportWorkflow.open;
const { scene, camera, renderer, controls } = createStage({
  THREE,
  OrbitControls,
  viewport: $("viewport"),
  fov: 35,
  far: 5000,
});
const model = new THREE.Group();
scene.add(model);
let bounds,
  images = [];
function clearPreview() {
  performance.stop();
  sceneData = null;
  disposeModel(model);
  for (const image of images) image.dispose();
  images = [];
  shapeRows = [];
  bounds = null;
  epoch++;
  window.__retailPreview = { ready: false };
  $("preview-empty").hidden = false;
  $("preview-note").textContent = "";
}
function frame(direction = 1) {
  frameStage({
    THREE,
    camera,
    controls,
    bounds,
    view: direction < 0 ? "back" : "fit",
    factor: 1.9,
    lift: 0.04,
    near: 0.01,
  });
}
$("fit").onclick = () => frame();
$("front").onclick = () => frame();
$("back").onclick = () => frame(-1);
$("wireframe").onchange = () => {
  for (const mesh of model.children) mesh.material.wireframe = $("wireframe").checked;
};
$("preview").onclick = async () => {
  const mine = ++epoch,
    result = unpackPreview(await act("retail_preview", {}, "Decoding the static model…"));
  if (!result || mine !== epoch) return;
  const loadedImages = [];
  const loader = new THREE.TextureLoader(),
    textures = {};
  await Promise.all(
    Object.entries(result.textures).map(async ([key, url]) => {
      const texture = await loader.loadAsync(url);
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.flipY = false;
      textures[key] = texture;
      loadedImages.push(texture);
    }),
  );
  if (mine !== epoch) {
    for (const image of loadedImages) image.dispose();
    return;
  }
  performance.stop();
  sceneData = result;
  disposeModel(model);
  for (const image of images) image.dispose();
  images = loadedImages;
  for (const part of result.meshes) {
    const geometry = geometryFor(THREE, part);
    const mesh = new THREE.Mesh(
      geometry,
      new THREE.MeshBasicMaterial({
        map: textures[part.atlas],
        side: THREE.DoubleSide,
        wireframe: $("wireframe").checked,
      }),
    );
    mesh.userData.source = part;
    model.add(mesh);
  }
  bounds = result.bounds;
  shapeRows = result.shapes.map((r) => ({ id: r.name, name: r.name + " · " + r.width + "×" + r.height }));
  options("shape", shapeRows);
  $("shape").disabled = !state?.document;
  frame();
  $("preview-note").textContent = result.notices.join(" · ");
  $("preview-empty").hidden = true;
  window.__retailPreview = { ready: true, meshes: result.meshes.length, shapes: result.shapes };
};

renderer.setAnimationLoop((now) => {
  performance.tick(now);
  controls.update();
  renderer.render(scene, camera);
});
new QWebChannel(qt.webChannelTransport, (channel) => {
  client.connect(channel.objects.editor);
  act("retail_snapshot").then(startFlow);
});
