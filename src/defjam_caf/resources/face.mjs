export function faceMethodState(sculpt, project, requested) {
  const locked = { presets: Boolean(sculpt.present), sliders: !project || Boolean(sculpt.imported), mesh: !project };
  let method = sculpt.imported ? "mesh" : sculpt.present ? "sliders" : requested;
  if (locked[method]) method = "presets";
  return { locked, method };
}

export function createFaceControls({ $, readyFighter, makeOptions, act, renderFaceSculpt }) {
  function faceMethod() {
    return document.querySelector("input[name=face-method]:checked").value;
  }
  function syncFace(state) {
    const sculpt = state?.face_sculpt || {},
      project = Boolean(state?.project);
    const radios = Object.fromEntries(
      [...document.querySelectorAll("input[name=face-method]")].map((radio) => [radio.value, radio]),
    );
    const { locked, method } = faceMethodState(sculpt, project, faceMethod());
    for (const [name, radio] of Object.entries(radios)) {
      radio.disabled = locked[name] || !readyFighter();
      radio.closest(".choice-opt").classList.toggle("locked", locked[name]);
    }
    radios[method].checked = true;
    for (const panel of document.querySelectorAll(".face-panel")) panel.hidden = panel.dataset.face !== method;
    $("face-method-note").textContent = !project
      ? "Standalone fighter projects also offer proportion sliders and imported head meshes."
      : sculpt.imported
        ? "This outfit uses an imported head mesh, so presets and sliders are off."
        : sculpt.present
          ? "This outfit has slider changes saved, so the original presets are off."
          : "Each outfit uses one method at a time.";
    $("face-method-clear").hidden = !sculpt.present;
    $("face-method-clear").disabled = !sculpt.present;
  }
  function renderFacePresets(state) {
    renderFaceSculpt(state);
    const root = $("face-presets");
    root.replaceChildren();
    for (const row of state.face_presets || []) {
      const label = document.createElement("label");
      label.textContent = row.label;
      const select = document.createElement("select");
      select.id = "face-" + row.id;
      makeOptions(select, row.options, row.value);
      if (!row.options.some((option) => option.value === row.value)) {
        const preserved = new Option("Unavailable saved preset · preserved", String(row.value));
        preserved.disabled = true;
        select.prepend(preserved);
        select.value = String(row.value);
      }
      select.disabled = !readyFighter() || !row.options.length;
      select.onchange = () => act("appearance", { changes: { [row.id]: Number(select.value) } }, "Updating face…");
      label.append(select);
      root.append(label);
    }
  }
  return { faceMethod, syncFace, renderFacePresets };
}
