/* Adapter: /api/v1/risk-calendar answer -> what the sowing-date calendar draws.
   Renaming and tidying only. Counts, windows and water numbers are the server's, over the past seasons it names.
   A null in the grid means "not assessed for that date" and stays null: it is never turned into 0.
   Tolerant: a missing part becomes null / [] and the page leaves it out. */
(function () {
  'use strict';
  function arr(x) { return Array.isArray(x) ? x : []; }
  function obj(x) { return x && typeof x === 'object' && !Array.isArray(x) ? x : null; }
  function measure(m) { m = obj(m); return m && m.value !== undefined && m.value !== null ? { value: m.value, unit: m.unit || '', src: arr(m.src) } : null; }

  function adapt(json) {
    var j = obj(json);
    if (!j) return { ok: false, errors: [], notices: [], provenance: {}, dates: [], hazards: [], grid: [] };
    var d = obj(j.data), prov = {};
    arr(j.provenance).forEach(function (p) { if (p && p.id) prov[p.id] = p; });
    var hz = {};
    if (d) arr(d.hazards).forEach(function (h) { hz[h.id] = { id: h.id, label: obj(h.label), threshold: measure(h.threshold) }; });
    var g = d && obj(d.grid), w = d && obj(d.water), sn = d && obj(d.sensitivity), rw = d && obj(d.recommended_window), nar = obj(j.narration);
    return {
      ok: !!d && arr(j.errors).length === 0, errors: arr(j.errors), notices: arr(j.notices), provenance: prov,
      sourceMode: j.source_mode || null, isMock: j.is_mock === true,
      crop: d && d.crop || null, cropName: d && obj(d.crop_name), years: d ? measure(d.years_used) : null,
      window: rw ? { start: rw.start, end: rw.end, method: rw.method || null, src: arr(rw.src) } : null,   // MM-DD
      dates: d ? arr(d.sowing_dates) : [],                    // "MM-DD", the same day in every season
      hazards: hz,
      grid: g ? arr(g.rows).map(function (r) { return { id: r.hazard, hit: arr(r.years_hit) }; }) : [],
      gridUnit: g && g.unit || '', gridSrc: g ? arr(g.src) : [],
      checkedText: d && obj(d.hazards_checked_text), missing: d ? arr(d.hazards_missing) : [], coverageNotice: d && obj(d.coverage_notice),
      water: w ? { src: arr(w.src), rows: [['irrigation_mm_mean', w.irrigation_mm_mean], ['irrigation_mm_worst20', w.irrigation_mm_worst20],
                                           ['stress_days_mean', w.stress_days_mean], ['stress_days_worst20', w.stress_days_worst20]]
                     .map(function (x) { return { key: x[0], values: arr(x[1]), unit: (obj(w.units) || {})[x[0]] || '' }; }) } : null,
      sens: sn ? { unit: sn.unit || '', src: arr(sn.src), rows: arr(sn.rows).map(function (r) { return { id: r.id, label: obj(r.label), values: arr(r.any_problem_years) }; }) } : null,
      disease: d ? arr(d.disease_risks).map(function (x) {   // additive: disease-favourable weather counts, or "not assessed" + reason
        var w = obj(x.window);
        return { crop: x.crop || null, status: x.status || 'not_assessed', label: obj(x.disease_label), reason: x.reason || '', text: obj(x.text), meaning: obj(x.meaning),
                 fav: measure(x.seasons_favourable), n: measure(x.seasons_counted), run: measure(x.min_run_days),
                 windowText: w ? obj(w.text) : null, windowNote: w ? obj(w.note) : null,
                 rule: arr(x.rule).map(function (r) { return { label: r.label || '', value: r.value, unit: r.unit || '' }; }) };
      }) : [],
      narration: nar ? { en: nar.en, bn: nar.bn, narrator: nar.narrator || null, check: nar.provenance_check || null } : null
    };
  }
  window.CS_RK = { adapt: adapt };
})();
