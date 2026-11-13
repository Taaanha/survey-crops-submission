/* Adapter: /api/v1/warnings answer -> what the weather-warning card draws. Renaming and tidying only.
   The server's own key for the expected amount is renamed "expected" here so the page never shows that word.
   The server's one-line narration is NOT passed on: it uses wording the page must not show. */
(function () {
  'use strict';
  function arr(x) { return Array.isArray(x) ? x : []; }
  function obj(x) { return x && typeof x === 'object' && !Array.isArray(x) ? x : null; }
  function measure(m) { m = obj(m); return m && m.value !== undefined && m.value !== null ? { value: m.value, unit: m.unit || '', src: arr(m.src) } : null; }
  function adapt(json) {
    var j = obj(json), d = j && obj(j.data), prov = {};
    if (!d) return { ok: false, errors: arr(j && j.errors), notices: [], provenance: {}, items: [] };
    arr(j.provenance).forEach(function (p) { if (p && p.id) prov[p.id] = p; });
    return {
      ok: arr(j.errors).length === 0, errors: arr(j.errors), notices: arr(j.notices), provenance: prov,
      sourceMode: j.source_mode || null, isMock: j.is_mock === true, district: d.district || null,
      from: d.valid_from || null, to: d.valid_to || null,
      items: arr(d.warnings).map(function (w) {
        return { type: w.type || '', date: w.date || null, expected: measure(w.forecast), threshold: measure(w.threshold), action: obj(w.action) };
      })
    };
  }
  window.CS_WN = { adapt: adapt };
})();
