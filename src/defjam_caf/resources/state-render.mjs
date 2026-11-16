export function shouldRefreshAppearance(previous, next, force = false) {
  return force || !previous || previous.appearance_key !== next.appearance_key;
}

export function createStateRenderer({ $, act, discard }) {
  function renderBackups(state) {
    const rows = state.backups || [];
    $("backups-box").hidden = !state.selected || Boolean(state.project);
    $("backups").replaceChildren(
      ...(rows.length
        ? rows.slice(0, 4).map((row) => {
            const line = document.createElement("div");
            line.className = "backup-row";
            const when = new Date(row.when);
            const text = document.createElement("span");
            text.textContent =
              when.toLocaleDateString(undefined, { month: "short", day: "numeric" }) +
              " " +
              when.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
            const button = document.createElement("button");
            button.textContent = "Restore";
            button.onclick = () => {
              if (!discard()) return;
              if (
                confirm(
                  "Restore " +
                    state.selected +
                    " from the backup of " +
                    when.toLocaleString() +
                    "?\n\nYour current save is backed up first. Close the game before restoring.",
                )
              )
                act("restore_backup", { id: row.id }, "Restoring backup…");
            };
            line.append(text, button);
            return line;
          })
        : [
            Object.assign(document.createElement("div"), {
              className: "backup-row",
              textContent: "No backups of this profile yet.",
            }),
          ]),
    );
  }
  return { renderBackups };
}
