/* Adapter: /api/v1/models answer -> what the Model page draws. Renaming and tidying only.
   Every number keeps its interval and sample size exactly as the server returned it; nothing is rounded or averaged here.
   The server's own "which method is used and why" sentences are kept as written. */
(function () {
  'use strict';
  function arr(x) { return Array.isArray(x) ? x : []; }
  function obj(x) { return x && typeof x === 'object' && !Array.isArray(x) ? x : null; }
  function ci(x) { x = obj(x); return x && x.value !== undefined && x.value !== null ? { value: x.value, lo: x.lo, hi: x.hi, n: x.n, level: x.level } : null; }
  function block(x) {
    x = obj(x); if (!x) return null;
    var a = obj(x.method_a) || {}, b = obj(x.method_b) || {};
    return { use: x.use || null, reason: x.reason || '', caveat: x.caveat || '', years: arr(x.years), features: arr(x.features), n: x.n_district_seasons_assessed || x.n_district_seasons || null,
             sources: arr(x.sources).map(function (s) { return { name: s.dataset, url: s.source_url || s.url }; }),
             rows: [['hit_rate_a', 'Events caught, method A', ci(a.hit_rate)], ['hit_rate_b', 'Events caught, method B', ci(b.hit_rate)],
                    ['outside_a', 'Flagged outside the listed events, method A', ci(a.outside_rate)], ['outside_b', 'Flagged outside the listed events, method B', ci(b.outside_rate)],
                    ['agree', 'Two methods agree', ci(x.agreement)], ['hit_diff', 'Events caught, B minus A', ci(x.hit_rate_b_minus_a)], ['out_diff', 'Flagged outside, B minus A', ci(x.outside_rate_b_minus_a)],
                    ['sil', 'Season-type separation (held-out silhouette), B minus A', ci(x.silhouette_b_minus_a)], ['stab', 'Season-type stability, B minus A', ci(x.stability_b_minus_a)]]
               .filter(function (r) { return r[2]; }).map(function (r) { return { key: r[0], label: r[1], v: r[2] }; }) };
  }
  function adapt(json) {
    var j = obj(json), d = j && obj(j.data), m = d && obj(d.metrics);
    if (!m) return { ok: false, errors: arr(j && j.errors), blocks: [] };
    var ss = obj(m.stressed_seasons) || {}, st = obj(m.season_types), tr = obj(m.seasonal_transitions);
    var blocks = [];
    if (ss.weather_2001_2024) blocks.push({ id: 'stress_w', title: ['Unusual seasons: weather only, 2001–2024', 'অস্বাভাবিক মৌসুম: শুধু আবহাওয়া, ২০০১–২০২৪'], b: block(ss.weather_2001_2024) });
    if (ss.with_smap_ndvi) blocks.push({ id: 'stress_s', title: ['Unusual seasons: with soil moisture and greenness', 'অস্বাভাবিক মৌসুম: মাটির আর্দ্রতা ও সবুজতা সহ'], b: block(ss.with_smap_ndvi) });
    if (st) blocks.push({ id: 'types', title: ['Season types (hot, wet, typical)', 'মৌসুমের ধরন (গরম, ভেজা, স্বাভাবিক)'], b: block(st) });
    if (tr) { var t = block(tr) || {}; t.methodAStatus = tr.method_a_status || ''; t.resolution = tr.resolution_note || ''; blocks.push({ id: 'trans', title: ['Green-up and browning dates', 'সবুজ হওয়া ও বাদামি হওয়ার তারিখ'], b: t }); }
    return {
      ok: arr(j.errors).length === 0, errors: arr(j.errors), sourceMode: j.source_mode || null, isMock: j.is_mock === true,
      note: m.note || '', seed: m.seed, districts: arr(m.districts), blocks: blocks, excluded: obj(m.excluded_inputs) || {}, layers: obj(m.layers) || {},
      stressCaveat: ss.caveat || '', events: { used: arr(ss.events_used), notUsed: arr(ss.events_not_used) },
      cards: obj(d.cards) || {}, notes: d.note || ''
    };
  }
  window.CS_MD = { adapt: adapt };
})();
