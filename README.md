# Counterfactual Explorer · V3

**The nearest counterfactual is not necessarily the nearest feasible counterfactual.**

An interactive, local Streamlit demo for a university XAI seminar: **“Counterfactual
Explanations: What Would Need to Change the Prediction?”** Originally named
AI-CounterFactualX, this project uses a tiny synthetic application-screening model
so the prediction, counterfactual search, and feasibility assumptions can all be
explained in two minutes. No training, database, backend service, or API key is needed.
After installation, the demo works offline; the paper hyperlink is optional reading.

## V3: Basic and Advanced

**Results first; details on demand.** V3 preserves the V2 dashboard, classifier,
distance formula, threshold enumeration, and validated default results. It adds
metric sensitivity and scenario experiments without stacking more main sections.

The compact **Basic / Advanced** switch changes only the available tabs:

- **Basic (default):** Decision Boundary, Search Process, Candidates.
- **Advanced:** Sensitivity Analysis, Scenario Comparison.

Both modes share the input row, prediction, and optimal-CF cards. Switching modes
does not reset input, normalization, custom limits, inspection selection, or search
step. Advanced displays the three normalization controls inline; Basic retains V2's
collapsed settings access. No additional application dependencies are needed.

- One input row with income, experience, certification, Generate, and Constraints.
- Compact prediction/condition badges and side-by-side **Closest CF** and
  **Closest Feasible CF** cards, populated immediately at startup.
- **Settings ⚙** popover for practical limits; collapsed **Additional Settings**
  for manual normalization scales, lambda, and optional immutable context.
- **Decision Boundary:** interactive certification selector, hover details,
  selected-candidate highlighting, and separate markers for both optima.
- **Search Process:** Original → Thresholds → Candidates → Evaluation →
  Feasibility → Result, with Previous Step, Next Step, and Reset controls.
  The actual default enumeration includes **all eight combinations**: four
  rejected points (including the original) and four accepted changes.
- **Candidates:** sortable, selectable compact table; feasible-only filter;
  horizontal distance-sensitivity bars; collapsed exact calculations.
- Mathematical Details, Search Algorithm, and Assumptions & Limitations are
  collapsed by default. Cards stack on narrow screens; custom CSS is scoped
  to the dashboard's own elements rather than Streamlit internals.

Both cards **always** solve their labeled problems. The main Constraints switch
selects which result is active; it never changes the meaning of either card. The
right card labels its practical profile: **3 Months**, **No Certificate**, or
**Custom**. Selecting **No Constraints** activates the left card while retaining
the right card as an explicitly labeled practical comparison. With no feasible
solution the right card reports that even when constraints are OFF.

Selecting a table row or candidate dropdown highlights the same application and
navigates to its certification slice. Switching slices manually never places the
selected point on an incompatible slice. Changing original inputs, constraints,
scales, or lambda refreshes the real trace and resets the search step/selection;
changing the active constraint policy resets the presentation state as well.
Tab navigation retains inputs. Generate explicitly recalculates and restarts the
trace; it is not required to reveal initial results. Manual stepping is supported;
there is no simulated autoplay or optimization animation.

### Sensitivity Analysis

Smaller normalization scales make changes to that feature more expensive. This
changes **distance**, not prediction thresholds or feasibility assumptions.
The horizontal chart sorts by current distance, marks the unconstrained optimum,
and distinguishes practical feasibility by both color and hatching. A compact
table compares default/current distances and feasible rankings under the profile
shown on the right card.

For original `(24, 2, 0)`, changing only experience normalization from **5** to **0.5**:

| Stable dashboard ID | Application | Default distance | Modified distance |
|---|---|---:|---:|
| CF1 | `(25, 3, 0)` | 0.30 | 2.10 |
| CF2 | `(25, 2, 1)` | 1.10 | 1.10 |
| CF3 | `(24, 3, 1)` | 1.20 | 3.00 |
| CF4 | `(25, 3, 1)` | 1.30 | 3.10 |

The dashboard reports **“Optimal CF changed: CF1 → CF2”**. All predictions remain
unchanged. Tied optima use deterministic sparsity/feature-value tie-breaking;
the insight explicitly identifies a tie instead of implying a strictly better point.

### Scenario Comparison

All rows are calculated from the same current input and metric:

| Scenario | Practical constraints | Default result |
|---|---|---|
| No Constraints | None; domains and immutable context still mandatory | `(25, 3, 0)`, d = 0.30 |
| 3 Months | Income +5, experience +0.25, certification allowed | `(25, 2, 1)`, d = 1.10 |
| No Certificate | Same horizon, obtaining certification disallowed | No feasible CF |
| Custom | User-configured limits in Settings ⚙ | Computed dynamically |

Income and experience cannot decrease in practical scenarios. Editing a limit
selects **Custom**; switching to a preset never overwrites the saved Custom
configuration. The scenario selector and Basic's Constraints toggle are synchronized.

For the default **No Certificate** scenario, only income can reach a new passing
condition; experience cannot reach 3 within +0.25 years and certification cannot
be obtained. Income alone is insufficient. The no-solution message is scoped to
that scenario, not to all possible horizons or constraints. Missing distances
are displayed as a dash, not infinity or a fabricated recommendation.

### Optimality explanation and reset

**Why this counterfactual?** is collapsed and computed on demand. It shows current
threshold changes/costs, reachable conditions, eligible combinations, exclusions,
and the minimum eligible distance. It handles changed inputs, scales, permissions,
already-accepted inputs, and no-solution cases. In Basic it is nested in Mathematical
Details; Advanced provides it within each analytical tab.

**Settings → Reset to Defaults** restores the full worked example: `(24, 2, 0)`,
scales `(10, 5, 1)`, lambda 10, default three-month limits, Basic mode, and original
search/selection state. No ineffective time-horizon slider is included: limits
are explicit assumptions rather than derived from an unused time control.

## Installation and execution

Requires **Python 3.11+**. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, normally **http://localhost:8501**.
On Windows activate with `.venv\Scripts\activate` instead. If using `uv`, the
equivalent setup is `uv venv --python 3.12` followed by
`uv pip install -r requirements.txt` and the same activation/run commands.
Direct dependencies are version-pinned in `requirements.txt`.

Run all tests:

```bash
python -m pytest -q
```

For a headless launch:

```bash
python -m streamlit run app.py --server.headless=true --server.address=127.0.0.1
```

Streamlit usage telemetry is disabled in `.streamlit/config.toml`. All graphs
are rendered locally; no external images, fonts, or model services are required.

## Two-minute live demo

1. **0:00–0:20:** Keep `(income, experience, certification) = (24, 2, 0)`.
   The original is **Rejected**, satisfying **0 / 3** conditions.
2. **0:20–0:40:** Compare the two cards immediately: nearest valid `(25, 3, 0)`,
   distance **0.30**, versus nearest feasible `(25, 2, 1)`, distance **1.10**.
3. **0:40–1:00:** Toggle **Constraints** OFF and ON.
   With the three-month limits ON, the recommendation becomes `(25, 2, 1)`,
   distance **1.10**: an extra year of experience cannot fit within a 0.25-year limit.
4. **1:00–1:25:** Switch to Advanced → Sensitivity Analysis; change experience
   normalization from **5** to **0.5**. The closest valid point becomes CF2;
   CF1's distance rises to **2.10**. Predictions have not changed.
5. **1:25–1:45:** Open Scenario Comparison and select **No Certificate**.
   No feasible counterfactual exists; expand **Why this counterfactual?** for the
   current calculation. Other scenarios retain their own results.
6. **1:45–2:00:** Select **No Constraints** or restore defaults. Conclude: metric
   and constraints determine the recommendation; acceptance alone is not actionability.

Constraints start **enabled**. Changing any input, scale, lambda, or feasibility
setting immediately recomputes the results, including before Generate is clicked. The
table remains sortable and includes infeasible accepted candidates for comparison.

## Model and mathematical formulation

An application is `x = (I, E, C)`:

| Feature | Domain | Condition | Unit |
|---|---|---|---|
| Income `I` | Nonnegative, finite continuous value | `I >= 25` | Million VND/month |
| Experience `E` | Nonnegative, finite continuous value | `E >= 3` | Years |
| Certification `C` | `{0, 1}` | `C == 1` | Binary |

The classifier is:

```text
f(I, E, C) = 1 if 1[I >= 25] + 1[E >= 3] + 1[C = 1] >= 2; otherwise 0.
```

`1` means Accepted; `0` means Rejected. Optional birth year is immutable contextual
information: users may edit it for the original, but generated applications retain
it exactly. It never enters prediction, distance, or sparsity.

The educational objective inspired by counterfactual optimization is:

```text
L(x') = lambda * 1[f(x') != 1] + d(x, x')
d(x, x') = |I - I'| / 10 + |E - E'| / 5 + |C - C'|
```

Default `lambda = 10`. All three positive normalization factors and lambda
are adjustable in advanced settings. Scales are **manually chosen synthetic
normalization factors, not median absolute deviations (MADs) computed from data**.

The actual recommendation solves the constrained interpretation:

```text
minimize d(x, x')
subject to f(x') = 1,
           valid feature domains and unchanged immutable attributes,
           practical feasibility limits, when enabled.
```

**Target validity is enforced before minimizing distance.** Lambda and `L` are
diagnostics, not a substitute for the acceptance constraint. Lambda 10 does not
guarantee a valid minimum of the penalty objective for arbitrary input/scales:
the unchanged rejected original has `L = lambda`, while all accepted points
could have distances greater than lambda. For every generated accepted candidate,
prediction loss is zero, so `L = distance` regardless of lambda.

Metrics:

- **Validity:** candidate prediction equals target 1.
- **Proximity:** normalized Manhattan distance from the current original.
- **Sparsity:** number of predictive features changed (0–3).
- **Feasibility:** satisfies the assumed practical limits and immutable context.
- **Changed features:** original values, new values, signed differences, and units.

## Threshold-aware enumeration

Income and experience are continuous. Search does **not** use fixed steps such as
0.5 or 0.25. Numeric input step sizes only help edit values in the UI.

```text
validate the original, scales, lambda, and feasibility limits
if original already Accepted: return no recourse needed
for each feature:
    include its original value
    if its condition fails: include the exact minimum satisfying value
for point in itertools.product(all unique feature-value sets):
    preserve immutable context and validate domains
    compute validity, distance contributions, sparsity, L, changes, feasibility
    record the point in the complete diagnostic trace
exclude unchanged original and rejected points from generated explanations
rank accepted candidates by distance
select the closest eligible candidate (filter by feasibility when enabled)
if none is eligible: explicitly report no feasible counterfactual
```

There are at most **eight** combinations. Already satisfied conditions never
receive unnecessary changes. Distance ties prefer lower sparsity, then a stable
feature-value ordering, shared by ranking and recommendation.
`enumerate_search` is the shared implementation used by `generate_counterfactuals`
and the step viewer, rather than an independent demonstration sequence. Its
`SearchTrace` retains product-order evaluations and distance-ranked accepted
changes. Rejected trace IDs are `Tn`.
Already-accepted originals stop before enumeration with empty result/trace lists.

V3 enumerates once per original application with default scales to establish stable
dashboard CF IDs. `reassess_trace` reuses those applications and IDs when scales,
lambda, or constraints change; it does not call `itertools.product` again. The
unmodified V2 enumeration API still assigns IDs by its requested metric's ranking
for compatibility. Dashboard IDs are identities within the current original, not
current ranks; changing the original establishes a new set of identities.

### Why this enumeration finds an optimum here

Acceptance depends only on three monotonic threshold conditions. Given any
accepted application, keep the original value for unnecessary changes or conditions
already satisfied in the original; for any newly satisfied condition, replace
its value with its exact threshold. This preserves sufficient passing conditions
and cannot increase positively weighted Manhattan distance. Therefore a closest
accepted point exists among the enumerated combinations. The same projection
preserves these particular practical constraints: increases get smaller, experience
never falls below the original, and certification never needs new permission.

This is a guarantee for **this threshold classifier, distance, and constraint set**,
not for arbitrary black-box classifiers or arbitrary feasibility restrictions.

## Practical feasibility

Default **three-month** assumptions, relative to the current original:

```python
max_income_increase = 5.0       # million VND/month
max_experience_increase = 0.25  # years; experience also cannot decrease
can_obtain_certification = True
income_cannot_decrease = True   # applied by V3 practical scenario definitions
```

These limits are adjustable. Turning the toggle OFF ignores only optional
practical limits; domain validation and immutability always apply. The table
continues to report practical feasibility even when it is not enforced for
recommendation. No feasible solution is explicitly reported rather than silently
substituting an infeasible point.

These are synthetic assumptions, **not verified real-world employment guarantees**.

## Expected default results

For original `(24, 2, 0)` the following applications are generated automatically:

| ID | Income | Experience | Certification | Prediction | Distance | Sparsity | Three-month feasible |
|---|---:|---:|---:|---|---:|---:|---|
| CF1 | 25 | 3 | 0 | Accepted | 0.30 | 2 | No |
| CF2 | 25 | 2 | 1 | Accepted | 1.10 | 2 | Yes |
| CF3 | 24 | 3 | 1 | Accepted | 1.20 | 2 | No |
| CF4 | 25 | 3 | 1 | Accepted | 1.30 | 3 | No |

Worked calculations:

```text
CF1: |24-25|/10 + |2-3|/5 + |0-0| = 0.10 + 0.20 + 0 = 0.30
CF2: |24-25|/10 + |2-2|/5 + |0-1| = 0.10 + 0    + 1 = 1.10
CF3: |24-24|/10 + |2-3|/5 + |0-1| = 0    + 0.20 + 1 = 1.20
```

The unconstrained optimum is **CF1**; the feasible optimum is **CF2**.
The separate excessive-income example `(500, 3, 0)` is accepted, has distance
**47.80**, and is infeasible under defaults. It is not part of optimal enumeration.
That example adapts to the current original and settings.

## Architecture and verification

```text
app.py                    Shared dashboard shell, V2 Basic views, authoritative result cache
dashboard_state.py        Persistent mode/scenario/custom settings and reset callbacks
analytics_views.py        Sensitivity, scenario comparison, on-demand optimality explanations
dashboard_details.py      Collapsed mathematical explanations, assumptions, attribution
visualization.py          Exact Plotly regions, point layers, distance-sensitivity bars
core/model.py             Validated Application and two-of-three classifier
core/distance.py          Manual normalization, contributions, sparsity, change descriptions
core/constraints.py       Relative practical limits and immutable checks
core/generator.py         Shared threshold enumeration/trace, ranking, recommendation
core/sensitivity.py       Reassess cached points; stable identity, threshold costs, ranking insight
core/scenarios.py         Presets and per-scenario results using the same evaluator/selector
tests/test_model.py       Thresholds, domains, contextual independence
tests/test_distance.py    Worked examples, scales, changed-feature metrics
tests/test_constraints.py Relative limits, no-solution cases, immutable enforcement
tests/test_generator.py   Continuous inputs, validity-first selection, ranking, edge cases
tests/test_search_trace.py Complete unsuccessful/successful enumeration and trace consistency
tests/test_visualization.py Exact regions, certification slices, adaptive axes
tests/test_app.py         Streamlit AppTest: cards, controls, search sync, selection, context
tests/test_sensitivity.py  Metric example, stable IDs, tiny scales, ties, no regeneration
tests/test_scenarios.py    Presets, Custom isolation, empty/accepted states, invariants
tests/test_v3_app.py       Mode lifecycle, reset, scenario sync, metric updates, cache behavior
```

Business logic has no Streamlit dependency. Automated UI tests require no browser
or running server. Plotly views use exact rectangles: with `C = 0`, acceptance
requires both income and experience thresholds; with `C = 1`, either suffices.
Both slices share axis extents. Points and highlight overlays are filtered by
certification before plotting. The UI presents one selectable slice at a time.

V3 retains the complete V2 test suite and adds core/Streamlit AppTest coverage,
plus a headless Chromium check at **1366×768** and **390×844**: both default cards
and the beginning of the decision chart fit the desktop viewport, narrow-screen
cards stack without horizontal overflow, and tab/search/constraint interactions
work without browser errors. No browser automation package is required to run
the app or the pytest suite.

The browser check also exercises both analytical tabs, the required 0.5-scale
example, scenario switching, on-demand proof rendering, saved Custom settings,
and reset, with external page requests blocked. Floating-point distances that
exceed representable range are reported as validation errors rather than shown
as infinite recommendations. Very small positive scales within that range work normally.

## Academic context, limitations, and attribution

**Wachter et al. (2018):** the counterfactual optimization formulation and a
MAD-weighted distance approach motivate the seminar. Their paper explores
counterfactuals for black-box models, including Adam-based optimization experiments.

**Our educational implementation:** a synthetic two-of-three threshold classifier,
manually normalized Manhattan distance, exact threshold enumeration, and assumed
three-month practical limits. These choices are ours, not algorithms or synthetic
experiments attributed to the original paper. We do not reproduce its neural-network
experiments or its Adam optimizer.

Limitations:

- A synthetic classifier cannot represent realistic application-screening decisions.
- Income as a hiring feature can introduce unfair bias.
- A prediction change is not evidence of causality or a promise of acceptance in reality.
- Feasibility depends on the stated assumptions; distance does not capture all costs,
  effort, opportunity, fairness, or individual preferences.
- Threshold enumeration is specific to this model and these constraints.
- The UI displays rounded numbers; the algorithm uses unrounded floating-point values.

**Citation:** Wachter, S., Mittelstadt, B., & Russell, C. (2018).
*Counterfactual Explanations without Opening the Black Box: Automated Decisions
and the GDPR.* Harvard Journal of Law & Technology, 31(2), 841–887.
[arXiv:1711.00399](https://arxiv.org/abs/1711.00399).
