# Survey Crops: Innovation Decision and Build Plan (24 Oct 2026)

*Answers the "make Survey Crops the strongest Field Shift solution" prompt. Agreed with Tanha in chat on 24 Oct 2026. Every competitor and dataset claim links to a page that was opened (see Sources). Anything not checked is marked **UNVERIFIED**.*

---

## 0. Decisions confirmed by Tanha (24 Oct 2026)

| # | Decision | Note |
|---|---|---|
| 1 | **Headline = a field-aware crop-rotation planner** (wording follows the official challenge text), with flood features #1 (flood-tolerant variety matching) and #2 (satellite damage map vs DAE figures); #3 (safest seedbed finder) if time allows | The flood replant planner becomes the "adapt" step of the rotation tool |
| 2 | **Districts: add Chattogram, Khulna, Rajshahi, Barishal**, giving 9 in total. Stay open to all 64 later | Overrides the earlier "locked 5 districts" rule. Tanha confirmed explicitly |
| 3 | **Basic mode** for every other district/location uses **NASA data only** | Labelled "basic, weather and soil-moisture only, not validated here" |
| 4 | **Cyclone Remal demo** (Khulna; Barishal as backup) | Salt part uses the research-based leaching method; no guessed multipliers |
| 5 | **Build tasks are written for Claude Code** | The project instructions still say "plain chat only, no Claude Code". **Tanha should update the project instructions** so they match |
| 6 | Add-ons accepted: season-wise disease risk (BAMIS weather thresholds), soil-nutrient disorder warnings (SRDI), research-based salinity, drought "too dry" flag | See the priority order in §6 |
| 7 | **Extended cut order in §6.3 confirmed** (24 Oct 2026) | New add-ons are cut first, last-in first-out; the existing order (UI polish → ML sophistication → Sentinel-1 → districts) is unchanged underneath |

---

## 1. What the research found (Step 1 summary)

**Field Shift entries checked: about 22 public repos.** The 9 from the prompt plus BoponX, both TerraShift teams, Zishan-125's Field Shift, AgriOrbit, FarmShift (Nepal), Crop Care, Krishi Bondhu, FieldShift-NASA (Punjab), imarwanmokhtar/fieldshift, farmstack and AgriShift.

- **UNVERIFIED (no public page found):** Nebula Collectors, Zero Requiem "FieldShift BD", Stellavia, PANDAM, NEXVIA.
- **YouTube:** no Field Shift videos found yet. Local videos are due 13 Nov; check manually around 10–12 Nov.

### Feature rarity

| Feature | Teams | Rarity |
|---|---|---|
| NASA POWER, FAO-56 water use, priority sliders, provenance/receipts, offline, Bangla voice | almost all | **Common** |
| "Bad in X of N past years" or replaying plans through past years | Krishi Mama, FieldShift (global), Hold the Field, AgroRadar (planned), Crop Care, us | **Common** |
| SMAP, IMERG, season-shift statistics, "what if" scenarios | 5–8 | Common |
| Haor upstream flash-flood warning | AgroRadar, Hold the Field, Crop Care, RotaShift | Rare (about 4) |
| NDVI, salinity, SMS, LLM layer, real ML, officer named as user | 2–4 each | Rare |
| Lender/insurance loss certificate | Crop Care (claimed, not validated) | Unique to them |
| **OPERA radar/optical water maps; post-flood "when can I sow"; out-of-sample hindcast; code-enforced provenance gate; El Niño lens** | **us only** | **Unique** |
| **Field-level (30 m) water history driving rotation choice; checking advice against real outcomes (DAE figures, observed regrowth); one screen for an officer's whole block** | **nobody** | **White space** |

### District coverage of competitors

- MOUSUMI and TerraShift (chandon2025) cover all 64 districts, but with POWER-only or untested scores. POWER is about a 50 km grid, so neighbouring districts share values.
- Others cover 1–4 districts or demo plots.
- Nobody combines many districts with multi-sensor, tested outputs.

### Risks found in our own project

- **Our public README still describes the old idea**, including a "live ML classification feature" that was cut. It must be rewritten (task T19).
- MOUSUMI's audit found **multi-decade breaks in POWER data over Bangladesh**. We must run our own homogeneity check before showing 1981+ or 2001+ trends (task T9b).

---

## 2. Problem sizing (cited)

| Problem | Evidence | Verdict |
|---|---|---|
| **Flood loss and late replanting (east/southeast)** | Aug 2024 flood: 1,414,089 farmers affected, 714,514 t crop loss worth about Tk 3,346 crore. Feni 80% of farmland affected, Noakhali 37%, Comilla 36%, Brahmanbaria 35%. Standing Aman washed away on 0.3 M ha; 0.1 M ha uncertain because of a seedling shortage | **Biggest in our area. The headline is built around it** |
| Haor flash flood (Boro) | 2017: 0.88 Mt Boro lost, about USD 450 M; roughly once in 3 years | Big, but crowded and outside the Nov season |
| Cyclone saltwater (southwest) | Remal 2024: 537,234 farmers affected, 80,591 ha inundated, about $96.7 M farm loss | Real. **Remal demo in Khulna** |
| Coastal salinity | SRDI: about 1.02–1.06 M ha salt-affected (2009 survey); a 2024 SRDI figure quoted in the press is about 1.156 M ha | Background layer for Noakhali, Khulna and Barishal |
| Drought (northwest) | Crowded (3 teams) | Rajshahi as the drought showcase, using existing features |

---

## 3. The headline

### 3.1 Headline innovation
**"A rotation planner that knows how *your* field floods and dries."**

Survey Crops is a decision-support tool for exploring **year-round crop rotations** for a specific field, matching the official challenge text. It combines:

- **NASA Earth observations:** POWER, IMERG, SMAP, OPERA DSWx (S1 radar + HLS optical), OPERA DIST-ALERT, HLS.
- **Local soil information:** SoilGrids texture, SRDI fertility status (Zn, S, B, P, K, OM, pH), SRDI salinity, the officer's own soil test.
- **Crop characteristics:** FAO-56 Kc, GDD stages, heat/cold limits, duration, flood tolerance, FAO-29 salt tolerance, legume status.
- **Farmer priorities:** save water / soil health / lowest risk / flood safety.

**The unique part:** each field's **own measured water behaviour at 30 m** (how often it floods, how long it stays under water, when it drains) decides which rotations are feasible. When a flood hits, the rotation **re-plans itself** from the satellite-measured ready date.

### 3.2 Supporting upgrades
- **C. Drain-time model (Layer 2):** a real trained model predicting "days until this patch drains" from terrain, antecedent soil moisture and rain. Trained on the 2024 flood, tested on a later flood, with honest accuracy against a simple baseline.
- **D. Honesty scorecard:** out-of-sample hindcast of rotation advice against the traditional calendar over 2001–2024, measured in problem years avoided and irrigation saved. It also publishes the damage-map and regrowth validations.

### 3.3 Flood features inside the headline
1. **Flood-tolerant variety matching:** submergence-tolerant varieties withstand about 15–17 days of stagnant water. If a field's typical inundation is ≤ 14 days (conservative), allow a flood-tolerant Aman; otherwise use rotations without Aman.
2. **Satellite damage map vs DAE figures:** OPERA DIST-ALERT vegetation loss over cropland for Aug–Sep 2024, summed per district and compared with DAE's reported affected hectares.
3. *(If time)* **Safest seedbed finder:** the least-flooded patches in a block, for community seedbeds.

### 3.4 Stop emphasising (everyone has these)
Bangla voice, priority sliders as a feature, offline mode, "receipts", "bad in X of N years" as the pitch, the analog year as the hero, El Niño as the hero. **All of them stay in the app** but are not the story.

### 3.5 One-line pitch
> "Survey Crops helps farmers and extension officers choose a year-round crop rotation for each field, based on how that field actually floods and dries as seen by NASA satellites, plus its soil and the farmer's priorities. Every option is tested on 24 past seasons, and the plan re-adjusts the day floodwater leaves."

### 3.6 30-second hook
> "August 2024. 1.4 million Bangladeshi farmers lost crops; in Feni, 80% of farmland went under water. When the water left, every farmer asked: *what can I still grow, and what should next year's rotation be?* Every app gives the same advice to a whole district. NASA satellites can see how each field floods and dries. Survey Crops turns that into a crop rotation for each field, tested on 24 past seasons, that re-plans itself when the next flood comes."

### 3.7 Why it beats the strongest competitors on the three goals

| Goal | MOUSUMI / FieldShift (global) / Krishi Mama | Survey Crops |
|---|---|---|
| Huge real problem | Generic "shifting seasons" | The costliest recurring hazard: 2024 flood, 1.41 M farmers, Tk 3,346 crore. Also covers the drought, salt and cyclone belts |
| Local impact | Farmer app or district dashboard | The SAAO's block view: one officer serves about a thousand households. Seed requests follow how DAE actually responds after floods |
| Data and technology | POWER (+ MODIS) at about 50 km | 30 m radar + optical fusion (OPERA DSWx/DIST, HLS) plus SMAP and IMERG; validated against DAE figures and observed regrowth; a real ML model with held-out testing |

---

## 4. Datasets (availability checked; resolution and record)

| Dataset | Use | Resolution / record | Status |
|---|---|---|---|
| NASA POWER | Weather, ET0, GDD, disease-weather days | about 0.5°, 1981– | ✅ in use |
| GPM IMERG | Rain (separates neighbouring districts), heavy-rain flood exposure, salt washout | 0.1°, 2000– | ✅ in use |
| SMAP L3/L4 | Soil back to normal / too dry | 9–36 km, 2015– | ✅ in use |
| OPERA DSWx-S1 | Radar water through cloud | 30 m. **Record start: July or Sept 2024 (sources disagree). Check against the Aug 2024 recession before relying on it** | ✅ in use (20 km box) → per pixel |
| OPERA DSWx-HLS | Optical water, incl. Remal | 30 m, Apr 2023– | ✅ near-global |
| OPERA DIST-ALERT-HLS | Vegetation and crop loss (damage map) | 30 m, every 2–4 days, Jan 2023– | ✅ near-global, includes crops |
| HLS (NDVI) | Observed regrowth after flood | 30 m | ✅ |
| JRC Global Surface Water (Landsat-based, **non-NASA product**, label it) | Long-term flood frequency | 30 m, 1984– | ✅ in Earth Engine |
| HAND / terrain (NASADEM or GLO-30 HAND) | ML feature | 30 m | **UNVERIFIED: check which HAND product is free and covers Bangladesh** |
| SoilGrids 2.0 | Texture → leaching K, water holding | 250 m | ✅ in use |
| SRDI Soil Fertility Atlas 2020 | Nutrient status classes | Upazila-level maps | **UNVERIFIED: downloadable data, or PDF maps to transcribe? Check licence** |
| SRDI salinity (2010) + Noakhali field studies | Salinity background | Upazila / point samples | ✅ citable, labelled "not current" |
| Topsoil Salinity Observatory, SW coast (Sci Data 2025) | Testing the salt method in Khulna | Point samples | **UNVERIFIED: Khulna site coverage and licence** |
| BAMIS crop-weather calendars | Disease and pest weather thresholds | Regional | ✅ government PDFs |
| Admin boundaries (union/upazila) | Block summaries | Polygons | **UNVERIFIED: source and licence (e.g. OCHA COD-AB on HDX)** |

---

## 5. Validation plan (how every claim is proven)

| Claim | Test | Metric reported |
|---|---|---|
| Rotation advice beats the traditional calendar | Leave-one-year-out hindcast 2001–2024 (existing module, extended to rotations) | Problem years avoided; irrigation mm saved (worst 20%); n shown |
| Water model is realistic | FAO-56 water balance vs SMAP (existing) | r, bias |
| Satellite damage reading is credible | DIST-ALERT damaged cropland vs DAE district figures, Aug 2024 | Ratio per district; honest explanation of the gaps (DAE "affected" ≠ "vegetation lost"; clouds) |
| Ready-to-plant dates are right | Predicted ready date vs HLS-observed green-up after the 2024 flood (sampled pixels) | Hit rate, false alarms, median error in days |
| Drain-time model works | Trained on 2024 events, tested on a later flood (Feni). Spatial block cross-validation | MAE in days vs a median-drain-time baseline. **If it does not beat the baseline, say so** |
| Disease-weather index means something | Blast-favourable days vs BRRI's 2015–2017 blast peak (highest in the Cumilla region) | Rank of 2015–17 among all years |
| Salt leaching method is reasonable | Hoffman textbook example as a unit test; Khulna observatory samples if available | Error vs measured EC |
| POWER is homogeneous enough | Break test on POWER vs IMERG over the record (T9b) | Breaks flagged; trend windows limited to clean periods |

---

## 6. Build plan

### 6.1 Rules for every task
- **Layer boundaries are non-negotiable.**
  - Layer 1 `src/compute`: deterministic, unit-tested, no AI.
  - Layer 2 `src/ml`: real model, honest metrics.
  - Layer 3 `src/agents`: free Hugging Face model, plain state machine, 6-step cap, `guard()` provenance gate, template fallback.
  - Layer 4 `web/`: renders the API only.
- **Every new number carries `dataset`, `source_url` and `retrieved` fields** in the API response. `guard()` must block any narrated number that isn't in a tool result.
- **Raw rasters never go in git.** Use Colab/local or a Hugging Face Dataset repo. Only small derived files (parquet, small COGs, JSON) go in `data/processed/`.
- **Each task ends with:** tests passing, `docs/AI_USE.md` updated, `docs/assumptions` regenerated, and a PR.
- **Wording rule:** never write "predict" or "forecast". Use "past seasons show…", "estimated…", "tested on…".

### 6.2 Ordered tasks (each sized for one Claude Code session)

> **Owner key:** T = Tanha + Claude Code. R = research teammate. F = frontend teammate. V = video teammate.

**CORE (critical path)**

**T0. Housekeeping** (Layer 1 + docs, 0.5 d, T)
- Fix the Field Twin heat flag (grain fill must use the grain-fill limit, not the flowering limit).
- Update CLAUDE.md with the new scope.
- Add the AI_USE entry.

*Acceptance:* a new test shows a grain-fill-stage day is judged against the grain-fill threshold.

**T1. Rotation engine** (Layer 1, 1.5–2 d, T)
- Build full-year rotations (Kharif-2 Aman → Rabi → Kharif-1) by chaining the existing per-crop risk calendar.
- Feasibility: harvest date + turnaround ≤ next sowing window.
- Per rotation per year (2001–2024):
  - problems yes/no;
  - **Kc-weighted irrigation need** (never cut);
  - legume count;
  - soil-health indicators, cited only.
- Crop table: duration, Kc, GDD, heat/cold limits, flood tolerance (days), FAO-29 ECt and slope, legume flag. Every row cited.

*Acceptance:*
- A long-duration Aman followed by a 10 Nov mustard is flagged infeasible when the harvest overlaps.
- Results are identical across repeated runs.
- The Kc comparison test still passes.
- "Problems in X of N" matches a hand count on a synthetic 3-year fixture.

**T2. Farmer priorities** (Layer 1 + API, 0.5 d, T)
- Transparent weighted re-ranking: water saving, soil health, lowest risk, flood safety.
- Normalised components are shown in the API.

*Acceptance:* raising the "water saving" weight never moves a higher-irrigation rotation above a lower-irrigation one, all else equal (property test).

**T3. Field water profile** (data prep in Colab/GEE + Layer 1 query, 2 d, T, with R helping on downloads)
- Per 30 m pixel on cropland, using OPERA DSWx-HLS + DSWx-S1 (2023–2026):
  - inundation days per event;
  - drain date;
  - number of events.
- Long-term occurrence % from JRC GSW, labelled non-NASA.
- **First sub-step:** list the OPERA granules (CMR) over Feni and Cumilla for 15 Aug–31 Oct 2024. Record the true DSWx-S1 first date and cloud gaps.
- Store the profile as small COG/parquet tiles on a Hugging Face Dataset.
- `field_profile(lat, lon)` returns metrics plus granule IDs.

*Acceptance:* a known flooded Feni pixel shows inundation in Aug 2024; a known high-ground pixel shows none; every value has a granule ID.

**T4. Flood-tolerant variety matching** (Layer 1, 0.5 d, T)
- Filter or re-rank rotations using T3 inundation days against the crop table's flood tolerance (Sub1 class cited; 14-day conservative cut-off).

*Acceptance:* boundary tests at 13 / 14 / 15 days.

**T5. Flood re-plan + officer block view** (Layer 1 + API, 1.5 d, T; R supplies seed rates and boundaries)
- The existing post-flood readiness (SMAP rule + OPERA recession) moves from the 20 km box to per-pixel T3 drain dates.
- Re-run T1 from the ready date, giving three outcomes: short Aman possible / switch to winter crop / fallow risk.
- Block or union summary: hectares per outcome, plus seed request = ha × **cited** BRRI/BARI seed rate.

*Acceptance:*
- Seed arithmetic unit test.
- A ready date after the Aman cut-off never returns "Aman possible".
- The summary hectares equal the sum of pixel areas.

**T6. Damage map vs DAE** (Layer 1 notebook + JSON for `/methods`, 1.5 d, T)
- DIST-ALERT VEG-DIST-STATUS confirmed loss, Aug–Sep 2024, over a cropland mask (MODIS MCD12Q1, NASA, or a labelled non-NASA mask).
- Sum the hectares per district and compare with DAE figures (UNB, 2024).

*Acceptance:* the script reproduces the numbers from cached inputs. The output JSON carries both figures and both sources. The README explains the definitional differences.

**T7. Regrowth check of ready dates** (validation, 1.5 d, T)
- HLS NDVI time series on a sample of 2024-flooded pixels, giving a green-up date.
- Compare with T5 ready dates.
- Repeat on the later Feni flood if HLS coverage allows.

*Acceptance:* hit rate, false alarm rate and median error published to `/methods`, with sample size and the cloud-loss share.

**T8. Layer 2: drain-time model** (Layer 2, 2 d, T)
- **Features:** HAND/terrain (UNVERIFIED source), JRC occurrence, SMAP antecedent, IMERG post-peak rain, optional distance to river (labelled non-NASA).
- **Label:** T3 drain days.
- **Model:** scikit-learn gradient boosting with spatial block cross-validation; test on the later flood.
- **Baseline:** median drain days.

*Acceptance:*
- Metrics JSON includes MAE for both model and baseline, plus n.
- The confidence or interval is reported.
- `src/ml` has a model card.
- If the model loses to the baseline, the app uses the baseline and says so.
- *Cut order item 2 ("ML sophistication") can simplify this to linear or quantile regression.*

**T9. Honesty scorecard** (Layer 1, 1 d, T)
- Extend the hindcast to rotations against the traditional DAE/BRRI calendar, leave-one-year-out.
- Keep the analog-year backtest (Field Twin), which is never cut.

*Acceptance:* problem years avoided and irrigation saved, with n and years listed, published as JSON + a page.

**T9b. POWER homogeneity check** (Layer 1, 0.5 d, T)
- Break test on POWER rain against IMERG, 2001–2024, per district.

*Acceptance:* detected breaks are listed; trend outputs are restricted to clean windows and labelled.

**T17. Agent `/ask`** (Layer 3, 1.5–2 d, T)
- Free HF model with tool-calling; state machine; 6-step cap; tools for T1–T9; `guard()` before every answer; template fallback; Bangla and English.

*Acceptance:*
- The test where a fabricated number is blocked passes.
- When the HF endpoint is down, a template sentence is returned.
- The response is never empty or broken JSON.

**T18. API contract consolidation** (1–1.5 d, T)
- New endpoints:
  - `/rotation`
  - `/field-profile`
  - `/replan`
  - `/block-summary`
  - `/validation/damage`
  - `/validation/regrowth`
  - `/scorecard`
- Fix or remove the mock `/warnings` and `/enso-lens`.
- Update `web/mock/*.json`.

*Acceptance:* contract tests pass; every number field has a sibling `source` object.

**T19. README rewrite + demo fixtures + offline mode** (0.5–1 d, T + V)

*Acceptance:* the README matches the live system (no ML classifier claim); the offline fixtures replay the full demo with Wi-Fi off.

**DISTRICTS** (in this order)

**T10a–d. Chattogram → Khulna → Rajshahi → Barishal** (0.5–1 d each, T + R)
- POWER (existing CSVs for Chattogram and Barishal; new pulls for Khulna and Rajshahi), IMERG (Giovanni), SMAP, SoilGrids, OPERA tiles, BAMIS regional calendar.
- Re-run T1, T3 and T9.

*Acceptance per district:* the risk calendar and hindcast JSON exist; the provenance is complete; a district test passes.

**ADD-ONS** (in priority order)

**T14. Salinity add-on** (Layer 1, 1.5–2 d, T)
- Hoffman leaching: (C/C0)(dL/ds) = K, with K from soil texture.
- FAO concentration factors for dry-season build-up.
- FAO-29 Maas–Hoffman thresholds.
- Inputs: soil test → SRDI baseline ("2010, not current") → "unknown".
- **No guessed seasonal multipliers.**

*Acceptance:*
- The textbook case (K 0.3, 3 ft, 10 → 2 dS/m) needs 4.5 ft of drained water.
- "Unknown" is returned when no input exists.
- Validated against Khulna observatory points if available.

**T15. Remal demo, Khulna** (1–1.5 d, T)
- DSWx-HLS scenes, late May–June 2024; IMERG rain since 26 May 2024; T14 "water still needed to wash salt out vs drained so far"; offline fixture.

*Acceptance:* every number traces to a granule or the IMERG file. Salt "now" is shown as "not measured" unless a soil test is entered.

**T16. Drought "too dry" flag + Rajshahi showcase** (Layer 1, 0.5 d, T)
- SMAP below the 20th percentile for the date gives "irrigate before sowing or pick a low-water crop".

*Acceptance:* mirror tests of the existing 80th-percentile flood rule.

**T12. Disease weather-risk** (Layer 1, 2 d, T; R transcribes BAMIS thresholds with page citations)
- Count favourable days per crop stage per season from POWER (T2M_MIN, T2M_MAX, RH2M, PRECTOTCORR, cloud amount).
- Precautions text comes only from BRRI/DAE/BAMIS. Cultural practices only, no pesticide doses, "consult your SAAO".

*Acceptance:* threshold unit tests; the 2015–17 blast rank check for Cumilla published honestly.

**T13. Soil-nutrient disorder warnings** (Layer 1 + data, 1.5–2 d, T; R transcribes the SRDI atlas classes for our upazilas)
- Status classes → cited disorder table (e.g. zinc deficiency → khaira symptoms) → "get a soil test (SRDI mobile lab / OFRS)".
- Correct wording: disorder, not disease.

*Acceptance:* every class value has an atlas page reference; a test confirms no fertilizer dose is ever output.

**T20. Safest seedbed finder** (flood feature #3, 1 d, T)
- Rank the least-flooded patches per block from T3 and JRC.

*Acceptance:* the ranking matches flood-occurrence order on a fixture.

**T11. Basic mode for any location in Bangladesh** (NASA data only, 1–1.5 d, T)
- POWER + IMERG + SMAP at any point: risk calendar + rotation (T1/T2) without the field water profile.
- Clearly labelled "basic, not validated here". Keeps the door open to all 64 districts.

*Acceptance:* returns for random points across all 64 districts; the label is always present; no SRDI or OPERA fields appear.

**PARALLEL (teammates)**
- **F:** screens on mocks: rotation comparison, field water-profile map, re-plan, officer block view, proof page, priorities, Bangla toggle. Then wire to the live API.
- **R:** cited tables (crop table, flood tolerance, seed rates, BAMIS thresholds, SRDI atlas classes, DAE 2024 figures, union boundaries plus licence), and the licence checks marked UNVERIFIED above.
- **V:** video script v5 (storyline in §7), Bangla TTS check on the demo laptop, backup recording.

### 6.3 Priority and cut order

**Never cut:**
- the analog-year backtest (Field Twin);
- the Kc-weighted comparison;
- the `guard()` provenance gate;
- the hindcast/scorecard.

**Build order:** T0 → T1 → T2 → T3 → T4 → T5 → T6 → T7 → T9 (+T9b) → T8 → T17 → T18 → T10a (Chattogram) → T10b (Khulna) + T14 + T15 → T10c (Rajshahi) + T16 → T10d (Barishal) → T12 → T13 → T20 → T11 → T19 last before the freeze.

**Cut order if late (confirmed by Tanha, 24 Oct 2026):**
1. *New add-ons, last-in first-out:* T11 basic mode → T20 seedbeds → T13 nutrients → T12 disease → T10d Barishal → T16 drought flag → T15 Remal → T14 salinity.
2. *Then the existing order, unchanged:* UI polish → ML sophistication (simplify T8) → Sentinel-1/waterlogging details → district count (remove T10c, then T10b, then T10a).

### 6.4 Honest time check
- **Core (T0–T9b, T8, T17, T18, T19):** about 17–19 working days for one person with Claude Code.
- **Calendar:** 24 Oct to the 12 Nov dry run is 19 days.
- **So the core alone fills the time.** The districts and add-ons happen only if research teammates take the data and table tasks, and Claude Code sessions run efficiently.
- **Expect to cut some add-ons.** That is planned, not a failure.

### 6.5 Calendar

| Dates | Tanha + Claude Code | Teammates |
|---|---|---|
| 24–26 Oct | T0, T1, T2 | R: crop table, flood tolerance, seed rates; F: rotation screen on mocks |
| 27–29 Oct | T3 (+ granule check), T4. **28 Oct: read NASA's full challenge statement and adjust** | R: DAE figures, boundaries, BAMIS thresholds |
| 30 Oct–1 Nov | T5, T6 | F: water-profile map + re-plan screens |
| 2–3 Nov | T7, T9, T9b | R: SRDI atlas transcription |
| 4–5 Nov | T8, T10a | F: officer block view + proof page |
| 6–7 Nov | T17, T18; frontend wired to live API | V: script v5 |
| 8–9 Nov | Add-ons in priority order (T10b + T14/T15, T10c + T16, …) | F: Bangla polish, mobile |
| 10–11 Nov | **Freeze**, T19, fixtures, video recording | V: Bangla TTS check, backup recording |
| 12 Nov | **Full offline dry run** | everyone |
| 13 Nov | Local video + submission | everyone |

---

## 7. Demo storyline (about 4 min; one case from start to finish)

*All numbers on screen must come from the live tool; [brackets] mark where a real output goes. The farmer is fictional and adult; no under-18 names, faces or voices.*

1. **0:00–0:30 Hook + headline.**
   - Aug 2024 flood stats.
   - The camera lands on one field in Feni with its **water profile**: "under water [N] days in Aug 2024; drained [date]" (OPERA radar + optical).
   - Title: *a crop rotation for each field, tested on 24 seasons.*
2. **0:30–1:10 Plan the year.**
   - The SAAO opens their block and picks the field.
   - Farmer priorities: soil health + low risk.
   - Three rotations compared: "problems in [X] of 24 years", irrigation [mm] in dry years, legume in rotation.
   - A flood-tolerant Aman is suggested because the field usually drains within [≤14] days.
3. **1:10–1:50 The flood comes (Field Twin replay of 2024).**
   - DIST-ALERT damage appears.
   - The water recedes; SMAP soil returns to normal; the ready date is [date].
   - **The rotation re-plans itself:** short Aman no longer possible → [black gram → …].
   - Block summary: [ha] per outcome → seed request [kg].
4. **1:50–2:40 Proof.**
   - Damage map vs DAE figures for 4 districts.
   - Ready dates vs observed regrowth: hit rate [ ].
   - Scorecard vs the traditional calendar.
   - Drain-time model MAE vs baseline.
   - The receipt drawer, and the provenance gate blocking a made-up number live.
5. **2:40–3:20 One engine, four hazards.**
   - Khulna: Remal saltwater, "water still needed to wash salt out vs drained so far".
   - Rajshahi: drought, too dry to sow.
   - Disease-weather risk and nutrient warnings in one card.
   - Basic mode for any location.
6. **3:20–4:00 Impact and pilot.**
   - One SAAO serves about a thousand households.
   - Post-hackathon pilot: one union in Cumilla, Rabi 2026–27, with the Upazila Agriculture Office.
   - We'll measure: officer time per farmer, decisions taken, and satellite-observed sowing against the plan.
   - Open source (Apache-2.0); team name.

**30-second global video:** the field water profile (8 s) → rotation re-plans after the flood (10 s) → proof against DAE figures + regrowth (7 s) → impact line (5 s). English subtitles.

---

## 8. Post-hackathon pilot (one union, Cumilla)

- **Partners:** Upazila Agriculture Office + 1–2 SAAOs. Possible soil/salinity advisers: researchers at NSTU who published Noakhali salinity work.
- **Season:** Rabi 2026–27 (Nov–Feb).
- **Measures:**
  - farmers reached per SAAO;
  - which rotation each farmer chose;
  - satellite-observed sowing dates against the plan;
  - officer feedback.
- **No yield or Taka benefit is claimed until it is measured.** Impact claims stay limited to cited figures and calculations.

---

## Sources

**Competitors**
- MOUSUMI: https://github.com/Shamimhasan8/NASA-MOUSUMI
- Field Shift (Zul-Qarnain): https://github.com/Zul-Qarnain/field-shift
- RotaShift: https://github.com/XtremeseOISHEE/RotaShift
- AgroRadar: https://github.com/mahabub5090/AgroRadar
- Krishi Mama: https://github.com/mahjabin-alif-lamiya/krishi-mama
- AgriSense Fusion: https://github.com/ASHIK311/agrisense-fusion
- Zerox: https://github.com/eskit2005/NASA-Space-App-Challenge-Field-Shift
- FieldShift (global): https://github.com/samuelakosaonyejekwe/fieldshift
- Hold the Field: https://github.com/ameerul-muminin/anthropocene-spaceapps-2026
- BoponX: https://github.com/rzprince/NASA-SPACE-APPS-Challenge-2026
- TerraShift (chandon2025): https://github.com/chandon2025/Terrashift
- Field Shift (Zishan-125): https://github.com/Zishan-125/field-shift
- AgriOrbit: https://github.com/mahidulphy/AgriOrbit
- FarmShift (Nepal): https://github.com/Spongly/FarmShift
- Crop Care: https://github.com/mdshirajulislam/crop-care-nasa-spaceapps-2026
- Krishi Bondhu: https://github.com/ScriptySphere/Krishi-Bondhu
- FieldShift-NASA (Punjab): https://github.com/sagar25446-prog/FieldShift-NASA
- imarwanmokhtar/fieldshift: https://github.com/imarwanmokhtar/fieldshift
- farmstack: https://github.com/anirban-islam/farmstack

**Problem sizing**
- UNB, Aug 2024 flood (district shares, farmers, Tk): https://unb.com.bd/category/Bangladesh/no-shortage-of-fertilizers-in-the-country-agriculture-adviser/142861
- Financial Express, Aman washed away / seedlings: https://thefinancialexpress.com.bd/economy/food-security-at-stake-as-standing-aman-plants-washed-away
- IRRI, short-duration replanting window: https://news.irri.org/2024/10/irri-strengthens-its-commitment-of.html?m=0
- Daily Star, submergence-tolerant varieties: https://images.thedailystar.net/node/1487869
- Daily Star, seedling crisis: https://www.thedailystar.net/frontpage/seedlings-crisis-worries-farmers-1455001
- Financial Express, seedbeds submerged: https://thefinancialexpress.com.bd/national/huge-farmlands-of-21-districts-go-under-water?amp=true
- Haor flash flood losses: https://encyclopedia.pub/entry/history/compare_revision/119636/-1
- UN rapid assessment, Cyclone Remal: https://bangladesh.un.org/en/download/162708/271466
- SAAO union farmer list: https://archive.saulibrary.edu.bd/handle/123456789/1627?show=full

**NASA data**
- OPERA DSWx: https://www.earthdata.nasa.gov/data/projects/nsite/solutions/opera-near-global-dswx-product-suite
- OPERA DIST: https://www.earthdata.nasa.gov/data/projects/nsite/solutions/opera-near-global-surface-dist-product-suite
- DIST-ALERT covers crops: https://landcarbonlab.org/insights/new-monitoring-system-land-ecosystem-disturbances/
- JPL OPERA slides: https://wwao.jpl.nasa.gov/documents/120/WWAO-Annual-Meeting-Presentation-2024-OPERA-WWAO-meeting-Renato_Frasson.pdf

**Salinity**
- Hoffman leaching: https://workforce.libretexts.org/Bookshelves/Water_Systems_Technology/Irrigation_Systems_Management_(AET_021)/07%3A_Salinity_Management/7.08%3A_Reclamation/7.8.01%3A_Saline_Soils
- FAO salt balance: https://www.fao.org/3/Y4263E/y4263e0h.htm
- Surge salinity persistence (EGU 2024): https://meetingorganizer.copernicus.org/EGU24/EGU24-7175.html
- BAU rainfall leaching trial: https://zenodo.org/records/3953115
- Noakhali studies: https://doaj.org/article/2687995470634193b3cd1e948f58d0db ; https://agris.fao.org/search/en/records/65df2a010f3e94b9e5d5b7c3
- SRDI data age: https://arxiv.org/pdf/2412.19740

**Soil, disease and extension**
- SRDI Soil Fertility Atlas 2020: https://srdi.portal.gov.bd/sites/default/files/files/srdi.portal.gov.bd/publications/cdfc33d1_1d11_4263_9efb_5d3f94b8e502/2021-07-19-04-53-72e64dc42c94b35b3d503c34078e72d1.pdf
- Banglapedia, soil nutrients: https://en.banglapedia.org/index.php?title=Soil_Nutrient
- BAMIS calendars: https://bamis.gov.bd/res/calendars/2019/08/23/5098.pdf ; https://www.bamis.gov.bd/res/public/calendars/2019/08/23/5076.pdf
- BRRI blast 2015–17, Cumilla: https://www.tbsnews.net/node/782534
