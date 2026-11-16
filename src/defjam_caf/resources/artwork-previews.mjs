const representatives = {
  selector: "selector_2p",
  loading: "loading_2p",
  icon: "result_2p",
  titlecard: "selector_logo_2p",
  grid_normal: "grid_normal_2p",
  grid_selected: "grid_selected_2p",
};
function master(role) {
  if (role in representatives) return role;
  const base = role.replace(/_[234]p$/, "");
  return base.endsWith("_logo") ? "titlecard" : base === "result" ? "icon" : base;
}
export function artworkPreview(imports, references, role, original = false) {
  const group = master(role);
  if (!original) {
    let key = [role, group, ...(role.startsWith("grid_") ? ["icon"] : [])].find((k) => imports[k]);
    if (!key && role in representatives) key = Object.keys(imports).find((k) => master(k) === role);
    if (key)
      return { png: "data:image/png;base64," + imports[key], original: false, caption: "Imported artwork · " + key };
  }
  const key = representatives[role] || role;
  const png = references?.images[key];
  if (!png) return null;
  const size = references.layouts[key];
  return {
    png,
    original: true,
    caption: `Original donor · ${key} · ${size[0]}×${size[1]}${role in representatives ? " · 2-player example" : ""}`,
  };
}
