# Claude Code prompts: Sessions A, B and C (Survey Crops)

*Written 24 Oct 2026. Run them in order: A → B → C. Paste one prompt per session.*

## Before Session A (one time, about 2 minutes)
1. Download two files from the chat: `innovation-decision-2026-10.md` and this file.
2. Open File Explorer and go to `C:\Users\DELL\New folder\Crop-Shift\docs\`.
3. Copy both files into that `docs` folder.
4. In the Claude desktop app, open the **Code** tab on the Crop-Shift folder, as you normally do.

---

## SESSION A: set up partitioned modules + fix the Twin heat flag (T0)

```
You are working in the Survey Crops repo (NASA Space Apps 2026, Challenge 7 "Field Shift").
First read: CLAUDE.md, README.md, docs/innovation-decision-2026-10.md (the new plan), everything
under docs/, and the full src/ and tests/ trees. Do NOT change the behaviour of existing features
except the single bug fix in Part 3.

GOAL OF THIS SESSION
(1) Make the repo "partitioned": a future CHAT assistant (no repo access) must be able to work on ONE
    feature by reading only ~5 small files. (2) Fix one bug (task T0). (3) Self-review. (4) Write a full
    handoff report so a new assistant can catch up.

PART 1: MAP THE REPO (read only)
- For every module under src/compute, src/ml, src/agents, the FastAPI app, and web/: purpose, public
  functions/classes, imports, tests that cover it, data files it reads, layer (1 compute / 2 ml /
  3 agents / 4 web / API).
- Write docs/ARCHITECTURE_MAP.md: one table row per module (path | layer | purpose | public API |
  depends on | tests | data inputs), plus a plain-text dependency diagram. Max ~250 lines.

PART 2: PARTITION CONVENTIONS (minimal file moves)
- Do NOT move or rename existing files unless the move is purely mechanical AND all tests still pass.
  Prefer adding docs over moving code. If you move anything, list it in the report.
- Create a MODULE.md next to the code of every EXISTING feature area (water balance, crop stages/GDD,
  risk calendar + ranking, hindcast, ENSO lens, post-flood readiness (SMAP recovery + OPERA
  recession), field twin, provenance guard, API). Use the MODULE.md template at the bottom.
- Shared contracts: if they do not already exist, create src/compute/common/ with:
  (a) a Provenance dataclass {dataset, source_url, retrieved, granule_or_file, note};
  (b) a small helper so any function can return {value, unit, provenance}.
  Do NOT refactor old code to use it in this session; just list the gaps in ARCHITECTURE_MAP.md.
- Rule for all NEW modules from now on: one folder per feature under src/compute/<feature>/ with
  __init__.py (public API only), core.py (+ small helper files), MODULE.md; tests in
  tests/<feature>/. A module may import only from src/compute/common and from other modules' PUBLIC
  API listed in their MODULE.md. Keep every file under ~400 lines so it can be pasted into a chat.
- Every coefficient/threshold used by new code must live in a CSV under data/reference/ with
  columns: name, value, unit, source_title, source_url, page_or_table, note.

PART 3: BUG FIX T0
- The Field Twin heat flag uses the FLOWERING heat limit during GRAIN FILL. Fix it so each crop
  stage uses its own sourced limit (see the existing heat/cold limits table and its sources).
- Write a failing test first (a grain-fill-stage day judged against the grain-fill threshold), then
  fix, then run the full suite.

PART 4: PROJECT MEMORY FILES
- docs/PROJECT_STATE.md (max ~150 lines): product summary using the NEW headline from
  docs/innovation-decision-2026-10.md; district plan; layer rules; never-cut list (analog-year
  backtest/Field Twin, Kc-weighted comparison, guard() provenance gate, hindcast/scorecard); a status
  table for tasks T0–T20 (copy the task list from the decision doc, mark T0 done after this session);
  the cut order from §6.3 (confirmed by Tanha on 24 Oct 2026); open questions; how to run tests;
  where data lives (repo vs Colab vs Hugging Face Dataset).
- Append to CLAUDE.md a section "WORKING RULES FOR EVERY SESSION" with exactly these rules:
  1. Layer 1 (src/compute) is pure deterministic Python, no AI/LLM imports ever, fully unit-tested.
     Layer 2 (src/ml) = real trained model with honest held-out metrics. Layer 3 (src/agents) = free
     Hugging Face model, plain state machine, hard step cap 6, guard() provenance check as CODE, and
     template fallback (never empty or broken JSON). Layer 4 (web/) only renders API responses.
  2. Every number returned by the API carries provenance (dataset, source_url, retrieved, granule/file).
  3. Never invent numbers, thresholds or citations. If a source cannot be verified, stop and add it to
     "Open questions" in PROJECT_STATE.md instead of guessing.
  4. Raw rasters/scenes never go into git; fail if any file >5 MB is staged. Only small derived files
     go into data/processed/.
  5. User-facing text never says "predict" or "forecast"; use "past seasons show", "estimated",
     "tested on".
  6. One task per branch; all tests must pass before merging.
  7. Every task ends with: self-review checklist, handoff report in docs/handoff/, updated
     PROJECT_STATE.md, updated MODULE.md for touched modules, updated docs/AI_USE.md.
  8. New features go in their own module folder with MODULE.md and tests; files under ~400 lines.
- Create docs/handoff/ and add the report from Part 6 there.

PART 5: SELF-REVIEW (mandatory; fix anything you find, then re-run)
- Run the full test suite; report passed/failed counts before and after.
- grep src/compute for imports of transformers, huggingface_hub, openai, anthropic, langchain:
  there must be none.
- grep user-facing strings in new/changed code for "predict" and "forecast".
- Confirm no staged file is >5 MB.
- Re-read your own full diff line by line; list every mistake you found and how you fixed it.
- Confirm every MODULE.md matches the actual code (function names and signatures).

PART 6: HANDOFF REPORT
Write docs/handoff/2026-10-24_session-A.md using the HANDOFF TEMPLATE below, and also print the
whole report in the chat at the end. Then commit on branch session-a-partition, open a PR, and merge
only if all tests pass. Tell me the PR link and the final test counts.

--- MODULE.md TEMPLATE ---
# <module name>
Layer: <1 compute | 2 ml | 3 agents | API | 4 web>
Purpose (2–3 sentences, plain English):
Public API (exact signatures + one-line description each):
Inputs (data files / other modules) and their provenance:
Outputs (shape + units + provenance fields):
Reference tables used (data/reference/*.csv rows):
Tests (file names + what each proves):
Known limitations / honest caveats:
CHAT KIT (the exact files a chat assistant needs to work on this module):
Last changed: <date> by <session/task>

--- HANDOFF TEMPLATE ---
# Handoff: <task id>: <date>
## 1. What was done (plain English)
## 2. Files changed (path: why)
## 3. Public API added/changed (exact signatures)
## 4. Tests (new tests; total passing/failing before → after)
## 5. Self-review findings (checks run; mistakes found and fixed)
## 6. New numbers/thresholds and their sources
## 7. Known issues / TODO / open questions
## 8. Next task, plus the CHAT KIT for it (exact file list to paste into a chat)
## 9. How to verify by hand (commands + what you should see)
```

**What you should see if it worked:**
- A PR is merged.
- `docs/ARCHITECTURE_MAP.md`, `docs/PROJECT_STATE.md` and `docs/handoff/2026-10-24_session-A.md` exist.
- A `MODULE.md` sits beside each existing feature.
- The test count is the same as before, plus at least 1 new test.

**If it didn't:** copy the exact error text or the failing test name and paste it to me in chat. Don't let it "guess-fix" repeatedly.

---

## SESSION B: rotation engine (T1)

```
Read CLAUDE.md (especially WORKING RULES), docs/PROJECT_STATE.md, docs/ARCHITECTURE_MAP.md,
the latest file in docs/handoff/, and section 6.2 task T1 of docs/innovation-decision-2026-10.md.
Follow the working rules exactly.

TASK T1: FULL-YEAR ROTATION ENGINE (Layer 1, new module src/compute/rotation/)
- Build full-year rotations (Kharif-2 Aman → Rabi → Kharif-1) by CHAINING the existing per-crop risk
  calendar / water balance functions. Reuse them through their public API; do not duplicate logic.
- Crop table: data/reference/crops.csv with columns crop, variety_class, duration_days, sowing window
  per region, Kc stages (FAO-56), GDD needs, heat/cold limits, flood_tolerance_days,
  salt_ECt_dSm, salt_slope_pct (FAO-29 Maas–Hoffman), is_legume, plus source columns. Fill ONLY values
  you can cite from sources already in the repo; leave a blank + "NEEDS SOURCE" note otherwise and list
  them in Open questions (the research teammate will fill them).
- Feasibility: a rotation is infeasible in a year if crop N's harvest date + turnaround days exceeds
  crop N+1's latest sowing date (turnaround from the reference table, with a source).
- For each rotation × year (2001–2024) per district: feasible?, problem year? (any crop hits a
  problem in the existing risk logic), Kc-weighted irrigation need (mm, using the existing water
  balance; this is the never-cut Kc-weighted comparison), number of legumes.
- Summary per rotation: "problems in X of N years", irrigation mm in median and worst-20% years,
  legume count, all with provenance.
- Public API (document in MODULE.md): candidate_rotations(district) and
  evaluate_rotation(district, rotation, years) returning the summary, plus per-year details.

ACCEPTANCE TESTS (write them first)
1. A long-duration Aman followed by a mustard sowing window that ends before Aman harvest + turnaround
   is flagged infeasible.
2. Same inputs give identical outputs on repeated runs (deterministic).
3. The existing Kc-weighted comparison tests still pass unchanged.
4. On a synthetic 3-year weather fixture, "problems in X of N" equals a hand count written in the test.
5. Every numeric field in the summary has a provenance object.

Then run SELF-REVIEW (same checklist as in CLAUDE.md / Session A Part 5), fix anything found, write
docs/handoff/<today>_T1.md with the HANDOFF TEMPLATE, update PROJECT_STATE.md (T1 status),
MODULE.md, AI_USE.md, print the report in chat, commit on branch t1-rotation, open a PR, and merge
only if all tests pass.
```

**What you should see:** a new `src/compute/rotation/` folder containing `MODULE.md`, `data/reference/crops.csv` (some cells marked NEEDS SOURCE is fine), at least 5 new tests passing, a handoff report, and a merged PR.

**If it didn't:** paste me the failing test name and its error.

---

## SESSION C: farmer priorities (T2)

```
Read CLAUDE.md (WORKING RULES), docs/PROJECT_STATE.md, the latest docs/handoff/ report,
src/compute/rotation/MODULE.md, and task T2 in docs/innovation-decision-2026-10.md section 6.2.

TASK T2: FARMER PRIORITIES (Layer 1 module src/compute/priorities/ + API endpoint)
- Inputs: weights for save_water, soil_health, lowest_risk, flood_safety (0–1, normalised to sum 1).
- Metrics come ONLY from the rotation module's public API: irrigation worst-20% (lower is better),
  legume count (higher is better), problem-year share (lower is better), flood_safety (for now the
  problem-year share for flood-related problems only; leave a TODO hook for the field water profile
  from task T3).
- Min-max normalise each metric across the candidate rotations, compute a transparent weighted score,
  and return each component (raw value, normalised value, weight, contribution) so the UI can show
  the reasoning. No hidden factors.
- API: POST /rotation/rank {district, weights} → ranked rotations with components and provenance.
  Update web/mock/ with a matching example JSON.

ACCEPTANCE TESTS (write first)
1. Property test: raising save_water never moves a higher-irrigation rotation above a lower-irrigation
   one when all other metrics are equal.
2. Weights that don't sum to 1 are normalised; all-zero weights return a clear error.
3. Contributions sum to the total score (within 1e-9).
4. API contract test for /rotation/rank.

Then SELF-REVIEW, handoff report docs/handoff/<today>_T2.md, update PROJECT_STATE.md, MODULE.md,
AI_USE.md, print the report in chat, branch t2-priorities, PR, merge only if tests pass.
```

---

## When your Claude Pro limit runs out: how to continue in plain chat

Paste these into the chat, **in this order**. You don't need the whole repo.

1. `docs/PROJECT_STATE.md` (where the whole project stands)
2. The newest file in `docs/handoff/` (what happened last, and the CHAT KIT for the next task)
3. The `MODULE.md` of the feature you want to work on (e.g. `src/compute/drought/MODULE.md`)
4. That module's code files and its `tests/<feature>/` files
5. Only if the module.md says it's needed: `src/compute/common/` files or one other module's `MODULE.md`

Then say: *"Continue task TX using this chat kit."*

I'll give you the code as complete files to replace, plus the tests, and ask you to run `pytest tests/<feature>` and paste the result back.
