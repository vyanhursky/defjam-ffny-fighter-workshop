export function createUIArt({ $, call, fail, state }) {
  let uiArtEpoch = 0,
    donors = [],
    donorRuntime = null,
    donorTask = null,
    donorError = "",
    previewKey = null;
  function renderDonors(current) {
    const rows = donors.length ? donors : current?.performance?.catalog?.fighters || [];
    const chosen = current?.ui_art?.donor || "retail/blaze";
    $("ui-donor").replaceChildren(...rows.map((row) => new Option(row.label, row.key)));
    if (!rows.some((row) => row.key === chosen)) $("ui-donor").prepend(new Option("Current donor · " + chosen, chosen));
    $("ui-donor").value = chosen;
    $("ui-donor").disabled = !current?.project || !rows.length;
    $("ui-donor-status").textContent =
      donorError ||
      (rows.length
        ? "Choose an original fighter by name. Saved donor identity is preserved."
        : "Connect your game in Game setup to choose a different donor.");
  }
  async function ensureDonors() {
    const current = state(),
      runtime = current?.setup?.runtime?.path;
    if (donorTask) return donorTask;
    if (donorRuntime === runtime && donors.length) return donors;
    if (!current?.setup?.ready) {
      renderDonors(current);
      return null;
    }
    donors = [];
    donorError = "";
    donorRuntime = runtime;
    donorTask = (async () => {
      try {
        donors = (await call("donors")).donors;
      } catch (error) {
        donorError = error.message;
      } finally {
        donorTask = null;
        renderDonors(state());
      }
      return donors;
    })();
    return donorTask;
  }
  async function previewUIArt() {
    const role = $("ui-role").value;
    const row = state()?.ui_art?.roles.find((r) => r.id === role);
    $("ui-clear").disabled = !state()?.project || !row?.own;
    $("ui-role-status").textContent = row
      ? `${row.label} · ${row.origin.source}${row.origin.role ? " · " + row.origin.role : ""}`
      : "Create or open a fighter project to import UI artwork.";
    const next = JSON.stringify([
      state()?.project?.identity.pack,
      state()?.active_outfit,
      role,
      state()?.ui_art?.revision,
    ]);
    if (next === previewKey) return;
    previewKey = next;
    const epoch = ++uiArtEpoch;
    $("ui-image").hidden = true;
    if (!state()?.project || !role) return;
    try {
      const result = await call("ui_preview", { role });
      if (epoch !== uiArtEpoch) return;
      $("ui-image").hidden = !result?.png;
      if (result?.png) $("ui-image").src = result.png;
      window.__cafUIArt = { role, ready: true, hasImage: Boolean(result?.png) };
    } catch (e) {
      if (epoch === uiArtEpoch) fail(e);
    }
  }
  function renderUIArt(state) {
    const ui = state.ui_art,
      role = $("ui-role").value;
    $("ui-scale").value = String(ui?.hd_scale || 4);
    $("ui-role").replaceChildren();
    const groups = new Map();
    for (const row of ui?.roles || []) {
      let group = groups.get(row.group);
      if (!group) {
        group = document.createElement("optgroup");
        group.label = row.group;
        groups.set(row.group, group);
        $("ui-role").append(group);
      }
      group.append(new Option(row.label, row.id));
    }
    if ((ui?.roles || []).some((r) => r.id === role)) $("ui-role").value = role;
    for (const id of ["ui-donor", "ui-scale", "ui-role", "ui-apply-settings", "ui-retail", "ui-import", "ui-clear-all"])
      $(id).disabled = !state.project;
    renderDonors(state);
    const outfit = state.outfits?.find((r) => r.id === state.active_outfit);
    $("ui-outfit").textContent = state.project
      ? `Editing ${outfit?.name || "Outfit 1"}. ${state.active_outfit === "default" ? "These UI defaults are shared with the other outfits." : "Overrides apply to this outfit."}`
      : "UI artwork belongs to standalone fighter projects.";
    const variants = (ui?.roles || []).filter((r) => r.group !== "All layouts");
    $("ui-coverage").textContent = ui
      ? `${variants.filter((r) => r.available).length}/24 roles use project images. Remaining roles inherit the UI donor. ${ui.hd_scale === 1 ? "Native output." : ui.hd_scale + "× HD tiles accompany the native fallback."}`
      : "";
    previewUIArt();
  }
  return { previewUIArt, renderUIArt, ensureDonors };
}
