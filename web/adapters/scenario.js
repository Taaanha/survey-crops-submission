/* Adapter: /api/v1/map/scenario answer -> the what-if table. Renaming only.
   baseline / scenario / delta are all computed by the server over the past seasons it lists. */
(function () {
  'use strict';
  function arr(x) { return Array.isArray(x) ? x : []; }
  function obj(x) { return x && typeof x === 'object' && !Array.isArray(x) ? x : null; }
  var KEYS = ['irrigation_mm_mean', 'irrigation_mm_worst20', 'water_stress_days_mean', 'rain_mm_mean', 'etc_mm_mean'];
  function adapt(json) {
    var j = obj(json), d = j && obj(j.data);
    if (!d) return { ok: false, errors: arr(j && j.errors), rows: [] };
    var b = obj(d.baseline) || {}, sc = obj(d.scenario) || {}, de = obj(d.delta) || {};
    return {
      ok: arr(j.errors).length === 0, errors: arr(j.errors), notices: arr(j.notices), label: d.label || null,
      inputs: obj(d.inputs), ranges: obj(d.ranges), nYears: b.n_years || null, years: arr(b.years),
      rows: KEYS.filter(function (k) { return b[k] !== undefined; }).map(function (k) { return { key: k, base: b[k], what: sc[k], delta: de[k] }; }),
      heat: arr(b.heat).map(function (h, i) {
        var s2 = arr(sc.heat)[i] || {}, hd = obj(de.heat_mean_days) || {}; return { item: h.item, limit: h.limit, unit: h.unit, base: h.mean_days, what: s2.mean_days, delta: hd[h.item], url: h.source_url, title: h.source_title };
      }),
      assumptions: arr(d.assumptions), sources: arr(d.provenance)   // [{dataset, source_url}]
    };
  }
  window.CS_SC = { adapt: adapt };
})();
