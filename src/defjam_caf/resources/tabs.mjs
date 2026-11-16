export function nextTabIndex(index, key, count) {
  if (key === "Home") return 0;
  if (key === "End") return count - 1;
  return (index + (["ArrowUp", "ArrowLeft"].includes(key) ? -1 : 1) + count) % count;
}

export function createTabs({
  root,
  buttons = ".tab",
  panels = ".tab-content",
  key = "tab",
  panelKey = null,
  onSelect = () => {},
}) {
  const tabs = [...root.querySelectorAll(buttons)],
    contents = [...root.querySelectorAll(panels)];
  const nameOf = (button) => button.dataset[key];
  function show(name, { focus = false } = {}) {
    const selected = tabs.find((button) => nameOf(button) === name);
    if (!selected || selected.disabled) return;
    for (const button of tabs) {
      const active = button === selected;
      button.setAttribute("role", "tab");
      button.setAttribute("aria-selected", String(active));
      button.classList.toggle("active", active);
      button.tabIndex = active ? 0 : -1;
    }
    for (const panel of contents) {
      panel.setAttribute("role", "tabpanel");
      panel.hidden = panelKey ? panel.dataset[panelKey] !== name : panel.id !== "tab-" + name;
    }
    if (focus) selected.focus();
    onSelect(name);
  }
  for (const button of tabs) {
    button.onclick = () => show(nameOf(button));
    button.onkeydown = (event) => {
      if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
      const visible = tabs.filter((tab) => !tab.disabled && tab.getClientRects().length);
      event.preventDefault();
      const next = visible[nextTabIndex(visible.indexOf(button), event.key, visible.length)];
      if (next) show(nameOf(next), { focus: true });
    };
  }
  show(nameOf(tabs.find((button) => button.classList.contains("active")) || tabs[0]));
  return { show, active: () => nameOf(tabs.find((button) => button.classList.contains("active"))) };
}
