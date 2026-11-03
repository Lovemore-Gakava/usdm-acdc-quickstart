// overlay.js — appended to the hosted application's page by tools/build_site.py.
// Not part of cdisc-org/analysis-concepts. The application's own files are not edited.
//
// Four things, the first three taken from the set-up repository's walkthrough server:
//   1. a '(no filter)' entry on every slice-value dropdown at step 8: the engine treats an empty
//      value as no filter, but the dropdowns offer only the values they found, so a Treatment
//      label can never be cleared and the run fails with "contrasts can be applied only to
//      factors with 2 or more levels".
//   2. the M.MMRM implementation (not upstream's) registered once the application has loaded.
//   3. the mmrm package installed once the WebR engine is up.
//   4. "Load a study definition" at step 1: a USDM JSON from the reader's disk, or from a URL
//      given as ?usdm=<url>. The hosted site carries no study of its own beyond CDISC's sample.
(function () {
  const BASE = location.pathname.slice(0, location.pathname.indexOf('ac-dc-app'));
  const NOFILTER = '__nofilter__';

  function status(msg, ms) {
    let el = document.getElementById('qs-overlay-status');
    if (!el) {
      el = document.createElement('div'); el.id = 'qs-overlay-status';
      el.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:9999;background:#1f2937;color:#fff;padding:8px 12px;border-radius:6px;font:13px system-ui;max-width:460px;box-shadow:0 2px 8px rgba(0,0,0,.3)';
      document.body.appendChild(el);
    }
    el.textContent = msg; el.style.display = 'block';
    if (ms) setTimeout(() => { el.style.display = 'none'; }, ms);
  }

  // ---- 1. '(no filter)' -------------------------------------------------------------------
  function addNoFilter() {
    for (const sel of document.querySelectorAll('select.exec-slice-val-override')) {
      if (!sel.querySelector('option[data-qs="' + NOFILTER + '"]')) {
        const opt = document.createElement('option');
        opt.value = ''; opt.textContent = '(no filter — keep all values)'; opt.dataset.qs = NOFILTER;
        sel.insertBefore(opt, sel.firstChild);
      }
      const st = window.appState, dim = sel.dataset.dim, slice = sel.dataset.slice || 'endpoint';
      const ep = st && (st.currentEndpointId || (st.selectedEndpoints || [])[0]);
      const ov = ep && st.endpointResults && st.endpointResults[ep] && st.endpointResults[ep].sliceOverrides;
      const o = ov && (ov[slice + '|' + dim] || ov['endpoint|' + dim]);
      if (o && o.value === '' && sel.value !== '') sel.value = '';
    }
  }

  // ---- 2 and 3. M.MMRM ----------------------------------------------------------------------
  let registered = false, mmrmInstalled = false, installing = false;
  async function registerMmrm() {
    const st = window.appState;
    if (!st || !st.loaded) return false;
    try {
      st.methodImplementationCatalog = st.methodImplementationCatalog || { implementations: {} };
      st.methodImplementationCatalog.implementations = st.methodImplementationCatalog.implementations || {};
      if (!st.methodImplementationCatalog.implementations['M.MMRM']) {
        const impl = await (await fetch(BASE + 'ac-dc-app/data/overlay/r_impl_mmrm.json')).json();
        st.methodImplementationCatalog.implementations['M.MMRM'] = [impl];
      }
      return true;
    } catch (e) { status('could not register M.MMRM: ' + e, 8000); return true; }
  }
  async function installMmrm() {
    if (mmrmInstalled || installing) return;
    try {
      const eng = await import(BASE + 'ac-dc-app/js/utils/webr-engine.js');
      if (!eng.isInitialized()) return;
      installing = true; status('installing the mmrm package in WebR (about half a minute) …');
      const out = await eng.executeR('webr::install("mmrm"); as.character(requireNamespace("mmrm", quietly = TRUE))');
      const ok = JSON.stringify(out).includes('TRUE');
      mmrmInstalled = ok;
      status(ok ? 'mmrm package installed' : 'mmrm install did not confirm: ' + JSON.stringify(out).slice(0, 120), ok ? 6000 : 0);
    } catch (e) { status('mmrm install failed: ' + e, 0); } finally { installing = false; }
  }

  // ---- 4. Load a study definition -----------------------------------------------------------
  async function addStudy(json, name) {
    const [{ parseUSDM }, app] = await Promise.all([
      import(BASE + 'ac-dc-app/js/utils/usdm-parser.js'),
      import(BASE + 'ac-dc-app/js/app.js'),
    ]);
    const st = app.appState;
    const parsed = parseUSDM(json);                    // throws on a file the application cannot read
    parsed.isSoaEnriched = (parsed.biomedicalConcepts || []).some(bc => bc.sdtmSpec != null);
    st.rawUsdmFiles.push(json);
    st.studyManifest = (st.studyManifest || []).concat([{ file: name }]);
    st.studies.push(parsed);
    app.renderCurrentStep();
    status('Loaded ' + name + ' — it is the last card. Click it to continue.', 8000);
  }

  function loadFromFile(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try { addStudy(JSON.parse(reader.result), file.name); }
      catch (e) { status('Could not load ' + file.name + ': ' + (e && e.message ? e.message : e), 0); }
    };
    reader.onerror = () => status('Could not read ' + file.name, 0);
    reader.readAsText(file);
  }

  async function loadFromUrl(url) {
    try {
      status('Fetching ' + url + ' …');
      const resp = await fetch(url);
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      await addStudy(await resp.json(), url.split('/').pop() || url);
    } catch (e) { status('Could not load ' + url + ': ' + (e && e.message ? e.message : e), 0); }
  }

  function addLoader() {
    const grid = document.querySelector('.study-grid');
    if (!grid || document.getElementById('qs-load-bar')) return;
    const bar = document.createElement('div');
    bar.id = 'qs-load-bar';
    bar.style.cssText = 'margin:0 0 20px;padding:14px 16px;border:1px dashed #9ca3af;border-radius:8px;background:#f9fafb;font:14px system-ui;color:#1f2937;display:flex;gap:12px;align-items:center;flex-wrap:wrap';
    bar.innerHTML =
      '<strong>Bring your own study.</strong> ' +
      '<span>A USDM v4 study definition as JSON, in the shape this application reads.</span> ' +
      '<button type="button" id="qs-load-btn" style="padding:6px 12px;border:1px solid #1d4ed8;border-radius:6px;background:#1d4ed8;color:#fff;font:inherit;cursor:pointer">Load a study definition…</button>' +
      '<input type="file" id="qs-load-input" accept=".json,application/json" style="display:none">' +
      '<span style="flex-basis:100%;font-size:12px;color:#6b7280">Nothing leaves your browser. Datasets (.xpt) are uploaded at step 8 the same way. ' +
      'The shape the parser expects is documented in the set-up repository, <code>study/usdm/README.md</code>.</span>';
    grid.parentNode.insertBefore(bar, grid);
    const input = bar.querySelector('#qs-load-input');
    bar.querySelector('#qs-load-btn').addEventListener('click', () => input.click());
    input.addEventListener('change', () => { if (input.files && input.files[0]) loadFromFile(input.files[0]); input.value = ''; });
  }

  let urlLoaded = false;
  function maybeLoadFromQuery() {
    if (urlLoaded) return;
    const st = window.appState;
    if (!st || !st.loaded) return;
    urlLoaded = true;
    const u = new URLSearchParams(location.search).get('usdm');
    if (u) loadFromUrl(u);
  }

  new MutationObserver(() => { addNoFilter(); addLoader(); }).observe(document.documentElement, { childList: true, subtree: true });
  addNoFilter(); addLoader();
  setInterval(async () => {
    if (!registered) registered = await registerMmrm();
    if (!mmrmInstalled) installMmrm();
    maybeLoadFromQuery();
  }, 1500);
})();
