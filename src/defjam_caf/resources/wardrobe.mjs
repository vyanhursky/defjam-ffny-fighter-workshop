export function groupKey(o) {
  return `${o.garment}||${(Number(o.key.split(":")[1]) & 0xff00ffff) >>> 0}`;
}
export function filterOptions(options, query) {
  const normalized = query.toLowerCase().trim();
  return options.filter((o) => o.label.toLowerCase().includes(normalized));
}
