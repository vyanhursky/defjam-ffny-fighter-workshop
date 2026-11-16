/** A bounded memory cache and one background preparation queue. Backend owns the disk cache. */
export function createAuditions({ load, maxBytes = 32 * 1024 ** 2, progress = () => {} }) {
  const cache = new Map(),
    pending = new Map();
  let bytes = 0,
    generation = 0,
    context = "";
  function key(request) {
    return JSON.stringify([context, Object.entries(request).sort(([a], [b]) => a.localeCompare(b))]);
  }
  async function get(request) {
    const id = key(request),
      epoch = generation;
    if (cache.has(id)) {
      const value = cache.get(id);
      cache.delete(id);
      cache.set(id, value);
      return value;
    }
    if (pending.has(id)) return pending.get(id);
    const task = (async () => {
      const value = await load(request),
        size = value.data.length * 2;
      if (epoch === generation && size <= maxBytes) {
        while (bytes + size > maxBytes && cache.size) {
          const oldest = cache.keys().next().value;
          bytes -= cache.get(oldest).data.length * 2;
          cache.delete(oldest);
        }
        cache.set(id, value);
        bytes += size;
      }
      return value;
    })();
    pending.set(id, task);
    try {
      return await task;
    } finally {
      if (pending.get(id) === task) pending.delete(id);
    }
  }
  return {
    get,
    context(value) {
      if (context === value) return;
      context = value;
      generation++;
      cache.clear();
      pending.clear();
      bytes = 0;
    },
    cancel() {
      generation++;
    },
    async prepare(requests) {
      const epoch = ++generation;
      let done = 0,
        failed = 0;
      progress({ done, failed, total: requests.length });
      for (const request of requests) {
        if (epoch !== generation) return;
        try {
          await get(request);
        } catch {
          failed++;
        }
        if (epoch !== generation) return;
        done++;
        progress({ done, failed, total: requests.length });
        await new Promise((resolve) => setTimeout(resolve, 0));
      }
    },
  };
}

export function voiceRequests(fighter, banks, catalogBanks) {
  if (!fighter) return [];
  const requests = [];
  for (const category of ["Character", "Taunts", "Enviro"]) {
    const voice = banks[category] ?? fighter.voice;
    const row = catalogBanks.find((r) => r.category === category && r.voice === voice);
    for (let index = 0; index < (row?.count || 0); index++) requests.push({ category, voice, index });
  }
  for (const role of ["intro", "extro"]) for (const stream of fighter.streams?.[role] || []) requests.push({ stream });
  return requests;
}
