/* Adapters: /api/v1/data/sources and /api/v1/districts -> what the Data page draws. Renaming and tidying only.
   A dataset the server could not assess keeps its status and reason ("not assessed" is never turned into 0 or "ok"). */
(function () {
  'use strict';
  function arr(x) { return Array.isArray(x) ? x : []; }
  function obj(x) { return x && typeof x === 'object' && !Array.isArray(x) ? x : null; }
  function sources(json) {
    var j = obj(json), d = j && obj(j.data);
    if (!d) return { ok: false, errors: arr(j && j.errors), items: [] };
    return {
      ok: arr(j.errors).length === 0, errors: arr(j.errors), notices: arr(j.notices), sourceMode: j.source_mode || null, isMock: j.is_mock === true, note: d.note || null,
      items: arr(d.datasets).map(function (x) {
        return { key: x.key, name: x.dataset, status: x.status || '', coverage: x.coverage || '', districts: x.districts, reason: x.reason || '', url: x.source_url || '', units: x.units || '', resolution: x.resolution || '' };
      }),
      files: arr(d.processed_files)
    };
  }
  function districts(json) {
    var j = obj(json), d = j && obj(j.data);
    if (!d) return { ok: false, errors: arr(j && j.errors), items: [] };
    return {
      ok: arr(j.errors).length === 0, errors: arr(j.errors), sourceMode: j.source_mode || null, isMock: j.is_mock === true,
      items: arr(d.districts).map(function (x) {
        var c = obj(x.coverage) || {};
        return { id: x.id, name: obj(x.name), covered: x.covered === true, sharedWith: arr(x.power_cell_shared_with), cov: c,
                 crops: arr(c.risk_calendar_crops) };
      })
    };
  }
  window.CS_DS = { sources: sources, districts: districts };
})();
