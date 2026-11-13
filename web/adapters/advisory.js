/* Adapter: /api/v1/advisory answer -> what the Rotation page draws.
   Only renaming and tidying. No maths, no ranking, no dates worked out here: the server did all that.
   Tolerant: any missing field becomes null / [] and the page simply leaves that line out.
   Bilingual fields stay {en, bn}. Every measure keeps {value, unit, src} so its source can be opened. */
(function () {
  'use strict';
  function arr(x) { return Array.isArray(x) ? x : []; }
  function obj(x) { return x && typeof x === 'object' && !Array.isArray(x) ? x : null; }
  function measure(m) { m = obj(m); return m && m.value !== undefined && m.value !== null ? { value: m.value, unit: m.unit || '', src: arr(m.src) } : null; }
  function dateOf(d) { d = obj(d); return d && d.date ? { date: d.date, src: arr(d.src) } : null; }

  // additive: a cited price (a price, not income) with its month, or "not assessed"; never 0
  function price(p) {
    p = obj(p); if (!p) return null;
    var v = obj(p.price);
    if (p.status !== 'assessed' || !v || v.value === undefined || v.value === null) return { na: true, reason: p.reason || '' };
    var pr = obj(p.past_range) || {};
    return { value: v.value, unit: v.unit || '', src: arr(v.src), type: p.price_type || '', variant: p.variant || null, asOf: p.as_of || null,
             market: p.market || '', label: obj(p.label), mode: p.source_mode || null, pastReason: pr.reason || '', caveat: p.caveat || '' };
  }

  function card(o) {
    o = obj(o) || {};
    var missing = arr(o.hazards_missing);
    return {
      id: o.crop || '',
      rank: o.rank == null ? null : o.rank,
      name: obj(o.crop_name) || { en: o.crop || '', bn: o.crop || '' },
      feasible: o.feasible !== false,
      sow: dateOf(o.sowing_date),
      window: obj(o.sowing_window) ? { start: o.sowing_window.start, end: o.sowing_window.end, src: arr(o.sowing_window.src) } : null,
      status: obj(o.window_status),                       // {code, en, bn}
      problem: measure(o.problem_years),                  // {value, unit:"of 24 years", src}
      problemLine: obj(o.problem_line),
      checked: arr(o.hazards_checked).map(function (h) {
        return { id: h.hazard, label: obj(h.label), years: measure(h.years_hit) };
      }),
      checkedText: obj(o.hazards_checked_text),
      missing: missing,
      coverageNotice: obj(o.coverage_notice),
      // "not all risks are checked" whenever the server names missing hazards or sends a coverage notice
      partial: missing.length > 0 || !!obj(o.coverage_notice),
      mainRisks: arr(o.main_risks),
      irrAvg: measure(o.irrigation_need_avg),
      irrWorst: measure(o.irrigation_need_worst20),
      eventsAvg: measure(o.irrigation_events_avg),
      eventsWorst: measure(o.irrigation_events_worst20),
      stressAvg: measure(o.water_stress_days_avg),
      stressWorst: measure(o.water_stress_days_worst20),
      maturity: dateOf(o.maturity_date),
      price: price(o.market_price),
      why: obj(o.why),
      waterNote: obj(o.water_note),
      reason: obj(o.reason),                              // only on filtered_out rows
      reasonCode: o.reason_code || null
    };
  }

  function adapt(json) {
    var j = obj(json);
    if (!j) return { ok: false, errors: [], options: [], filtered: [], notices: [], provenance: {} };
    var d = obj(j.data), prov = {};
    arr(j.provenance).forEach(function (p) { if (p && p.id) prov[p.id] = p; });
    return {
      ok: !!d && arr(j.errors).length === 0,
      errors: arr(j.errors),                              // [{code, en, bn}] shown as is
      district: d && d.district || null,
      location: d && obj(d.location),
      narration: obj(j.narration) ? { en: j.narration.en, bn: j.narration.bn, narrator: j.narration.narrator || null, check: j.narration.provenance_check || null } : null,
      sourceMode: j.source_mode || null,                  // live | cache | fixture
      isMock: j.is_mock === true,
      rankedBy: d && obj(d.ranked_by) ? { text: obj(d.ranked_by.text), keys: arr(d.ranked_by.keys) } : null,
      earliest: d && obj(d.earliest_sowing_date) ? { date: d.earliest_sowing_date.date, basis: obj(d.earliest_sowing_date.basis), src: arr(d.earliest_sowing_date.src) } : null,
      method: d && obj(d.method) || null,
      yearsUsed: d && d.years_used != null ? d.years_used : null,
      options: d ? arr(d.options).map(card) : [],
      filtered: d ? arr(d.filtered_out).map(card) : [],
      notices: arr(j.notices),                            // [{level, en, bn}] always shown
      provenance: prov                                    // id -> {dataset, url, period, resolution, ...}
    };
  }

  // Source entries behind a list of src ids (unknown ids are skipped, never invented).
  function sources(adapted, ids) {
    return arr(ids).map(function (id) { return adapted.provenance[id]; }).filter(Boolean);
  }

  window.CS_AD = { adapt: adapt, sources: sources };
})();
