/* Adapter: /api/v1/rotation/strategies answer -> what the Strategies and Evidence pages draw. Renaming and tidying only.
   Each option keeps the server's own sentences (problem line, why suggested, gaps). An indicator the server marked "gap"
   keeps its reason and is never shown as 0. Provenance stays attached to the number it belongs to. */
(function () {
  'use strict';
  function arr(x) { return Array.isArray(x) ? x : []; }
  function obj(x) { return x && typeof x === 'object' && !Array.isArray(x) ? x : null; }
  function m(x) { x = obj(x); return x && x.value !== undefined && x.value !== null ? { value: x.value, unit: x.unit || '', prov: obj(x.provenance) } : null; }
  function option(o) {
    o = obj(o); if (!o) return null;
    var ind = obj(o.indicators) || {}, w = obj(ind.water_use) || {}, py = obj(ind.problem_years) || {}, ng = obj(ind.nitrogen_fixing) || {}, card = obj(o.card) || {},
        mp = obj(ind.market_price) || {}, rot = obj(o.rotation) || {}, bf = obj(ind.bare_field_days) || {}, pc = obj(ind.pest_cycle_break) || {};
    return {
      id: o.id, role: o.role, slots: arr(rot.slots), problemLine: o.problem_line || '', nYears: o.evidence_n_years || null, datasets: arr(o.datasets),
      problem: py.status === 'assessed' ? { count: m(py.count), n: py.n, lo: py.lo, hi: py.hi, level: py.level, checked: arr(py.hazards_checked) } : null,
      waterStatus: w.status || '', waterMedian: m(w.median), waterWorst: m(w.worst20), waterNote: w.note || '',
      legumes: ng.status === 'assessed' ? m(ng.count) : null, bareDays: bf.status === 'assessed' ? m(bf.days_median) : null,
      pest: pc.status === 'assessed' ? { breaks: pc.breaks_cycle === true, families: arr(pc.families), note: pc.note || '' } : null,
      gaps: Object.keys(ind).filter(function (k) { return (obj(ind[k]) || {}).status === 'gap'; }).map(function (k) { return { key: k, reason: ind[k].reason || '' }; }),
      price: mp.status === 'assessed' && m(mp.measure)
        ? { value: mp.measure.value, unit: mp.measure.unit || '', prov: obj(mp.measure.provenance), type: mp.price_type || '', variant: mp.variant || null,
            asOf: mp.as_of || null, market: mp.market || '', mode: mp.source_mode || null, caveat: mp.caveat || '' }
        : (mp.status ? { na: true, reason: mp.reason || '' } : null),
      why: arr(card.why_suggested), evidence: arr(card.evidence), benefits: arr(card.benefits), infoGaps: arr(card.information_gaps), fallow: rot.kharif1 || ''
    };
  }
  function adapt(json) {
    var j = obj(json), d = j && obj(j.data);
    if (!d) return { ok: false, errors: arr(j && j.errors), options: [] };
    var base = option(d.baseline);
    return {
      ok: arr(j.errors).length === 0, errors: arr(j.errors), notices: arr(j.notices), sourceMode: j.source_mode || null, isMock: j.is_mock === true,
      baseline: base, options: arr(d.alternatives).map(option).filter(Boolean),
      notOffered: arr(d.crops_not_offered), assumptions: arr(d.assumptions), pestRule: obj(d.pest_rule)
    };
  }
  window.CS_ST = { adapt: adapt };
})();
