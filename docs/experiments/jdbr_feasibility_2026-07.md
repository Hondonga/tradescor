# Experiment record — JDBR initial feasibility test

**Status: DEVELOPMENT RESULT — CONSUMED. Promotion: BLOCKED.**
Do not tune parameters against this same data and report the new performance as independent evidence. Any future promotion decision must use fresh, unseen data.

---

## Experiment
JDBR (Jump Displacement Break‑Retest) initial feasibility test — does the confluence strategy show a directional edge on Jump indices?

## Data
- 8 days each of JD10, JD50, JD75, JD100 (cached `data/smc_matrix/v2-*` M1 → M5).
- JD25 not tested (no cached data).
- This is 8 days, not the ≥12 months the spec (§9) requires for a promotion decision. These results are feasibility only.

## Method
Event‑driven backtest implementing JDBR rules directly: qualifying jump (≥2·ATR displacement) → confluence zone (S&D origin ∩ broken‑level band) → M5 retest confirmation → structural stop → TP1 at nearest unswept swing with R:R ≥ 1.5 → forward‑simulated outcome (stop‑first on same‑bar ambiguity) → cost applied. Two backtests:

1. **Unpaired** (continuation vs fade, each on its own qualifying events).
2. **Paired** (identical event set for all directions, symmetric geometry, group‑level bootstrap CIs) — the methodologically clean directional test.

## Results

### Unpaired
| Version | Setups | Win rate | Expectancy | PF | t |
|---|---|---|---|---|---|
| Continuation | 70 | 42.9% | +0.094R | 1.16 | 0.62 |
| Fade | 82 | 20.7% | +0.159R | 1.20 | 0.50 |

Per‑symbol continuation vs fade disagreed (JD10 favored continuation, JD50 favored fade, JD100 favored neither). Controls were not paired (70 ≠ 82 events).

### Paired (identical 76 events, symmetric geometry, bootstrap CIs)
| Direction | Mean R | 95% CI (symbol‑block) | 95% CI (event‑grouped) |
|---|---|---|---|
| Continuation | +0.151R | [+0.006, +0.319] | **[−0.112, +0.447]** |
| Fade | +0.020R | [−0.189, +0.296] | [−0.277, +0.283] |
| Random | −0.013R | [−0.132, +0.128] | [−0.277, +0.250] |

**Continuation − Fade** difference = +0.132R, 95% CI (symbol‑block) = **[−0.274, +0.473]** → spans zero.

## Outcome
**No statistically reliable directional edge.**
- Continuation's event‑grouped CI spans zero.
- The continuation‑minus‑fade difference spans zero → direction adds no reliable information.
- Random ≈ 0, as expected.
- Under symmetric geometry, the fade result collapsed from +0.16R to +0.02R, confirming the earlier fade number was an artifact of asymmetric target selection, not a reversal edge.
- Per‑symbol ordering was unstable across the two backtests — a signature of noise, not signal.
- Sample far below the ≥200 trades / ≥8 independent periods promotion bar.

## Decision
JDBR demoted from proposed strategy to research hypothesis:
```
RESEARCH_ONLY
NOT_AUTO_ELIGIBLE
NOT_PAPER_SIGNAL_ELIGIBLE
NO_CONFIRMED_DIRECTIONAL_EDGE
```
Jump remains a market‑event / context module, not a trade generator.

## If a larger test is ever run
Only if 12+ months of history is cheap to obtain. Requirements: JD10/25/50/75/100, anchored walk‑forward, purged boundaries, realistic costs, **event‑level grouping** for CIs (not per‑trade), fresh untouched final holdout. Also required before trusting the confluence score: score‑bucket monotonicity (top vs bottom quintile), and component ablations (does S&D / broken‑level / FVG / sweep each add information, or only shrink the sample?). Treat the run as confirm‑or‑permanently‑reject — not a search for profitable settings. If it still shows inconsistent symbol direction, near‑zero expectancy, no score monotonicity, and no edge over random, archive JDBR as `REJECTED_NO_STABLE_EDGE`.
