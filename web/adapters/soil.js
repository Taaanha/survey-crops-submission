/* Adapter: /api/v1/soil answer -> the soil tiles. Renaming only.
   `estimate` is "field" (SoilGrids 250 m model estimate at the point) or "district" (district values, pH and
   organic carbon then have value null = not available, never 0). SoilGrids is a model estimate, not a lab test. */
(function () {
  'use strict';
  function arr(x) { return Array.isArray(x) ? x : []; }
  function obj(x) { return x && typeof x === 'object' && !Array.isArray(x) ? x : null; }
  function measure(m) { m = obj(m); return m && m.value !== undefined && m.value !== null ? { value: m.value, unit: m.unit || '', src: arr(m.src) } : null; }
  function adapt(json) {
    var j = obj(json), d = j && obj(j.data), so = d && obj(d.soil), prov = {};
    arr(j && j.provenance).forEach(function (p) { if (p && p.id) prov[p.id] = p; });
    if (!so) return { ok: false, errors: arr(j && j.errors), notices: arr(j && j.notices), provenance: prov };
    return {
      ok: arr(j.errors).length === 0, errors: arr(j.errors), notices: arr(j.notices), provenance: prov,
      sourceMode: j.source_mode || null, estimate: so.estimate || null, depth: so.depth || null,
      texture: obj(so.texture), sand: measure(so.sand_pct), silt: measure(so.silt_pct), clay: measure(so.clay_pct),
      ph: measure(so.ph), oc: measure(so.organic_carbon_g_kg), advice: d && obj(d.test_advice)
    };
  }
  window.CS_SOIL = { adapt: adapt };
})();
