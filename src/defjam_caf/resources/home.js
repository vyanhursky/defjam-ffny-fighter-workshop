// Home: the front door. It only chooses a workflow; each workflow page does its own work.
import {gameSetup} from './setup.mjs';

const $ = id => document.getElementById(id), pending = new Map();
let serial = 0, bridge, state = null;

function call(action, args = {}) {
  const id = String(++serial);
  return new Promise((resolve, reject) => { pending.set(id, {resolve, reject}); bridge.dispatch(JSON.stringify({id, action, args})); });
}
function toast(text, error = false) {
  $('status-message').textContent = text;
  $('toast').textContent = text;
  $('toast').classList.toggle('error', error);
  $('toast').hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { $('toast').hidden = true; }, 9000);
}
async function act(action, args = {}, label = 'Working…') {
  $('busy-label').textContent = label;
  $('busy').hidden = false;
  try {
    const result = await call(action, args);
    if (result?.message) toast(result.message);
    return result;
  } catch (error) {
    toast(error.message || String(error), true);
    return null;
  } finally { $('busy').hidden = true; }
}

const setup = gameSetup({call, act: async (action, args, label) => {
  const result = await act(action, args, label);
  if (action === 'setup_use' || action === 'choose_data') await refresh();
  return result;
}});
$('setup-open').onclick = () => setup.open(state?.setup);

const GROUPS = [
  {title: 'CHANGE WHAT’S IN YOUR SAVE', cards: [{
    name: 'Story character editor',
    about: 'Edit your Create-a-Fighters inside a Story save: their look, stats and moves.',
    buttons: [['Open a save profile', {mode: 'story', start: 'open'}, true], ['Import a .djprofile', {mode: 'story', start: 'import'}]],
    note: s => s.setup.data ? '' : 'Needs your game data. Use Game setup, top right.'}]},
  {title: 'MAKE A NEW FIGHTER · A .FFNYFIGHTER PROJECT YOU CAN EXPORT AS A MOD', cards: [{
    name: 'Fighter from a Create-a-Fighter',
    about: 'Start with one of your Create-a-Fighters, then give it its own artwork, outfits, voice, moves and AI.',
    buttons: [['New fighter', {mode: 'caf', start: 'new'}, true], ['Open project', {mode: 'caf', start: 'open'}]],
    note: s => !s.setup.data ? 'Needs your game data. Use Game setup, top right.'
      : !s.setup.runtime?.features.export ? 'You can build it now, but exporting needs a newer game version. See Game setup.' : ''}, {
    name: 'Fighter from a retail fighter',
    about: 'Start from one of the game’s own fighters and turn them into someone new.',
    buttons: [['New fighter', {mode: 'retail-new', start: 'new'}, true], ['Open project', {mode: 'retail-new', start: 'open'}]],
    note: retailNote}]},
  {title: 'CHANGE A RETAIL FIGHTER', cards: [{
    name: 'Retail fighter editor',
    about: 'Replace how an existing fighter looks, or add an extra outfit, without making a new fighter.',
    buttons: [['Choose a fighter', {mode: 'retail-edit', start: 'new'}, true], ['Open project', {mode: 'retail-edit', start: 'open'}]],
    note: retailNote}]},
];

function retailNote(s) {
  if (!s.setup.runtime) return 'Needs a game version. Use Game setup, top right.';
  return s.setup.runtime.features.retail ? '' : 'Your game version can’t do this yet: it needs the retail studio. See Game setup.';
}

async function go(target) {
  const result = await act('open_workflow', target, 'Opening…');
  if (result === false) toast('Staying on Home.');
}

function make(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function render() {
  const chip = setup.chip(state.setup);
  $('setup-open').textContent = chip.text;
  $('setup-open').className = 'chip ' + chip.state;
  const groups = GROUPS.map(group => {
    const section = make('section', 'home-section');
    section.append(make('div', 'home-group', group.title));
    const row = make('div', 'home-cards');
    for (const card of group.cards) {
      const element = make('div', 'home-card');
      element.append(make('h3', '', card.name), make('p', '', card.about));
      const buttons = make('div', 'home-buttons');
      for (const [label, target, primary] of card.buttons) {
        const button = make('button', primary ? 'primary' : '', label);
        button.onclick = () => go(target);
        buttons.append(button);
      }
      element.append(buttons);
      const note = card.note(state);
      if (note) element.append(make('span', 'home-need', note));
      row.append(element);
    }
    section.append(row);
    return section;
  });
  $('home-groups').replaceChildren(...groups);
  const recent = state.recents || [];
  $('home-recent').hidden = !recent.length;
  $('home-recent-list').replaceChildren(...recent.map(item => {
    const button = make('button', 'recent-item');
    button.append(make('b', '', item.name), make('small', '', item.mode === 'caf' ? 'Create-a-Fighter project' : item.mode === 'retail-new' ? 'Retail-fighter project' : 'Retail fighter edit'));
    button.title = item.path;
    button.onclick = () => go({mode: item.mode, start: 'open', path: item.path});
    return button;
  }));
  $('home-version').textContent = 'Offline · nothing leaves this computer · Workshop ' + (state.version || '');
  setup.offer(state.setup);
}

async function refresh() {
  state = await call('home');
  render();
}

new QWebChannel(qt.webChannelTransport, channel => {
  bridge = channel.objects.editor;
  bridge.response.connect(raw => {
    const message = JSON.parse(raw), task = pending.get(message.id);
    if (!task) return;
    pending.delete(message.id);
    if (message.error) task.reject(new Error(message.error)); else task.resolve(message.result);
  });
  refresh().catch(error => toast(error.message || String(error), true));
});
