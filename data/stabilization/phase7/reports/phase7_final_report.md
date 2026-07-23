# Phase 7 Final Report: Strategy Failure Post-Mortem and One New Hypothesis Design

1. **phase7 process status**: COMPLETE

2. **working branch**: tradescor-phase7-strategy-failure-postmortem

3. **starting phase6 commit**: 2ab0c681dd0f98066144e02224497865d798a185

4. **final phase7 commit**: 8d2babf27e2ec9bf9ea2f39b3f12385445254408

5. **phase5 frozen integrity result**: PASS -- all file_checksums in experiment_record.json verified byte-identical; strategy_verdict still REJECTED_NO_EDGE_AFTER_COSTS (data/stabilization/phase7/baseline/phase5_reference_manifest.json)

6. **phase5 holdout status**: SEALED, opened_at=None, result=None -- unchanged, never opened

7. **phase6 external verification result**: PROVIDER_UNAVAILABLE for all 4 items (3 Deriv-dependent Python tests, R_75/Jump/GBPUSD-switching browser smoke) -- Deriv confirmed unavailable at check time (DerivAPIError: Deriv returned no active symbols.); no application logic changed as a result; tracked as open external verification debt, never conflated with any strategy verdict (data/stabilization/phase7/diagnostics/phase6_external_verification.json)

8. **postmortem dataset integrity result**: PASS -- 1093 rows (625 BUY / 468 SELL), 8 folds, 0 duplicate setup_ids, csv checksum matches the frozen manifest, gross/net R means match published Phase 5 evidence exactly

9. **primary signal quality finding**: The strategy showed directional information relative to the random control, but paired opposite-direction superiority was not statistically conclusive. (same-minus-opposite mean=0.2287, CI=[-0.0233, 0.4796]; only 2/8 folds had BUY and SELL net expectancy on the same side of zero)

10. **primary cost sensitivity finding**: The flat conservative cost (0.10R per trade) consumes 134.8% of the 0.0742R average gross edge -- the edge is thinner than the cost applied to erase it. 66.0% of individual trades had a gross edge smaller than the flat 0.10R cost. No cost assumption was lowered to produce this finding; costs were fixed before any outcome was computed (preregistration commitment).

11. **primary execution geometry finding**: 67.7% of stopped trades had some favorable excursion before reversing to stop, and 47.4% of all setups moved favorably but never reached TP1 -- friction/geometry, not pure directional wrongness, explains a large share of underperformance. realized_mae_r was NOT USABLE (constant -inf sentinel, never populated during the Phase 5 causal replay) -- disclosed as a genuine limitation of the frozen artifact, not fabricated.

12. **primary stability finding**: Only 37.5% of folds (3/8) were net positive; top single fold carried 51.0% of total profit; longest chronological losing sequence was 28 consecutive setups; maximum drawdown 114.1R was never recovered within the dataset.

13. **top documented failure modes**: 
  - DIRECTIONAL_FAILURE (n=710, 65.0%, net_r=-781.0)
  - LONG_LOSING_SEQUENCE (n=523, 47.8%, net_r=-568.3)
  - TARGET_NOT_REACHED_DESPITE_POSITIVE_MFE (n=518, 47.4%, net_r=-558.8)
  - STOP_TOO_TIGHT_RELATIVE_TO_NOISE (n=170, 15.6%, net_r=-187.0)
  - STOP_TOO_WIDE_RELATIVE_TO_TARGET (n=161, 14.7%, net_r=-177.1)

14. **number of candidate hypotheses generated**: 5

15. **selected hypothesis**: candidate_1_max_stop_distance_atr_ceiling

16. **selection rationale**: An unusually wide stop relative to the prevailing M5 ATR(14) at decision time plausibly indicates either a lower-quality/less-precise structural pullback (the protected swing sits unusually far from the retracement entry) or an entry taken further into an already-extended move than the typical setup. This is consistent with the observed pattern in the consumed data: the widest-stop quintile (stop_distance_atr in (3.975, 10.460]) is the only one of five quintiles across all three tested variables whose grouped 95% confidence interval excludes zero (mean -0.327R, CI [-0.480, -0.146], 0% positive folds across all 8 folds), while the tightest-stop quintile is the single best-performing bucket (+0.175R).

17. **exact single change**: Reject a setup the parent engine would otherwise mark TRADE_READY if stop_distance_atr > 3.975, where stop_distance_atr = abs(entry - stop) / mean(high - low) over the trailing 14 completed M5 candles up to and including the decision candle.

18. **research variant id**: volatility_structure_pullback_hypothesis_v2

19. **production engine diff result**: PASS -- analysis/volatility_structure_pullback_engine.py is byte-identical to its Phase 6 committed version (test_phase7_research_variant.py::test_research_variant_never_overwrites_the_parent_strategy_module); the research variant is a new, separate module that calls it unmodified

20. **untouched history coverage**: 5.77 hours (2026-04-20T23:59:00Z to 2026-04-21T05:45:00Z) -- the only calendar window outside every excluded/embargoed range; unusable (engine requires >=20 completed H1 candles alone before evaluating a single decision point)

21. **excluded consumed windows**: 
  - 2025-10-15T00:00:00Z to 2026-04-13T23:59:00Z :: PHASE_5_RAW_PULL
  - 2026-04-14T00:00:00Z to 2026-04-20T23:59:00Z :: PHASE_5_EMBARGO
  - 2026-04-21T05:45:00Z to 2026-07-20T05:44:00Z :: ML_DATASET_CONSUMED
  - 2026-07-20T05:44:00Z to 2026-07-27T05:44:00Z :: ML_DATASET_EMBARGO

22. **untouched data checksum**: null -- no candle data was fetched or persisted (nothing to checksum); provider unavailable regardless

23. **experiment id**: phase7-r75-vsp-hypothesis-v2-stopatr-ceiling

24. **parent setup count**: NOT COMPUTED -- no untouched-history candidate universe existed to evaluate (Parts 14-17 not executed)

25. **variant retained setup count**: NOT COMPUTED -- same reason as item 24

26. **retention percentage**: NOT COMPUTED -- same reason as item 24 (consumed-data-only estimate was 80%, data/stabilization/phase7/postmortem/diagnostic_buckets.json, but this must never be read as an untouched-history retention figure)

27. **buy count**: NOT COMPUTED -- same reason as item 24

28. **sell count**: NOT COMPUTED -- same reason as item 24

29. **fold count**: NOT COMPUTED -- same reason as item 24

30. **conservative cost parent expectancy**: NOT COMPUTED (untouched-history) -- same reason as item 24

31. **conservative cost variant expectancy**: NOT COMPUTED (untouched-history) -- same reason as item 24

32. **variant minus parent result**: NOT COMPUTED -- same reason as item 24

33. **variant grouped confidence interval**: NOT COMPUTED -- same reason as item 24

34. **profit factor**: NOT COMPUTED -- same reason as item 24

35. **maximum drawdown**: NOT COMPUTED -- same reason as item 24

36. **positive fold percentage**: NOT COMPUTED -- same reason as item 24

37. **same minus opposite result**: NOT COMPUTED (untouched-history) -- the consumed-data figure is reported in item 9 for post-mortem context only, never as new validation evidence

38. **geometry control v2 result**: NOT COMPUTED (untouched-history) -- the corrected methodology itself was built and unit-tested (10/10 passed, data/stabilization/phase7/controls/control_methodology_v2.json) and is ready for the next Phase 7 extension once sufficient untouched history exists

39. **random control percentile**: NOT COMPUTED (untouched-history) -- see item 38

40. **finite sample empirical p value**: NOT COMPUTED (untouched-history); methodology proven to never return exactly 0.0 (worked example: 500 permutations, 0 exceedances -> p=0.001996, matches the required value exactly)

41. **development gate results**: NOT EXECUTED -- Parts 14-17 (untouched-history evaluation, matched controls, gate evaluation) require a candidate universe that does not exist; running them against 0 achievable setups would not produce a meaningful result and was not attempted

42. **hypothesis verdict**: RESEARCH_EXTENSION_REQUIRED_INSUFFICIENT_UNTOUCHED_HISTORY

43. **final eligibility status**: RESEARCH_EXTENSION_REQUIRED_INSUFFICIENT_UNTOUCHED_HISTORY (this is also the maximum-severity outcome on the allowed-verdict ladder that requires no further computation; it is a complete, valid Phase 7 completion, not a failure)

44. **causality audit result**: N/A -- no replay was executed, so no future-data or setup-ownership violation could occur; vacuously satisfied

45. **backend test result**: 3 failed, 985 passed, 13 subtests passed in 723.31s (0:12:03) (32 new Phase 7 tests, 0 regressions; the 3 failures are the same pre-existing live-Deriv-connectivity cases documented since Phase 5)

46. **frontend test build result**: Tests  184 passed (184) -- unchanged from the Phase 6 baseline (Phase 7 touched zero frontend files)

47. **phase6 registry regression**: PASS -- volatility_structure_pullback, ict_2022, jump_*, and ml registry entries verified unchanged by test_phase7_process_safety.py::test_phase6_registry_remains_unchanged_by_phase7

48. **volatility reachability regression**: PASS -- no file under analysis/volatility_structure_pullback_engine.py or strategies/derived/ was touched; existing reachability fixture tests pass unchanged

49. **forex regression**: PASS -- no Forex-related file touched this phase; not applicable to this phase's scope beyond the existing full regression pass

50. **frozen ml integrity**: PASS -- zero files under data/ml/ or analysis/ml_*.py touched; ML registry entry unchanged (REJECTED_POOR_CALIBRATION, INACTIVE, no decision/filtering/overlay/live authority)

51. **frozen experiment path**: data/stabilization/phase7/frozen/phase7-r75-vsp-hypothesis-v2-stopatr-ceiling

52. **remaining blockers**: External only: (a) live Deriv connectivity remains unavailable (same as Phase 6); (b) the ML-dataset-consumed window's embargo does not clear until 2026-07-27 -- even after Deriv connectivity is restored, meaningful untouched history will not exist until on/after that date, and even then will accumulate slowly (roughly one new day of coverage per day that passes) toward the 250-setup/6-fold preregistered minimum. No Phase 7 code or methodology blocker exists -- the preregistered plan, research variant, and corrected controls are all ready to run the moment sufficient untouched history exists.

53. **confirmation phase5 holdout remained sealed**: CONFIRMED -- status SEALED, opened_at null, result null, verified by checksum and by direct manifest read

54. **confirmation no production strategy changed**: CONFIRMED -- analysis/volatility_structure_pullback_engine.py byte-identical to its Phase 6 committed version; git status shows zero modified (only new/untracked) files for the entirety of this phase

55. **confirmation no threshold sweep occurred**: CONFIRMED -- all diagnostic buckets are fixed, predeclared quintiles (5 buckets, quantile-derived cutpoints computed once) on 3 variables, never a searched or swept threshold set

56. **confirmation exactly one hypothesis was evaluated**: CONFIRMED -- 5 candidates generated, exactly 1 selected (why_not_selected=null for exactly one of five candidate files, enforced by test), 1 research-variant module created; 0 were evaluated against untouched-history outcomes since none exist

57. **confirmation no post result tuning occurred**: CONFIRMED -- no untouched-history result was ever computed to tune against; the preregistered threshold (3.975) was fixed before this report was written and is unchanged

58. **confirmation no profitability claim was made**: CONFIRMED -- the maximum possible verdict for this hypothesis is ELIGIBLE_FOR_SECOND_INDEPENDENT_REPLICATION (enforced by validation/strategy_feasibility/phase7_verdicts.py, which raises ValueError for any of PRODUCTION_READY/LIVE_READY/AUTO_ELIGIBLE/PAPER_ELIGIBLE/CONFIRMED_PROFITABLE/GUARANTEED_EDGE); the actual verdict reached (RESEARCH_EXTENSION_REQUIRED_INSUFFICIENT_UNTOUCHED_HISTORY) makes no performance claim at all

59. **confirmation no auto paper or live eligibility changed**: CONFIRMED -- research variant hardcodes auto_eligible=False, paper_signal_allowed=False, live_execution_allowed=False, research_only=True (verified by test); Phase 6 production registry untouched

60. **confirmation no ml training or activation occurred**: CONFIRMED -- zero files under data/ml/ or analysis/ml_*.py touched or created; ml_filter_allowed=False on the research variant; ML registry entry unchanged
