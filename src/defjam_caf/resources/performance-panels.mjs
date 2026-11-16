// Shared authoring panels for standalone CAF and retail projects.
const markup = `<section id="tab-voice" class="tab-content" hidden="" role="tabpanel" aria-labelledby="section-voice">
            <div class="panel-title">
              <h3>Give your fighter a voice.</h3>
              <p>Independent of fighting style. Fighter projects only.</p>
            </div>
            <button id="performance-connect">Reload voice &amp; animation catalogs</button>
            <p id="performance-status" class="hint"></p>
            <label>Retail voice preset<select id="voice-preset"></select></label>
            <details>
              <summary>Category bank overrides</summary>
              <label>Character<select id="voice-bank-Character"></select></label><label>Taunts<select id="voice-bank-Taunts"></select></label><label>Environment<select id="voice-bank-Enviro"></select></label>
            </details>
            <div class="two-cols">
              <button id="voice-apply">Stage voice settings</button><button id="voice-inherit">Inherit donor voice</button>
            </div>
            <p class="hint">
              Stage the preset before importing clips. Existing clip overrides are retained and validated against the
              selected bank. Clear incompatible overrides before switching banks.
            </p>
            <label>Category<select id="voice-category">
                <option>Character</option>
                <option>Taunts</option>
                <option>Enviro</option>
              </select></label><label>Event slot<select id="voice-slot"></select></label>
            <div class="two-cols">
              <button id="voice-play">Audition original</button><button id="voice-play-imported">Audition imported</button>
            </div>
            <audio id="voice-audio" controls="" preload="none"></audio>
            <div class="two-cols">
              <button id="voice-previous">Previous clip</button><button id="voice-next">Next clip</button>
            </div>
            <label class="hint"><input id="voice-auto" type="checkbox" checked=""> Play when selecting a clip</label>
            <button id="voice-save" disabled="">Save WAV…</button>
            <p id="voice-preload-status" class="hint" role="status"></p>
            <p id="voice-clip-status" class="hint"></p>
            <div class="two-cols">
              <button id="voice-import">Import WAV</button><button id="voice-clear-clip">Clear clip override</button>
            </div>
            <p class="hint">
              Mono PCM16 WAV, 8–48 kHz, at most 8 MiB each. Events are numbered until their names are verified.
              Entrance/victory audition uses the first available original stream; edited banks export that stream as the
              default unless you import a replacement.
            </p>
          </section>
<section id="tab-presentation" class="tab-content" hidden="" role="tabpanel" aria-labelledby="section-presentation">
            <div class="panel-title">
              <h3>Entrance &amp; victory.</h3>
              <p>
                Choose the original sequences your fighter uses. Catalogs load automatically when this tab opens.
                Previews play in the 3D viewer.
              </p>
            </div>
            <p id="tab-presentation-status" class="hint" role="status"></p>
            <button class="quiet" data-performance-retry="">Retry loading catalogs</button>
            <label>Entrance<select id="sequence-intro"></select></label>
            <div class="two-cols">
              <button id="preview-intro">Preview entrance</button><button id="apply-intro">Stage entrance</button>
            </div>
            <label>Victory<select id="sequence-victory"></select></label>
            <div class="two-cols">
              <button id="preview-victory">Preview victory</button><button id="apply-victory">Stage victory</button>
            </div>
            <div class="rule"></div>
            <details>
              <summary>Advanced · source clip viewer (saves nothing)</summary>
              <label>Retail animation bank<select id="animation-bank"></select></label><button id="animation-list">Browse original clips</button><label>Original clip token<select id="animation-clip"></select></label><button id="animation-load">Load clip in 3D viewer</button>
              <div class="two-cols">
                <button id="animation-play">Play</button><button id="animation-stop">Stop / restore pose</button>
              </div>
              <label>Timeline<input id="animation-time" type="range" min="0" max="1" value="0" step="0.1"></label><output id="animation-clock">0.00 s</output>
              <div class="two-cols">
                <label>Speed<select id="animation-speed">
                    <option value="0.25">0.25×</option>
                    <option value="0.5">0.5×</option>
                    <option value="1" selected="">1×</option>
                    <option value="2">2×</option>
                  </select></label><label class="switch"><input id="animation-loop" type="checkbox" checked=""> Loop</label>
              </div>
              <p id="animation-status" class="hint">
                Decoded source body/root tracks at 30 source ticks/s. Preview does not reproduce cameras, face/hand
                palettes, events or runtime blending. Unsupported codecs are reported. Playback does not edit or save
                the fighter.
              </p>
            </details>
          </section>
<section id="tab-ai" class="tab-content" hidden="" role="tabpanel" aria-labelledby="section-ai">
            <div class="panel-title">
              <h3>Shape the CPU opponent.</h3>
              <p>Retail personality plus per-difficulty tendency overrides.</p>
            </div>
            <p id="tab-ai-status" class="hint" role="status"></p>
            <button class="quiet" data-performance-retry="">Retry loading catalogs</button>
            <label>Original AI preset<select id="ai-preset"></select></label>
            <div class="two-cols">
              <label>Difficulty<select id="ai-difficulty">
                  <option>easy</option>
                  <option selected="">normal</option>
                  <option>hard</option>
                </select></label><label>Tendency slot<select id="ai-slot">
                  <option value="0">1</option>
                  <option value="1">2</option>
                  <option value="2">3</option>
                  <option value="3">4</option>
                </select></label>
            </div>
            <p class="hint">
              Check a field to override it with 1–5. Unchecked fields retain exact original values. Slots retain their
              original selection rules; they are not named combat phases. Changing the preset resets unstaged slider
              edits.
            </p>
            <div id="ai-sliders"></div>
            <div class="two-cols">
              <button id="ai-apply">Stage AI personality</button><button id="ai-inherit">Inherit donor AI</button>
            </div>
          </section>`;
export function mountPerformancePanels(placeholder, { retail = false } = {}) {
  const template = document.createElement("template");
  template.innerHTML = markup;
  if (retail)
    for (const panel of template.content.querySelectorAll(".tab-content")) {
      const name = panel.id.replace("tab-", "");
      panel.dataset.content = name;
      panel.setAttribute("aria-labelledby", "retail-tab-" + name);
    }
  placeholder.replaceWith(template.content);
}
