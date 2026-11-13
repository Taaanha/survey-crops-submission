/* Adapter: /api/v1/post-flood answer -> what the flood section draws.
   Only renaming and tidying. No maths: every date, day count, percentage and ranking comes from the server.
   Tolerant: a missing part becomes null / [] and the page leaves that part out.
   Measures keep {value, unit, src}; bilingual text stays {en, bn}.
   Needs adapters/advisory.js loaded first (the crop cards in still_possible have the same shape). */
(function () {
  'use strict';
  function arr(x) { return Array.isArray(x) ? x : []; }
  function obj(x) { return x && typeof x === 'object' && !Array.isArray(x) ? x : null; }
  function measure(m) { m = obj(m); return m && m.value !== undefined && m.value !== null ? { value: m.value, unit: m.unit || '', src: arr(m.src) } : null; }
  function dated(d, basis) { d = obj(d); return d && d.date ? { date: d.date, basis: obj(d.basis), src: arr(d.src) } : null; }

  function cascadeRow(r) {
    r = obj(r) || {};
    function leg(x) { x = obj(x); return x ? { sow: x.sowing_date || null, problem: measure(x.problem_years) } : null; }
    return { id: r.crop || '', name: obj(r.crop_name) || { en: r.crop || '', bn: r.crop || '' },
             readyAtOnce: leg(r.if_ready_at_once), afterFlood: leg(r.after_flood),
             change: obj(r.change), coverageNotice: obj(r.coverage_notice) };
  }

  function adapt(json) {
    var j = obj(json);
    if (!j) return { ok: false, errors: [], notices: [], provenance: {}, still: [], gone: [], cascade: [], images: [] };
    var d = obj(j.data), prov = {};
    arr(j.provenance).forEach(function (p) { if (p && p.id) prov[p.id] = p; });
    var ad = window.CS_AD ? window.CS_AD.adapt({ data: { options: d ? d.still_possible : [], filtered_out: d ? d.no_longer_possible : [] } }) : { options: [], filtered: [] };
    var w = d && obj(d.water_on_ground), s = d && obj(d.soil_back_to_normal);
    return {
      ok: !!d && arr(j.errors).length === 0,
      errors: arr(j.errors), sourceMode: j.source_mode || null, isMock: j.is_mock === true,
      notices: arr(j.notices), provenance: prov,
      floodDate: d && d.flood_date || null,
      district: d && d.district || null,
      location: d && obj(d.location),
      narration: obj(j.narration) ? { en: j.narration.en, bn: j.narration.bn, narrator: j.narration.narrator || null, check: j.narration.provenance_check || null } : null,
      earliest: d ? dated(d.earliest_sowing_date) : null,
      water: w ? {
        available: w.available === true, conclusive: w.conclusive === true,
        peakDate: w.peak_date || null, goneDate: w.water_gone_date || null,
        peakShare: measure(w.peak_flood_share), peakArea: measure(w.peak_flood_area),
        floor: measure(w.dry_season_floor), daysToGone: measure(w.days_peak_to_gone), scenes: measure(w.scenes_used),
        rule: obj(w.rule), resolutionNote: obj(w.resolution_note),
        curve: w.curve ? { src: arr(w.curve.src), rows: arr(w.curve.rows) } : null   // rows: {date, flood_pct, flood_km2, used}
      } : null,
      soil: s ? {
        date: s.date || null, days: measure(s.days_after_flood), rule: obj(s.rule),
        sensitivity: arr(s.sensitivity).map(function (x) { return { pct: x.pct, date: x.date, days: measure(x.days_after_flood) }; }),
        curve: s.curve ? { src: arr(s.curve.src), rows: arr(s.curve.rows) } : null    // rows: {date, value, threshold}
      } : null,
      still: ad.options,                // crop cards, same shape as the Rotation page cards
      gone: ad.filtered,                // crops that are no longer possible (may be empty)
      cascade: d && d.cascade ? arr(d.cascade.rows).map(cascadeRow) : [],
      cascadeNote: d && d.cascade ? obj(d.cascade.compares) : null,
      cascadeSrc: d && d.cascade ? arr(d.cascade.src) : [],
      images: d ? arr(d.flood_images).map(function (i) { return { date: i.date, path: i.path, src: arr(i.src), caption: obj(i.caption) }; }) : [],
      soilTest: d && obj(d.soil_test_advice)
    };
  }

  function sources(adapted, ids) {
    return arr(ids).map(function (id) { return adapted.provenance[id]; }).filter(Boolean);
  }
  window.CS_PF = { adapt: adapt, sources: sources };
})();
