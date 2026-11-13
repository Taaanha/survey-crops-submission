/* Adapter: /api/v1/map/passport answer -> the 30 m field map layers. Renaming only.
   Each layer is a square grid of 30 m pixels around the field point, row 0 = north edge.
   A layer the server could not assess keeps its reason (shown, never drawn as zero). */
(function () {
  'use strict';
  function arr(x) { return Array.isArray(x) ? x : []; }
  function obj(x) { return x && typeof x === 'object' && !Array.isArray(x) ? x : null; }
  function adapt(json) {
    var j = obj(json), d = j && obj(j.data);
    if (!d) return { ok: false, errors: arr(j && j.errors), layers: [] };
    return {
      ok: arr(j.errors).length === 0, errors: arr(j.errors), field: obj(d.field), windowM: d.window_m || null,
      layers: arr(d.layers).map(function (l) {
        return { key: l.key, label: l.label, pixelM: l.pixel_size_m, status: l.status, reason: l.reason || '',
                 dataset: l.dataset, url: l.source_url, unit: l.unit, grid: arr(l.grid), statusGrid: arr(l.status_grid),
                 caveats: arr(l.caveats) };
      })
    };
  }
  window.CS_PP = { adapt: adapt };
})();
