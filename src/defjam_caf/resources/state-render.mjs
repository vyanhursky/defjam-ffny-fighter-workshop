export function shouldRefreshAppearance(previous, next, force = false) {
  return force || !previous || previous.appearance_key !== next.appearance_key;
}
