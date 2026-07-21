# Jump Displacement Break‑Retest (JDBR) — Strategy Design Spec

**Status (2026‑07‑20): DEMOTED TO RESEARCH HYPOTHESIS after initial feasibility test.**

```
RESEARCH_ONLY
NOT_AUTO_ELIGIBLE
NOT_PAPER_SIGNAL_ELIGIBLE
NO_CONFIRMED_DIRECTIONAL_EDGE
```

Do **not** build JDBR as an active Jump signal, add Auto routing, register paper signals, generate ML features, or show Workspace trade recommendations for it. The existing Jump event engine may remain as a **market‑event / context module** only (see §13). The initial feasibility backtest found post‑cost expectancy statistically indistinguishable from zero with no stable directional edge — which the spec's own stop condition (§9) says blocks promotion. Full result frozen in `docs/experiments/jdbr_feasibility_2026-07.md` (CONSUMED — do not tune against that data and re‑report as independent evidence).

**Target family:** Jump (JD10 / JD25 / JD50 / JD75 / JD100).
**Combines:** Breakout‑and‑Retest + SMC/ICT + Supply & Demand, as *three descriptions of one event*, not three independent signals.
**Author note:** grounded in the existing `strategies/derived/jump_dex_post_event.py` engine, which already provides event classification, cooldown, post‑event structure, zone building, confirmation, structural stop, targets, and R:R. JDBR formalizes the confluence and geometry on top of that engine.

---

## 1. Why Jump, and why these three tools

### Market model
Jump indices are low‑volatility random walks punctuated by occasional **jumps** — sudden moves many multiples of the normal tick, occurring at a fixed *average* interval. Between jumps the series is effectively driftless (no edge). The **only** structural feature is the jump itself: a large, one‑directional displacement that temporarily breaks the local random walk.

Empirical support (this project, 8 days × 4 Jump symbols, ~9k observations): trend/breakout logic showed a faint positive tilt on Jump (t ≈ 0.9 at zero cost) — the weakest of "not nothing," and **not** statistically significant. Every other family and strategy was indistinguishable from random. So:

> **JDBR does not claim a signal edge. Its thesis is narrow: a jump is an information event; the highest‑quality continuation setups occur when the jump's displacement, its supply/demand origin, and the broken structural level all coincide, and price retraces to that confluence before continuing. The three tools exist to make the filter strict and the geometry clean — improving R:R and reducing false entries — not to manufacture predictive power.**

This honesty is load‑bearing: it dictates conservative acceptance gates (§9) and forbids live deployment before walk‑forward evidence.

### The three tools map to one event
A single qualifying jump produces all three signatures simultaneously:

| Lens | What it names in the jump | Role in JDBR |
|---|---|---|
| **SMC / ICT** | The jump *is* the displacement candle; it produces a Break of Structure / Market Structure Shift and typically a Fair Value Gap; often preceded by a liquidity sweep | **Direction + confirmation** |
| **Supply & Demand** | The consolidation/base immediately before the jump is the **origin zone** — demand (up‑jump) or supply (down‑jump) | **Where to enter (the zone)** |
| **Breakout‑and‑Retest** | The jump **breaks** a prior structural swing; price later **retests** the broken level | **Trigger + entry geometry** |

Combining them means requiring that all three agree about the *same* zone. That is a confluence filter, not an AND of three arbitrary indicators.

---

## 2. The unified setup, in one sentence

> A qualified jump breaks a structural swing in its direction, originates from a fresh unmitigated supply/demand base, and leaves a fair‑value gap; price then retraces into the confluence zone (broken level ∩ S&D origin ∩ FVG); on a completed M5 structure‑confirming close inside that zone, enter in the jump's direction, stop beyond the zone's protected extreme, target the next unswept liquidity with validated R:R.

---

## 3. Lifecycle (stages, in strict order)

Each stage must complete on **closed candles only** (no intrabar, no lookahead). Stage names mirror the existing engine's state machine so JDBR can reuse it.

1. `DATA_LOADING` — require H1 ≥ 20, M15 ≥ 40, M5 ≥ 60 completed candles.
2. `WAITING_FOR_EVENT` — no qualified jump yet. Detected via `classify_derived_event` (existing).
3. `EVENT_LOCKED` — a jump qualifies: displacement magnitude ≥ `min_jump_atr` × ATR and range/body ratios pass. Direction = jump direction. Record `event_origin` (pre‑jump base) and `broken_level` (the swing the jump traded through).
4. `COOLDOWN` — post‑jump volatility must settle (`evaluate_event_cooldown`). No entry while the market is still expanding from the jump, and no entry inside the statistical window where the *next* jump is likely (see §7 jump‑risk).
5. `WAITING_FOR_RETRACE` — price must retrace toward the confluence zone. If price runs away without a retrace, the setup expires (no chase).
6. `IN_CONFLUENCE_ZONE` — price trades into the zone defined in §4. Zone must be **unmitigated** (not previously tapped) to reach this stage cleanly.
7. `WAITING_FOR_CONFIRMATION` — await a completed M5 confirmation (§5).
8. `PLAN_VALIDATION` — build stop, targets, R:R, chase, confluence score; all invariants (§6) must pass.
9. `READY_TO_BUY` / `READY_TO_SELL` — full plan emitted.
10. Terminal: `TOO_LATE` (chase exceeded), `EXPIRED` (retrace/confirmation window elapsed), `INVALIDATED` (zone broken / opposite event).

---

## 4. The confluence zone (Supply & Demand ∩ Breakout level ∩ FVG)

Compute three sub‑zones, then require overlap.

- **S&D origin zone** — the last opposing‑candle base before the jump (existing `build_post_event_zone` / supply_demand `_active_zone`). Quality scored by: freshness (untouched since formation), departure strength (jump size in ATR), and mitigation depth. Reject if touched more than `max_zone_touches`.
- **Broken‑level band** — the structural swing the jump traded through, ± `retest_band_atr` × ATR. This is the classic breakout‑retest level.
- **Displacement FVG** — the fair‑value gap left by the jump candle sequence (existing ICT FVG detector). Optional but scored.

**Confluence zone** = intersection of the S&D origin zone and the broken‑level band. The FVG is a **scoring bonus**, not a hard requirement (jumps do not always leave a clean gap). If S&D origin and broken level do not overlap, **no setup** — this is the core filter that makes JDBR selective.

---

## 5. Entry trigger (Breakout‑Retest confirmation)

Inside `IN_CONFLUENCE_ZONE`, require a **completed M5 confirmation** that the retest held:

- A completed M5 candle closes back in the jump's direction after tagging the zone (an M5 micro‑BOS / rejection), via existing `confirm_post_event`.
- Entry price = confirmation close (or the confirmed retrace level), locked once (`lock_post_event_entry`) — never moved.
- **Chase guard:** if current price is already more than `max_chase_atr` × ATR beyond entry, state → `TOO_LATE`. No chasing.

---

## 6. Geometry and trade‑ready invariants

**Direction:** jump direction only. Never counter‑trend on Jump (fading a jump has no structural basis and failed empirically).

**Entry:** locked confirmation close inside the confluence zone.

**Stop:** structural, beyond the protected extreme of the confluence zone (below demand / above supply), plus `stop_buffer_atr` × ATR. Existing `build_structural_stop`. Reject if stop distance > `max_stop_atr` × ATR.

**TP1:** nearest **unswept** liquidity / structural level in the jump direction, hierarchy: M5 structural → M15 structural → H1 structural. (Reuse the volatility engine's causal target engine; do **not** allow already‑swept levels.)

**TP2:** next structural level beyond TP1.

**R:R:** TP1 reward / risk ≥ `min_tp1_rr` (start 1.5). Validated by existing `validate_reward_risk`.

**Trade‑ready invariants (all must hold, else `PLAN_VALIDATION`, never a partial plan):**
1. Eligible Jump family + sufficient completed history.
2. Qualified locked jump event.
3. Confluence zone exists (S&D ∩ broken level overlap).
4. Zone unmitigated at confirmation.
5. Completed M5 confirmation in the jump direction.
6. Entry locked and non‑retroactive.
7. Structural stop valid and within max distance.
8. TP1 unswept, R:R ≥ minimum.
9. Chase within limit.
10. Confluence score ≥ `min_confluence_score` (§8).
11. Not inside the next‑jump risk window (§7).

If any fails, the actionable plan (entry/stop/TP) **must be absent** from the contract — enforced at the contract level, mirroring the volatility engine's `PLAN VALIDATION` behavior. This directly prevents the "TP shown without entry/stop" bug class.

---

## 7. Jump‑specific risk controls

- **Next‑jump window:** because jumps occur at a known *average* interval, estimate ticks since last jump; if within the high‑probability band for the next jump, block new entries (`AT_JUMP_RISK` state). A jump against an open position is the dominant loss mode.
- **Cooldown:** no entry until post‑jump volatility normalizes.
- **One setup per event:** a new qualifying jump cancels/archives prior setups from the previous event (existing `cancel_active_setups_for_new_event`).
- **No counter‑jump trades.**

---

## 8. Confluence score (ranking, not a gate override)

A 0–100 score, for ranking and for the ML evidence layer later — **it never creates a trade, only filters/ranks ones that already pass all invariants:**

| Component | Weight | Full credit when |
|---|---|---|
| Displacement strength | 25 | jump ≥ 2× `min_jump_atr` |
| S&D zone freshness | 20 | zone completely unmitigated |
| Breakout‑level overlap tightness | 20 | S&D origin and broken level overlap ≥ 70% |
| FVG present & unfilled | 15 | clean displacement gap remains |
| Liquidity sweep before jump | 10 | prior liquidity taken then reversed |
| R:R headroom | 10 | TP1 R:R ≥ 2.5 |

`min_confluence_score` starts at 60. Tune only inside training folds (§9), never on the holdout.

---

## 9. Validation plan and acceptance gates

**Reachability first.** JDBR cannot enter Auto until it passes the chronological setup‑proof harness both directions. The current Jump failure is `INSUFFICIENT_HISTORY` in the fixtures — so step 1 is building Jump fixtures with adequate depth (H1 ≥ 20, M15 ≥ 40, M5 ≥ 60, plus a scripted qualifying jump + retrace + confirmation), then proving `REACHABLE` for buy and sell.

**Then evidence, via walk‑forward — not a single split:**
- Generate JDBR setups across JD10/25/50/75/100 over ≥ 12 months.
- Anchored expanding walk‑forward, 15‑day steps, purge + embargo = max trade‑resolution horizon.
- **Acceptance gates (all required before any live paper use):**
  1. ≥ 200 resolved trades across ≥ 8 independent periods.
  2. Positive expectancy in ≥ 60% of folds.
  3. Top‑confluence‑quintile expectancy > bottom quintile in ≥ 75% of folds (proves the score means something).
  4. Expectancy survives realistic Jump spread/cost.
  5. One — and only one — look at a fresh holdout, consumed once.
- **Stop condition:** if pooled expectancy after costs is statistically indistinguishable from zero, JDBR is **not** promoted. That is an acceptable outcome — the market may simply not permit it, and the empirical baseline says that is the likely result.

---

## 10. Parameters (initial, all tunable in‑fold only)

```
min_jump_atr            = 2.0     # jump magnitude vs ATR to qualify the event
retest_band_atr         = 0.15    # broken-level band half-width
max_zone_touches        = 0       # confluence zone must be unmitigated
min_tp1_rr              = 1.5
max_chase_atr           = 0.35
stop_buffer_atr         = 0.12
max_stop_atr            = 3.0
min_confluence_score    = 60
next_jump_block_pct     = 0.80    # block entries in the top 20% of the inter-jump interval
```

---

## 11. How it plugs into the existing engine

JDBR is largely a **formalization + confluence layer** over `evaluate_jump_dex_post_event`, which already produces event, cooldown, structure, zone, execution zone, confirmation, entry, stop, targets, R:R, and chase. Concrete deltas:

1. Add the **breakout‑level band** and require S&D‑origin ∩ broken‑level overlap to form the confluence zone (new gate before `WAITING_FOR_CONFIRMATION`).
2. Add the **confluence score** and the `min_confluence_score` invariant.
3. Add the **next‑jump risk window** block.
4. Route TP1 through the causal unswept‑liquidity target engine (shared with the volatility engine) for a clean hierarchy.
5. Enforce actionable‑fields‑absent‑unless‑valid at the contract layer.
6. Build Jump reachability fixtures and prove both directions.

No new market data, no ML, no counter‑trend logic. The reversal scenarios already in `_scenarios` (e.g. `up_event_bearish_rejection`) should be **disabled for JDBR v1** — continuation only — until there is separate evidence for reversals.

---

## 12. Honest caveats

- The empirical base rate says mechanical edges on synthetics do not survive costs. JDBR's only defensible claim is *better filtering and geometry on the one real structural feature (the jump)*. Treat §9's stop condition as the likely outcome, not a formality.
- The faint Jump trend tilt (t ≈ 0.9) was **not** significant and came from 8 days of data. It motivates the direction (continuation, not reversal) but is not evidence of profitability.
- Confluence scoring feels precise but adds parameters; every parameter is an overfitting surface. Keep them frozen outside training folds.
- Do not connect JDBR to live paper scoring, ML filtering, or Auto before walk‑forward + fresh‑holdout evidence exists.
