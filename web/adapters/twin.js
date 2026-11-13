/* Adapter: /api/v1/field-twin answer -> what the season replay draws.
   Only renaming and tidying. Every weekly value, flag and total comes from the server.
   Tolerant: missing parts become null / [] and the page leaves them out. A replay of ONE PAST YEAR, not a forecast. */
(function () {
  'use strict';
  function arr(x) { return Array.isArray(x) ? x : []; }
  function obj(x) { return x && typeof x === 'object' && !Array.isArray(x) ? x : null; }
  function measure(m) { m = obj(m); return m && m.value !== undefined && m.value !== null ? { value: m.value, unit: m.unit || '', src: arr(m.src) } : null; }

  function adapt(json) {
    var j = obj(json);
    if (!j) return { ok: false, errors: [], notices: [], provenance: {}, rows: [], thresholds: [] };
    var d = obj(j.data), prov = {};
    arr(j.provenance).forEach(function (p) { if (p && p.id) prov[p.id] = p; });
    var w = d && obj(d.weekly), rule = w && obj(w.events_rule), t = d && obj(d.totals), sm = d && obj(d.smap_check);
    return {
      ok: !!d && arr(j.errors).length === 0, errors: arr(j.errors), notices: arr(j.notices), provenance: prov,
      sourceMode: j.source_mode || null, isMock: j.is_mock === true,
      crop: d && d.crop || null, cropName: d && obj(d.crop_name), year: d && d.year || null,
      sow: d && d.sow_date || null, end: d && d.season_end || null,
      label: d && obj(d.label),                                  // "What happened in YEAR ... An example, not a forecast."
      isForecast: d ? d.is_forecast === true : false,
      units: w && obj(w.units) || {},
      rows: w ? arr(w.rows).map(function (r) {
        return { week: r.week_start, days: r.days, stage: r.stage, rain: r.rain_mm, et0: r.et0_mm, demand: r.crop_demand_mm,
                 tmax: r.tmax_mean_c, tmaxHi: r.tmax_highest_c, tmin: r.tmin_mean_c, soil: r.soil_water_pct,
                 stress: r.stress_days, irr: r.irrigation_mm, irrEvents: r.irrigation_events, smap: r.smap_rootzone_m3m3,
                 events: arr(r.events) };
      }) : [],
      thresholds: rule ? arr(rule.thresholds).map(function (x) {
        return { event: x.event, label: obj(x.label), stage: x.stage, limit: measure(x.limit), span: arr(x.span) };
      }) : [],
      totals: t ? {
        irrNeed: measure(t.irrigation_need), irrEvents: measure(t.irrigation_events), stress: measure(t.stress_days),
        rain: measure(t.rain), demand: measure(t.crop_water_demand)
      } : null,
      smapNote: sm && sm.available ? obj(sm.note) : null,
      location: d && obj(d.location)
    };
  }
  window.CS_TW = { adapt: adapt };
})();
