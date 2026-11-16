import { attachDetails } from "./errors.mjs";

export function projectLocation(path) {
  if (!path) return { name: "Unsaved project", folder: "" };
  const last = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
  return { name: path.slice(last + 1), folder: path.slice(0, last) };
}

export function createProjectPanel({ $, act, workflow }) {
  return function renderProjectPanel(state) {
    const present = workflow === "caf" && Boolean(state.project);
    document.body.dataset.hasProject = String(present);
    $("profile-sidebar").hidden = present;
    $("project-sidebar").hidden = !present;
    if (!present) return;
    const location = projectLocation(state.project_path);
    $("project-file-name").textContent = location.name;
    $("project-folder").textContent = location.folder;
    $("project-folder").title = state.project_path || "";
    $("project-origin").textContent = state.project_origin
      ? "Based on Story fighter " + state.project_origin
      : "Portable project. Story profiles stay separate.";
    $("project-outfits").replaceChildren(
      ...(state.outfits || []).map((row, index) => {
        const button = document.createElement("button");
        button.textContent = `${index + 1}. ${row.name}`;
        button.className = "outfit-card";
        button.setAttribute("aria-pressed", String(row.id === state.active_outfit));
        button.onclick = () => act("outfit_select", { id: row.id }, "Switching outfit…");
        return button;
      }),
    );
  };
}

export function createExportWorkflow({ $, call, act, fail, state, jump, hasFaceDraft, hasTryOn }) {
  const dialog = $("export-ready");
  async function open() {
    $("export-checks").replaceChildren();
    $("export-ready-confirm").disabled = true;
    dialog.showModal();
    try {
      const result = await call("export_checklist");
      const checks = [...result.checks];
      if (hasFaceDraft())
        checks.push({
          label: "Apply or revert the temporary face preview before exporting.",
          status: "fail",
          tab: "appearance",
        });
      if (hasTryOn())
        checks.push({
          label: "A clothing try-on is visible. Equip it to include it; export otherwise uses the staged outfit.",
          status: "note",
          tab: "appearance",
        });
      checks.push({
        label: state().dirty ? "Pending project and texture changes will be saved." : "No unsaved project changes.",
        status: "pass",
        tab: "textures",
      });
      $("export-checks").replaceChildren(
        ...checks.map((check) => {
          const item = document.createElement("li");
          item.className = check.status;
          const label = document.createElement("span");
          label.textContent = (check.status === "fail" ? "✗ " : check.status === "note" ? "· " : "✓ ") + check.label;
          const link = document.createElement("button");
          link.className = "text-button";
          link.textContent =
            {
              setup: "Game setup",
              project: "Details",
              textures: "Textures",
              outfits: "Outfits",
              appearance: "Appearance",
            }[check.tab] || "Open";
          link.onclick = () => {
            dialog.close();
            jump(check.tab);
          };
          item.append(label, link);
          attachDetails(item, check.detail);
          return item;
        }),
      );
      $("export-ready-confirm").disabled = !result.can_export || checks.some((check) => check.status === "fail");
    } catch (error) {
      dialog.close();
      fail(error);
    }
  }
  $("export-ready-cancel").onclick = () => dialog.close();
  $("export-ready-confirm").onclick = async () => {
    $("export-ready-confirm").disabled = true;
    if (state().dirty && !(await act("save", {}, "Saving fighter project…"))) return;
    dialog.close();
    await act("choose_mod_export", {}, "Validating and exporting fighter mod…");
  };
  return { open };
}
