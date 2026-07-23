# Phase 8 Final Report: Untouched-History Replication of the Stop-Distance Hypothesis

1. **phase8 process status**: COMPLETE

2. **working branch**: tradescor-phase8-stop-distance-replication

3. **starting phase7 commit**: d08810219fc1a2e9f6ac1c5bedcd3d9ca5af218c

4. **final phase8 commit**: 6576626e567572d7e4cd211c2b8dd5ac3e5cc8f0

5. **parent strategy**: volatility_structure_pullback

6. **variant strategy**: volatility_structure_pullback_hypothesis_v2

7. **exact single change**: reject a setup when stop_distance_atr > 3.975 (ATR = mean(high-low) over the trailing 14 completed M5 candles up to and including the decision candle)

8. **threshold verification**: CONFIRMED exactly 3.975 -- MAX_STOP_DISTANCE_ATR in strategies/research/volatility_structure_pullback_hypothesis_v2.py, unchanged from Phase 7 (data/stabilization/phase8/manifests/single_change_diff_report.json)

9. **parent engine integrity result**: PASS -- analysis/volatility_structure_pullback_engine.py byte-identical to its Phase 6 committed version (verified by test and by Part 0 checkpoint)

10. **phase5 frozen integrity result**: PASS -- all checksums in data/stabilization/phase5/frozen/phase5-r75-vsp-walkforward-v1/experiment_record.json verified byte-identical; verdict still REJECTED_NO_EDGE_AFTER_COSTS

11. **phase5 holdout status**: SEALED, opened_at=null, result=null -- unchanged, never opened

12. **phase7 frozen integrity result**: PASS -- all checksums in data/stabilization/phase7/frozen/phase7-r75-vsp-hypothesis-v2-stopatr-ceiling/experiment_record.json verified byte-identical; verdict still RESEARCH_EXTENSION_REQUIRED_INSUFFICIENT_UNTOUCHED_HISTORY

13. **untouched history coverage**: 5.77 hours (2026-04-20T23:59:00Z to 2026-04-21T05:45:00Z) -- unchanged from Phase 7; independently re-verified at this phase's own timestamp (2026-07-23), not merely copied forward

14. **excluded consumed windows**: 
  - 2025-10-15 to 2026-04-14 :: PHASE_5_DEVELOPMENT_AND_SEALED_HOLDOUT
  - 2026-04-14 to 2026-04-21 05:45 :: PHASE_5_EMBARGO (7-day)
  - 2026-04-21 05:45 to 2026-07-20 05:44 :: ML_DATASET_TRAIN_VALIDATION_TEST
  - 2026-07-20 05:44 to 2026-07-27 05:44 :: ML_DATASET_EMBARGO (7-day, not yet elapsed -- ~4.1 days remaining)

15. **untouched data checksum**: null -- no candle data was fetched or persisted; nothing to checksum (provider unavailable regardless)

16. **experiment id**: phase8-r75-vsp-hypothesis-v2-untouched-replication-v1

17. **parent setup count**: NOT COMPUTED -- 0 achievable from the 5.77-hour window (engine requires >=20 completed H1 candles, i.e. >=20 hours, before a single decision point can be scored)

18. **variant retained count**: NOT COMPUTED -- same reason as item 17

19. **variant rejected count**: NOT COMPUTED -- same reason as item 17

20. **retention percentage**: NOT COMPUTED -- same reason as item 17

21. **buy count**: NOT COMPUTED -- same reason as item 17

22. **sell count**: NOT COMPUTED -- same reason as item 17

23. **fold count**: NOT COMPUTED -- same reason as item 17

24. **conservative cost parent expectancy**: NOT COMPUTED -- same reason as item 17

25. **conservative cost variant expectancy**: NOT COMPUTED -- same reason as item 17

26. **variant minus parent result**: NOT COMPUTED -- same reason as item 17

27. **variant grouped confidence interval**: NOT COMPUTED -- same reason as item 17

28. **profit factor**: NOT COMPUTED -- same reason as item 17

29. **maximum drawdown**: NOT COMPUTED -- same reason as item 17

30. **positive fold percentage**: NOT COMPUTED -- same reason as item 17

31. **same minus opposite result**: NOT COMPUTED -- same reason as item 17

32. **geometry control v2 result**: NOT COMPUTED -- methodology exists and is unit-tested (validation/strategy_feasibility/control_methodology_v2.py, 10/10 passing) but was never applied to any Phase 8 outcome, since none exists

33. **random control percentile**: NOT COMPUTED -- same reason as item 32

34. **finite sample p value**: NOT COMPUTED against any Phase 8 outcome; methodology proven to never return exactly 0.0 (500 permutations/0 exceedances -> p=0.001996, re-verified by test_phase8_replication.py::test_empirical_p_value_is_never_zero)

35. **causality result**: PASS (vacuous) -- no replay executed, so zero future-data or setup-ownership violations were possible

36. **sample gate result**: FAILED -- 0 achievable parent setups versus the preregistered minimum of 250

37. **retention gate result**: N/A -- no parent-eligible population exists to compute retention against

38. **development gate results**: 
  - 1. CAUSALITY: PASS (vacuous)
  - 2. UNTOUCHED_HISTORY_VALIDITY: FAILED
  - 3. SAMPLE_SUFFICIENCY: FAILED (consequence of gate 2)
  - 4. RETENTION_SUFFICIENCY: N/A
  - 5. VARIANT_POST_COST_EDGE: N/A
  - 6. IMPROVEMENT_OVER_PARENT: N/A
  - 7. DIRECTIONAL_INFORMATION: N/A
  - 8. GEOMETRY_CONTROL_SUPERIORITY: N/A
  - 9. RANDOM_CONTROL_SUPERIORITY: N/A
  - 10. FOLD_STABILITY: N/A
  - 11. DIRECTION_STABILITY: N/A
  - 12. DRAWDOWN: N/A

39. **hypothesis verdict**: RESEARCH_EXTENSION_REQUIRED_INSUFFICIENT_UNTOUCHED_HISTORY

40. **final eligibility status**: RESEARCH_EXTENSION_REQUIRED_INSUFFICIENT_UNTOUCHED_HISTORY -- a complete, valid Phase 8 completion; not a failure of process

41. **backend test result**: 3 failed, 1006 passed, 13 subtests passed in 724.06s (0:12:04) (21 new Phase 8 tests, 0 regressions; the 3 failures are the same pre-existing live-Deriv-connectivity cases documented since Phase 5)

42. **frontend test build result**: Tests  184 passed (184) -- unchanged from the Phase 7 baseline (Phase 8 touched zero frontend files)

43. **phase6 registry regression**: PASS -- volatility_structure_pullback, ict_2022, jump_*, and ml registry entries verified unchanged by test_phase8_replication.py::test_production_registry_remains_unchanged

44. **volatility reachability regression**: PASS -- no file under analysis/volatility_structure_pullback_engine.py or strategies/derived/ touched; existing reachability fixture tests pass unchanged

45. **forex regression**: PASS -- no Forex-related file touched this phase

46. **frozen ml integrity**: PASS -- zero files under data/ml/ or analysis/ml_*.py touched; ML registry entry unchanged (REJECTED_POOR_CALIBRATION, INACTIVE, no decision/filtering/overlay/live authority)

47. **frozen experiment path**: data/stabilization/phase8/frozen/phase8-r75-vsp-hypothesis-v2-untouched-replication-v1

48. **remaining blockers**: External only, identical to Phase 7: live Deriv connectivity unavailable; ML-dataset embargo does not clear until 2026-07-27; even then, meaningful untouched history accumulates at roughly one new day per day that passes, toward the 250-setup/6-fold preregistered minimum. No Phase 8 code, methodology, or design blocker exists -- the full preregistered plan, single-change variant, and corrected controls are ready to run the moment sufficient untouched history exists.

49. **confirmation phase5 holdout remained sealed**: CONFIRMED -- verified by checksum and direct manifest read at both Part 0 and Part 14

50. **confirmation parent strategy remained unchanged**: CONFIRMED -- byte-identical to its Phase 6 committed version, verified by test

51. **confirmation threshold stayed exactly 3975**: CONFIRMED

52. **confirmation no additional filter was added**: CONFIRMED -- source-diff report (Part 1) found exactly one behavioral difference; MAX_STOP_DISTANCE_ATR appears exactly once in the variant module

53. **confirmation no second hypothesis was tested**: CONFIRMED -- exactly one research-variant module exists; exactly one of the five Phase 7 candidates has why_not_selected=null

54. **confirmation no post result tuning occurred**: CONFIRMED -- no Phase 8 outcome was ever computed to tune against

55. **confirmation no profitability claim was made**: CONFIRMED -- the actual verdict (RESEARCH_EXTENSION_REQUIRED_INSUFFICIENT_UNTOUCHED_HISTORY) makes no performance claim; forbidden verdicts remain code-enforced impossible (validation/strategy_feasibility/phase7_verdicts.py)

56. **confirmation no auto paper or live eligibility changed**: CONFIRMED -- research variant hardcodes auto_eligible=False, paper_signal_allowed=False, live_execution_allowed=False; Phase 6 production registry untouched

57. **confirmation no ml training or activation occurred**: CONFIRMED -- zero files under data/ml/ or analysis/ml_*.py touched or created this phase
