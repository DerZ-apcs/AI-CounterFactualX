# Counterfactual Explorer

**The nearest counterfactual is not necessarily the nearest feasible counterfactual.**

An interactive, local Streamlit demo for a university XAI seminar: **“Counterfactual
Explanations: What Would Need to Change the Prediction?”** Originally named
AI-CounterFactualX, this project uses a tiny synthetic application-screening model
so the prediction, counterfactual search, and feasibility assumptions can all be
explained in two minutes. No training, database, backend service, or API key is needed.
After installation, the demo works offline; the paper hyperlink is optional reading.

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
2. **0:20–0:50:** Click **Generate Counterfactuals**. Point out the nearest
   valid application `(25, 3, 0)` and its distance **0.30**.
3. **0:50–1:20:** Toggle **Enable Real-world Constraints** OFF and ON.
   With the three-month limits ON, the recommendation becomes `(25, 2, 1)`,
   distance **1.10**: an extra year of experience cannot fit within a 0.25-year limit.
4. **1:20–1:45:** Compare the certification slices and inspect a candidate's
   distance calculation. The prediction-valid and feasible labels are different concepts.
5. **1:45–2:00:** Disallow obtaining certification: no feasible counterfactual
   exists. Conclude with the central message above.

Constraints start **enabled**. After the first generation, changing any input,
scale, lambda, or feasibility setting immediately recomputes the results. The
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
    skip unchanged original and rejected points
    compute validity, distance contributions, sparsity, L, changes, feasibility
rank accepted candidates by distance
select the closest eligible candidate (filter by feasibility when enabled)
if none is eligible: explicitly report no feasible counterfactual
```

There are at most **eight** combinations. Already satisfied conditions never
receive unnecessary changes. Distance ties prefer lower sparsity, then a stable
feature-value ordering; IDs reflect the current ranking.

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
app.py                    Streamlit inputs, comparison table, recommendations, teaching notes
visualization.py          Exact Plotly regions and certification-specific point layers
core/model.py             Validated Application and two-of-three classifier
core/distance.py          Manual normalization, contributions, sparsity, change descriptions
core/constraints.py       Relative practical limits and immutable checks
core/generator.py         Threshold enumeration, evaluation, ranking, recommendation
tests/test_model.py       Thresholds, domains, contextual independence
tests/test_distance.py    Worked examples, scales, changed-feature metrics
tests/test_constraints.py Relative limits, no-solution cases, immutable enforcement
tests/test_generator.py   Continuous inputs, validity-first selection, ranking, edge cases
tests/test_visualization.py Exact regions, certification slices, adaptive axes
tests/test_app.py         Streamlit AppTest: controls, reactive results, errors, context
```

Business logic has no Streamlit dependency. Automated UI tests require no browser
or running server. Plotly views use exact rectangles: with `C = 0`, acceptance
requires both income and experience thresholds; with `C = 1`, either suffices.
Both slices share axis extents. Points are filtered by certification before plotting.

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
