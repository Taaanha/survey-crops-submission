# CropShift API contract, v1.0 (26 Sep 2026)

This is the handshake between the backend (`src/`, `app.py`) and the website (`web/`). **Both sides build to this document.**
- The website reads the example files in `web/mock/` until the backend is live.
- The backend has a contract test that checks its real responses have the same keys and types as those files.

**Changing this contract:** open a GitHub Issue titled "Contract change: …". Both sides agree first. Then update this file **and** the matching mock file in one Pull Request, and raise `api_version`.

---

## 1. Rules for every response

**Base URL:** `{API_BASE}/api/v1/…`. The website keeps `API_BASE` in one config line (`web/config.js`), set to `mock` during development.

Every response has the same **envelope**:

```json
{
  "api_version": "1.0",
  "endpoint": "/api/v1/advisory",
  "request": { "district": "cumilla", "lang": "bn" },
  "generated_at": "2026-11-13T09:00:00+06:00",
  "source_mode": "cache",
  "is_mock": false,
  "data": { },
  "narration": {
    "en": "…", "bn": "…",
    "sms_en": "… (≤160 characters)", "sms_bn": "…",
    "narrator": "hf_model | template",
    "provenance_check": "passed | blocked_fallback_used"
  },
  "provenance": [
    { "id": "p1", "dataset": "NASA POWER Daily Point API (AG)", "url": "https://power.larc.nasa.gov/",
      "agency": "NASA", "period": "2001-01-01/2026-08-31", "resolution": "~0.5°", "note": "" }
  ],
  "notices": [ { "level": "info | caution", "en": "…", "bn": "…" } ],
  "errors": []
}
```

| Field | Meaning |
|---|---|
| `source_mode` | `live`, `cache` or `fixture`. **Always shown as a badge.** |
| `is_mock` | `true` only in `web/mock/` files. When true, the website shows "MOCK DATA". |
| `narration` | Text written by the agent (or the template fallback), already checked by the provenance gate. **Display only; never parse numbers out of it.** It is `null` for `/districts` and for error responses. |
| `provenance` | The list of sources. Every number in `data` points to one or more of these by `id`. `url` is the dataset's official page; it is `""` (with a "Link pending" `note`) when a research source has no web address yet. Optional `view_url` (NASA datasets): a page that shows the data as satellite images for our area, e.g. NASA Worldview. Show `url` as "Dataset page ↗" and `view_url` as "See the satellite data ↗". |
| `notices` | Honest caveats, e.g. "area-level data", "Feni and Noakhali share one weather cell". |
| `errors` | Empty when OK. See section 3. |

**A "measure" object.** Every headline number in `data` uses this shape, so the website can open its receipt:

```json
{ "value": 49, "unit": "days", "src": ["p2"] }
```

- For large arrays (charts, calendars) the `src` sits at the array's parent level.
- Units are always given. Dates use `YYYY-MM-DD`.
- Language: all farmer-facing strings come as `{ "en": "…", "bn": "…" }`.

---

## 2. Endpoints

| Method and path | Purpose | Mock file |
|---|---|---|
| `GET /api/v1/districts` | Supported districts, their coverage, and caveats | `districts.json` |
| `GET /api/v1/advisory?district=&prev_harvest=&flood_ready=&lat=&lon=&water=rain_only\|limited\|regular\|plenty&priority=risk,water,more,soil&lang=` | **Main screen:** ranked crop options with sowing windows, risks and reasons | `advisory.json` |
| `GET /api/v1/risk-calendar?district=&crop=` | Crop × sowing-date × hazard grid over all years | `risk_calendar.json` |
| `GET /api/v1/field-twin?district=&year=&crop=&sow_date=` | Week-by-week replay of one past year (an explanation, not a forecast) | `field_twin.json` |
| `GET /api/v1/post-flood?district=&flood_date=&sand=yes\|no` | Water persistence, days until soil is back to normal, earliest sowing date, crops still possible | `post_flood.json` |
| `GET /api/v1/soil?district=&lat=&lon=` | **Farm screen "Your soil":** topsoil texture, pH and organic carbon at the field point (ISRIC SoilGrids, a model estimate). Does not change the ranking | `soil.json` |
| `POST /api/v1/rotation/rank` | **Farmer priorities:** body `{district, weights}`; rotations re-ranked by the weights, with every component shown | `rotation_rank.json` |
| `GET /api/v1/warnings?district=` | Short-range forecast warnings with actions (rule table) | `warnings.json` |
| `GET /api/v1/enso-lens?district=&crop=` | **PENDING confirmation.** El Niño years vs all years | `enso_lens.json` |
| `POST /api/v1/ask` body `{ "question": "…", "district": "…", "lang": "bn" }` | **Real (T17).** Free-text question → answer in the question's language (both `en` and `bn` returned), tools used, guard counts, sources | `ask.json` (shape only) |

**Ask (`POST /api/v1/ask`).** `question` (required, up to 400 characters) in English or Bangla; `district` (optional, one of the five live districts, a district named in the question wins); `lang` is the page language, used only when the question has no letters. A free Hugging Face model (`HF_TOKEN`, `HF_MODEL` in the server environment) picks among five tools (advice, crop risk, rotation ranking, soil, warnings) in at most 6 steps; the answer is the tools' own cited sentences, plus at most one model sentence that passes `guard()`. Without a token or if the model fails, a keyword router picks the tools and `data.llm_used` is `false` (a `RULE_ROUTER` notice says so). `narration.en` and `narration.bn` are both filled; `data.answer_lang` says which one matches the question. `data` has `tools_called`, `steps_used`, `step_cap` (6), `guard` (`numbers_checked`, `numbers_blocked`) and `district`. `provenance` is the union of the tools' sources. Errors: `BAD_PARAMETER` (missing or too-long question), `DISTRICT_NOT_COVERED`. Never an empty body.

**The water question (`water` on `/advisory`, optional).** The farmer's answer to "How much water can you give?". Absent = `regular` = the ranking everything else documents here (no notice added). The request echo carries `water` when it was sent; any other value is `BAD_PARAMETER`.

| `water` | What changes |
|---|---|
| `rain_only` | Options are ranked by problem years, then by `water_stress_days_worst20` (rainfed dry-soil days) instead of irrigation need. An option with dry-soil days in the worst 20% of years gets `water_note: { code: "NEEDS_IRRIGATION", en, bn }` (otherwise `null`). |
| `limited` (1–2 irrigations) | A crop stays ranked only if `irrigation_events_worst20 <= 2`. The others move to `filtered_out` with `reason_code: "NEEDS_MORE_WATER"` and a `reason` `{en, bn}` saying how many waterings it needed. Ranks of the rest are renumbered. All crops can end up filtered. |
| `regular`, `plenty` | Same ranking as today. A `notices` entry says the two are treated the same because there is no sourced pump-capacity number. |

**The priority question (`priority` on `/advisory`, optional).** The farmer's answer to "What matters most to you?": a comma list of `risk`, `water`, `more`, `soil`, in the order the user tapped them. Absent, empty, or `risk` alone = today's ranking (nothing changes). Any other word is `BAD_PARAMETER`. The request echo carries `priority` when it was sent. It is applied after `water` (so `limited` still filters first).

| Key | Sort key (only numbers already in each option) |
|---|---|
| `risk` | `problem_years` (fewest first), then `irrigation_need_worst20` (least first) |
| `water` | `irrigation_need_worst20` (least first), then `problem_years` |
| `more` | `maturity_date` (earliest median maturity; none = last), then `problem_years` |
| `soil` | crops with a kept, cited `data/reference` row `<crop>.soil.legume` = `yes` first. With no such row the key is dropped and a `notices` entry says "research pending: legume source" |

The first tapped key is the main sort key, the others break ties in tap order, then crop name. Crops whose sowing window has passed (`window_status.code = "late"`) still go last. Every card keeps `problem_years` and the irrigation numbers. If the new top crop has more `problem_years` than the best crop under `risk`, a `caution` notice names both numbers.

`data.ranked_by` is always present: `{ keys: [...], text: { en, bn }, src: [...] }`, e.g. `"Ranked by: saving water, then lowest risk"`. `keys` lists the keys that took effect (a `soil` with no cited row is not listed); `src` holds the reference ids behind any legume rows used. The narration ends with the same sentence.

Every option now also carries `irrigation_events_avg` and `irrigation_events_worst20` (measures, unit `waterings`, `src` FAO-56 + IMERG + POWER + the cited soil and crop rows) and `water_note` (`null` unless `rain_only` sets it). A watering is one day the FAO-56 balance refills the root zone; for boro rice, land preparation plus each pond top-up.

**Field twin week flags (`data.weekly.events_rule`, `GET /api/v1/field-twin`).** Each row of `weekly.rows` carries `events`, a non-empty list drawn from `heat`, `night_heat`, `cold`, `rain`, `dry`, `irrigation`, `ok`. `events_rule.thresholds` lists the crop's sourced temperature limits, each `{ event, hazard, label {en, bn}, stage, limit (measure), span }`. `stage` is the crop stage the limit is sourced for (for example `flowering`, `grain_fill`, `first_days`). `span` is `[first_day, last_day]`, inclusive, in days after sowing, for that stage on this sowing date, or `null` when the stage is not reached within the season. A heat, night-heat or cold flag is raised for a day only if the day falls inside the `span` of that limit, and is judged against that limit's own value (so wheat at 33 °C is flagged at anthesis, limit 31, but not in grain fill, limit 35.4). `span` is absent only when the caller gave no stage timing; the web must then treat the limit as applying on every day. Added in the fixups-after-t2 session (additive; needs teammate review as a shared file).

**Your soil (`GET /api/v1/soil`).** Give `lat` and `lon` (the backend picks the nearest district, within the same 60 km limit as `/advisory`) or only `district`. With a point, the backend asks ISRIC SoilGrids 2.0 (250 m, a **model estimate from soil surveys + satellite data, not a lab test**, agency ISRIC, not NASA) for the topsoil and caches the answer on disk (`data/processed/soilgrids_cache/`, not in git). Timeout 10 s. `data.soil` holds `estimate` (`"field"` or `"district"`), `depth`, `texture` `{ value, en, bn }` (USDA class), `sand_pct`, `silt_pct`, `clay_pct`, `ph` and `organic_carbon_g_kg` (all measures). `field`: 0-30 cm, thickness-weighted over 0-5, 5-15 and 15-30 cm, `src: ["soilgrids"]`, `source_mode` `live` or `cache`. If SoilGrids times out, errors, or has no value for that cell (rivers, ponds, towns), or only `district` was given, the answer falls back to the district values in `data/reference/soil_params.csv` (`estimate: "district"`, 0-100 cm, sand/silt/clay and texture only, `ph` and `organic_carbon_g_kg` have `value: null`, `source_mode: "fixture"`) with a `caution` notice saying why. A `notices` entry always says the crop ranking still uses the district soil, not this field estimate. BARI/BRRI field records keep their recorded texture; the website shows it next to this estimate. `data.test_advice` is the "Test your soil at the Upazila Agriculture Office" line. Errors use the usual envelope (`BAD_PARAMETER`, `DISTRICT_NOT_COVERED`); the endpoint never returns broken JSON.

**Farmer priorities (`POST /api/v1/rotation/rank`).** JSON body `{ "district": "cumilla", "weights": { "save_water": 0.5, "soil_health": 0, "lowest_risk": 0.3, "flood_safety": 0.2 } }`. Each weight is 0 to 1 (a missing key is 0); the backend scales them to sum 1, so they need not add up. All zero, an unknown key, or a value outside 0 to 1 is `BAD_PARAMETER`. `data` holds `weights` (`requested`, `normalised`), `metrics` (what each priority measures and its direction), `ranked` and `unranked`. Each `ranked` row has `rank`, `id`, `rotation`, `problem_line`, `score` (0 to 1, the sum of the contributions) and `components` keyed by priority; a component is `{ label, metric, direction, raw, normalised, weight, contribution, no_contrast, note }`, where `raw` is a measure `{ value, unit, provenance }` (provenance holds `dataset`, `source_url`, `retrieved`, `granule_or_file`) or `null`. `normalised` is min-max across the options shown (1 = best); `no_contrast: true` means every option is equal on that metric. A rotation not assessed on a priority that has weight goes to `unranked` with a `reason` and a `how_to_include` hint (for example "Lowest risk is not assessed for boro_rice (...). Set the lowest_risk weight to 0 to compare it on the other priorities."); it is never scored as zero. An unknown legume flag (blank `is_legume`) is treated the same way for `soil_health`: unknown, never 0. The envelope `provenance` lists every provenance entry used. Past seasons 2001-2024, not a forecast. The mock file `rotation_rank.json` is a real response used as an example of the shape.

**Errors** use the same envelope, with `data: null` and for example:
`"errors": [{ "code": "DISTRICT_NOT_COVERED", "en": "…", "bn": "…" }]` (see `error.json`).

Error codes: `DISTRICT_NOT_COVERED`, `BAD_PARAMETER`, `NO_DATA_FOR_PERIOD`, `MODEL_UNAVAILABLE` (the narration then falls back to the template; `data` is still returned), `INTERNAL`.

---

## 3. What the website must do
1. Render only what the JSON contains. No calculations, no unit conversions.
2. Every `measure` shows a small "source" link that opens its `provenance` entries.
3. Always show the `source_mode` badge, and "MOCK DATA" when `is_mock` is true.
4. Show every `notices` item; never hide caveats.
5. If `errors` isn't empty, show the message in the chosen language, and never a blank page.
6. Bangla uses Noto Sans Bengali (a local copy in `web/fonts/`).

## 4. What the backend must do
1. Return exactly these keys and types (checked by the contract test).
2. Every number in `data` has a `src` pointing to an existing `provenance` id.
3. `narration` passes `guard()`. If it doesn't, use the template text and set `provenance_check: "blocked_fallback_used"`.
4. Never return an empty body. On failure, return the error envelope.
