// Game setup: one place, shared by the fighter editor and the retail studio, to say where the game and its data are.
// The choice is saved by the Workshop, so every tool that needs the game's own scripts uses it without asking again.
export function gameSetup({call, act}) {
  const dialog = document.createElement('dialog');
  dialog.id = 'setup';
  dialog.className = 'setup';
  dialog.innerHTML = `
    <h3>Game setup</h3>
    <p class="hint">Choose where your game is installed. The Workshop reads your own game files and uses the installed game's tools; you only do this once.</p>
    <h4>1 · Your game folder</h4>
    <div class="setup-row"><code id="setup-folder">Not found yet</code><button id="setup-browse">Browse…</button></div>
    <p class="hint">Usually <b>C:\\Users\\&lt;you&gt;\\AppData\\Local\\DefJamRecompiled</b> on Windows or <b>~/Library/Application Support/DefJamRecompiled</b> on macOS — the folder that holds <b>app</b> and <b>data</b>. A source checkout also works.</p>
    <h4>2 · Game version</h4>
    <select id="setup-version" aria-label="Game version"></select>
    <ul id="setup-features" class="setup-features"></ul>
    <h4>3 · Game data</h4>
    <div class="setup-row"><code id="setup-data">Not chosen yet</code><button id="setup-data-change">Choose…</button></div>
    <p class="hint">The folder with <b>extracted</b> and <b>save</b> in it. It is normally the <b>data</b> folder inside your game folder, so it is filled in for you.</p>
    <p id="setup-message" class="hint" aria-live="polite"></p>
    <div class="dialog-actions"><button id="setup-cancel" class="quiet">Later</button><button id="setup-use" class="primary">Use these settings</button></div>`;
  document.body.append(dialog);
  const $ = id => dialog.querySelector('#' + id);
  let scan = null, current = null, dismissed = false;

  function selected() { return scan?.candidates.find(row => row.path === $('setup-version').value) || null; }

  function showFeatures() {
    const row = selected(), list = $('setup-features');
    list.replaceChildren();
    if (!row) { $('setup-message').textContent = scan?.folder ? 'No game version with the Workshop tools was found in that folder.' : ''; }
    else {
      for (const [name, ok] of Object.entries(row.features)) {
        const item = document.createElement('li');
        item.className = ok ? 'ok' : 'no';
        item.textContent = (ok ? '✓ ' : '✗ ') + row.labels[name] + (ok ? '' : ' — ' + row.missing[name]);
        list.append(item);
      }
      $('setup-message').textContent = row.complete ? '' : 'You can still use this version for what it supports. Features marked ✗ stay unavailable until you choose a newer one.';
    }
    $('setup-use').disabled = !row || (!scan.data && !current?.data);
  }

  function show(result) {
    scan = result;
    $('setup-folder').textContent = scan.folder || 'Not found yet — use Browse…';
    $('setup-version').replaceChildren(...scan.candidates.map(row => new Option(row.label + (row.note ? ' · ' + row.note : '') + (row.complete ? '' : ' · limited'), row.path)));
    const keep = current?.runtime && scan.candidates.find(row => row.path.toLowerCase() === current.runtime.path.toLowerCase());
    const best = keep || scan.candidates.find(row => row.complete) || scan.candidates[0];
    if (best) $('setup-version').value = best.path;
    $('setup-data').textContent = scan.data || current?.data || 'Not chosen yet';
    showFeatures();
  }

  async function open(setup) {
    current = setup || current;
    dialog.showModal();
    try { show(await call('setup_scan', {})); } catch (error) { $('setup-message').textContent = error.message; }
  }

  $('setup-version').onchange = showFeatures;
  $('setup-browse').onclick = async () => { const result = await act('choose_setup_folder'); if (result?.candidates) show(result); };
  $('setup-data-change').onclick = async () => {
    const result = await act('choose_data', {}, 'Loading profiles and original assets…');
    if (result?.snapshot || result?.profiles) { current = {...current, data: result.data || result.snapshot?.data}; $('setup-data').textContent = current.data || ''; showFeatures(); }
  };
  $('setup-cancel').onclick = () => { dismissed = true; dialog.close(); };
  $('setup-use').onclick = async () => {
    const row = selected();
    if (!row) return;
    dialog.close();
    await act('setup_use', {runtime: row.path, folder: scan.folder, data: scan.data}, 'Applying game setup…');
  };

  return {
    open,
    /** Opens the dialog by itself the first time something is missing, unless it was already put off. */
    offer(setup) { current = setup; if (!setup?.ready && !dismissed && !dialog.open) open(setup); },
    /** Header chip text and state for the current setup. */
    chip(setup) {
      const runtime = setup?.runtime;
      if (!runtime || !setup.data) return {text: 'Set up your game', state: 'alert'};
      return {text: runtime.label + (runtime.complete ? '' : ' · limited'), state: runtime.complete ? 'ok' : 'warn'};
    },
  };
}
