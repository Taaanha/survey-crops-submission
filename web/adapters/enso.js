/* Adapter: /api/v1/enso-lens answer -> what the El Nino context card draws. Renaming and tidying only.
   All-years vs El Nino-years numbers are the server's, with the count of El Nino years kept beside them.
   A missing number stays null ("not assessed"), never 0. Context only: the server says whether it is used in the ranking. */
(function () {
  'use strict';
  function arr(x) { return Array.isArray(x) ? x : []; }
  function obj(x) { return x && typeof x === 'object' && !Array.isArray(x) ? x : null; }
  function measure(m) { m = obj(m); return m && m.value !== undefined && m.value !== null ? { value: m.value, unit: m.unit || '', src: arr(m.src) } : null; }
  function adapt(json) {
    var j = obj(json), d = j && obj(j.data), prov = {};
    if (!d) return { ok: false, errors: arr(j && j.errors), notices: [], provenance: {}, rows: [] };
    arr(j.provenance).forEach(function (p) { if (p && p.id) prov[p.id] = p; });
    var cur = obj(d.current_enso), yrs = obj(d.el_nino_years), nar = obj(j.narration);
    return {
      ok: arr(j.errors).length === 0, errors: arr(j.errors), notices: arr(j.notices), provenance: prov,
      sourceMode: j.source_mode || null, isMock: j.is_mock === true, status: d.status || null,
      phase: cur ? cur.phase || null : null, advisory: cur ? cur.advisory || null : null, nino34: cur ? measure(cur.nino34_latest) : null,
      years: yrs ? { list: arr(yrs.list), src: arr(yrs.src) } : null,
      rows: arr(d.comparison).map(function (r) {
        return { metric: r.metric, all: measure(r.all_years), nino: measure(r.el_nino_years), n: measure(r.n_el_nino), significant: r.significant === true ? true : (r.significant === false ? false : null) };
      }),
      usedInRanking: d.used_in_ranking === true,
      narration: nar ? { en: nar.en, bn: nar.bn, check: nar.provenance_check || null } : null
    };
  }
  window.CS_EN = { adapt: adapt };
})();
