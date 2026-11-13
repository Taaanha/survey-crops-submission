# Handoff 13 Nov 2026: api-disease-risks

## What was asked
Make diseases a real, cited risk: count, over the 24 past seasons, in how many the weather favoured a disease in the crop's growing window; show it in the risk calendar and the pest card; "not assessed" where no sourced rule exists.

## What changed
- `src/compute/disease_risk/` (core.py, MODULE.md) and `tests/disease_risk/test_disease_risk.py` (16 tests).
- `src/api/disease_block.py` + `app.py` (`data.disease_risks` in `/api/v1/risk-calendar`, additive) + `src/api/test_disease_risks.py` (6 tests). The `/disease-rules` caution notice text was updated (it said the feature was not built).
- Web: `web/adapters/riskcal.js` (`disease`), `web/pages/risk.js` (`rkDiseaseHtml`, shown under the heat grid and in the pest card), `web/modes.html` (pest card slot `#pestdis`; two sentences that said diseases are not checked now say disease weather risk is counted only where a sourced rule exists).
- Docs: contract_change_proposals.md section 16, PROJECT_STATE.md (T12 row, Open questions), AI_USE.md.

## Result
Potato late blight, conditions favourable (10 or more favourable days in a row, 1 Nov to 24 Jan): Cumilla 7 of 24, Feni 8, Brahmanbaria 7, Noakhali 7, Sylhet 5. Wheat, lentil, mustard and boro rice: "not assessed" with the reason.

## Caveats
See Open questions "Disease weather risk": weak potato source link (page not pinned), no sourced potato season length, wheat blast source link missing, lentil needs leaf-wetness data. The browser pane could not open the local site in this session, so the web change was checked by running the real API answer through the adapter and render function in Node, not by clicking.
