/* Survey Crops API client (modes.html). It only asks the server and hands back the answer.
   No maths, no ranking, no dates: that all stays in the backend.

   CS_API.get(path) / CS_API.post(path, body) return a Promise that ALWAYS resolves (never rejects):
     { ok, source, data, ms, status, error, path }
       source "live"   - the server answered (data is its JSON, which may itself carry errors[])
       source "sample" - the server could not be reached, data is a saved sample from web/mock/live/
       source "error"  - neither worked; data is null. Show a friendly message, never `error`.
   `error` holds the technical reason for the Officer view only.

   Rules: 60 s timeout per try, one automatic retry (the free server may be waking up),
   then the saved sample. CS_API.on(fn) tells the page what is happening so it can show
   "waking up the server" and a clear failure message. CS_API.log has one entry per endpoint
   (ok / failed / slow, last response time) for the Server page. */
(function () {
  'use strict';
  var TIMEOUT_MS = 60000, SLOW_MS = 5000, WAKING_AFTER_MS = 6000, RETRIES = 1;
  // Only answers that are real, successful samples. Error samples (map layers) are not used.
  var SAMPLES = ['districts', 'advisory', 'soil', 'risk_calendar', 'post_flood', 'field_twin',
                 'rotation_rank', 'enso_lens', 'warnings', 'ask', 'map_scenario', 'data_sources', 'models'];
  var listeners = [], log = {}, pending = 0, provMap = {};
  function addProv(json) {
    if (!json || json.is_mock === true || !Array.isArray(json.provenance)) return;
    json.provenance.forEach(function (p) {
      if (!p || !(p.dataset || p.id)) return;
      var k = (p.dataset || '') + '|' + (p.url || p.source_url || '');
      if (!provMap[k]) provMap[k] = p;
    });
  }

  function base() { return String(window.API_BASE || '').replace(/\/$/, ''); }
  function emit(ev) { listeners.forEach(function (f) { try { f(ev); } catch (e) { /* page bug must not stop the client */ } }); }
  function endpointKey(path) { return path.split('?')[0].replace('/api/v1/', '/'); }
  function sampleName(path) {
    var n = endpointKey(path).replace(/^\//, '').replace(/[\/-]/g, '_');
    return SAMPLES.indexOf(n) >= 0 ? n : null;
  }

  function once(method, path, body) {
    var ctl = new AbortController(), timer = setTimeout(function () { ctl.abort(); }, TIMEOUT_MS);
    var opts = { method: method, signal: ctl.signal };
    if (body !== undefined) { opts.headers = { 'Content-Type': 'application/json' }; opts.body = JSON.stringify(body); }
    return fetch(base() + path, opts).then(function (r) {
      clearTimeout(timer);
      return r.text().then(function (t) {
        var j = null; try { j = JSON.parse(t); } catch (e) { /* not JSON */ }
        // 502/503/504 = the free server is still waking; 5xx with a JSON envelope = a server fault.
        if (r.status >= 500 || j === null) { var err = new Error('HTTP ' + r.status); err.retry = true; throw err; }
        return { json: j, status: r.status };   // 2xx and 4xx are answers (4xx carries errors[] for the page)
      });
    }, function (e) {
      clearTimeout(timer);
      var err = new Error(e && e.name === 'AbortError' ? 'timeout after ' + (TIMEOUT_MS / 1000) + ' s' : 'network: ' + (e && e.message));
      err.retry = true; throw err;
    });
  }

  function sample(path) {
    var n = sampleName(path);
    if (!n) return Promise.resolve(null);
    return fetch((window.API_SAMPLES || 'mock/live/') + n + '.json').then(function (r) {
      return r.ok ? r.json() : null;
    }).catch(function () { return null; });
  }

  function request(method, path, body) {
    var t0 = Date.now(), tries = 0, wakeTimer;
    pending++; emit({ type: 'start', path: path, pending: pending });
    wakeTimer = setTimeout(function () { emit({ type: 'waking', path: path }); }, WAKING_AFTER_MS);

    function finish(res) {
      clearTimeout(wakeTimer); pending--;
      var ms = Date.now() - t0, k = endpointKey(path);
      log[k] = { path: path, method: method, state: res.source === 'live' ? (ms > SLOW_MS ? 'slow' : 'ok') : 'failed',
                 ms: ms, source: res.source, error: res.error || null, at: new Date().toISOString(), json: res.data };
      res.ms = ms; res.path = path; addProv(res.data);
      emit({ type: 'end', path: path, source: res.source, ms: ms, pending: pending });
      return res;
    }

    function attempt() {
      tries++;
      return once(method, path, body).then(function (r) {
        return finish({ ok: true, source: 'live', data: r.json, status: r.status, error: null });
      }, function (err) {
        if (err.retry && tries <= RETRIES) { emit({ type: 'retry', path: path, tries: tries }); return attempt(); }
        return sample(path).then(function (s) {
          if (s) return finish({ ok: true, source: 'sample', data: s, status: 0, error: err.message });
          return finish({ ok: false, source: 'error', data: null, status: 0, error: err.message });
        });
      });
    }
    return attempt();
  }

  window.CS_API = {
    get: function (path) { return request('GET', path); },
    post: function (path, body) { return request('POST', path, body === undefined ? {} : body); },
    on: function (fn) { listeners.push(fn); },
    log: log,
    prov: function () { return Object.keys(provMap).map(function (k) { return provMap[k]; }); },
    pending: function () { return pending; },
    /* true only when the server answered for real AND the answer is not marked as example data */
    isLive: function (res) {
      return !!(res && res.source === 'live' && res.data && res.data.is_mock !== true &&
                !(res.data.errors && res.data.errors.length));
    }
  };
})();
