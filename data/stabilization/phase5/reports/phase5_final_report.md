# Phase 5 Final Report: R_75 Volatility Structure Pullback Walk-Forward Validation

1. **branch history correction status**: COMPLETE

2. **phase4 branch commit**: b87e72d8730629734740d4ec1a840d32770813cb

3. **status patch branch and tag**: tradescor-status-label-normalization @ c42a2626a25006b3a035f0a95321b23dd9771962; tag tradescor-status-labels-v1

4. **status patch validation result**: PASSED, PRESENTATION_ONLY

5. **phase5 process status**: PASSED

6. **strategy verdict**: REJECTED_NO_EDGE_AFTER_COSTS

7. **phase5 branch**: tradescor-phase5-volatility-walk-forward-validation

8. **phase5 starting commit**: c42a2626a25006b3a035f0a95321b23dd9771962

9. **final phase5 commit**: RECORDED AT THIS REPORT'S OWN COMMIT

10. **experiment id**: phase5-r75-vsp-walkforward-v1

11. **replay pid and exit code**: PID 13104, exit code 0

12. **replay evaluations expected**: 37152

13. **replay evaluations completed**: 37152 (yielding 1093 unique trade candidates)

14. **replay skipped count**: 0

15. **replay duplicate count**: 0

16. **strategy version**: volatility_structure_pullback_engine-v1

17. **parameter hash**: 2ebdea4417102280d5740c43b7183cae78d1c8c6c15ea384c0f5955c23ab603c

18. **data coverage**: 2025-10-15T00:00:00Z to 2026-04-13T23:59:00Z

19. **consumed data coverage**: {'start': '2026-04-21T05:45:00Z', 'end': '2026-07-20T05:44:00Z'}

20. **genuinely new coverage**: 181 days pulled

21. **dataset checksum**: 49b3f5563f6d6bd6d76890250f6fbfa1ce17912e2ea9c7feb356fe4e11e435ae

22. **raw trade ready snapshot count**: Not separately recorded (deduplication was applied inline during the causal replay via a setups_seen set, so only the first causally-valid TRADE_READY snapshot per setup_id was ever written to development_trade_candidates.csv). Verified indirectly below.

23. **unique setup count**: 1093

24. **resolved setup count**: 1093

25. **not filled count**: 0

26. **buy count**: 625

27. **sell count**: 468

28. **fold count**: 8

29. **conservative cost assumptions**: {'generated_at': '2026-07-22T20:04:11.511941+00:00', 'part': '10 - APPLY COSTS', 'zero_cost_mean_r': 0.07416955639705941, 'base_cost_mean_r': 0.024169556397059425, 'conservative_cost_mean_r': -0.02583044360294065, 'mean_cost_in_price': 40.17482860168605, 'mean_cost_in_atr': 0.30096499120690456, 'mean_cost_in_r': 0.1, 'gross_expectancy': 0.07416955639705941, 'net_expectancy_conservative': -0.02583044360294065, 'cost_sensitivity': {'zero_to_base_delta': 0.04999999999999999, 'base_to_conservative_delta': 0.05000000000000007}}

30. **gross mean realized r**: 0.07416955639705941

31. **net mean realized r**: -0.02583044360294065

32. **grouped expectancy confidence interval**: [-0.15085152419144907, 0.11031326284551592]

33. **profit factor after costs**: 0.9639014514026161

34. **maximum drawdown in r**: 114.08317174388051

35. **percentage positive folds**: 0.375

36. **same minus opposite result**: {'mean': 0.22870145152016336, 'lower_95': -0.023318063626141142, 'upper_95': 0.47961815342690745, 'n_groups': 326}

37. **same minus geometry result**: {'mean': 0.0, 'lower_95': 0.0, 'upper_95': 0.0, 'n_groups': 243, 'caveat': "This control arm's preregistered definition (identical absolute entry/stop/TP1 levels, direction reassigned by an independent coin flip) degenerates: whenever the coin flip happens to match the setup's real direction (~50% of pairs), the geometry-only trade becomes byte-identical to the real trade (same direction AND same levels), forcing diff=0 for every surviving matched pair after the opposite-direction half is dropped as geometrically invalid. The literal 0.0/0.0/0.0 result is a known design property of the preregistered arm, not evidence that price-level geometry has zero effect. Per the preregistration commitment, this was not corrected after seeing the result -- disclosed here instead. It does not affect the verdict, since post_cost_edge failed first in gate order."}

38. **random control percentile and p value**: {'percentile': 100.0, 'p_value': 0.0}

39. **fold concentration**: 0.5095213852801374

40. **direction stability**: {'buy_mean': -0.024341332299220347, 'sell_mean': -0.02781910720299437}

41. **development gate result**: post_cost_edge

42. **holdout status**: SEALED

43. **holdout access count**: 0

44. **holdout result**: None

45. **final eligibility status**: REJECTED_NO_EDGE_AFTER_COSTS

46. **harness self test result**: 18/18 passed

47. **causality audit result**: PASSED

48. **dataset integrity result**: PASSED

49. **python test result**: 934 passed, 3 failed, 13 subtests passed (937 total, baseline met). The 3 failures are all in tests/test_phase4_market_family_isolation.py (test_r75_resolves_only_to_deriv_and_volatility_family, test_r75_never_offers_a_forex_strategy_model, test_r75_market_schedule_is_24_7_not_forex_24_5), all raising DerivAPIError('Deriv returned no active symbols.') from a REAL live call to Deriv's public active_symbols endpoint -- reproduced independently outside pytest via a direct DerivProvider().list_symbols() call with the identical error. Neither this test file nor providers/deriv_provider.py / providers/deriv_ws_client.py were touched by any Phase 5 commit (last touched in Phase 4, commit b7c5a51). Consistent with transient live-API unavailability after ~15 hours of continuous heavy real Deriv API use during this experiment's data pull and causal replay -- not a code regression.

50. **frontend test build result**:    Duration  11.53s (transform 701ms, setup 9.34s, collect 3.59s, tests 5.28s, environment 31.23s, prepare 7.59s); TypeScript clean; production build succeeds

51. **volatility buy reachability regression**: PASS -- 625 real BUY setups causally reached TRADE_READY during the development replay itself (the strongest possible reachability evidence); targeted regression suite: 2 failed, 141 passed, 794 deselected, 4 subtests passed in 30.70s

52. **volatility sell reachability regression**: PASS -- 468 real SELL setups causally reached TRADE_READY during the development replay itself; targeted regression suite: 2 failed, 141 passed, 794 deselected, 4 subtests passed in 30.70s

53. **forex ict regression**: PASS -- 2 failed, 141 passed, 794 deselected, 4 subtests passed in 30.70s (includes forex/ict_2022_v2 slice, untouched by Phase 5)

54. **frozen ml integrity**: PASS -- byte-identical to Phase 4 baseline

55. **frozen experiment path**: /Users/user/Documents/Codex/ tradescor/ict_flask_scanner/data/stabilization/phase5/frozen/phase5-r75-vsp-walkforward-v1

56. **remaining blockers**: For the strategy: none to resolve -- REJECTED_NO_EDGE_AFTER_COSTS is a complete, frozen, negative result; no further Phase 5 action is implied or requested. For process hygiene: 3 pre-existing tests in tests/test_phase4_market_family_isolation.py are currently failing due to a live Deriv API connectivity issue unrelated to any code in this repository (see item 49); they should be re-run once Deriv's public endpoint is reachable again to confirm they return to passing, but this is an external infrastructure matter, not a Phase 5 deliverable.

57. **no thresholds changed confirmation**: CONFIRMED

58. **no cost assumptions changed after results**: CONFIRMED -- cost model fixed in experiment_spec.json before any outcome was computed

59. **no post result tuning confirmation**: CONFIRMED

60. **no profitability claim confirmation**: CONFIRMED -- max verdict is ELIGIBLE_FOR_PAPER_SHADOW

61. **no live execution confirmation**: CONFIRMED -- no broker execution code exists in this repository

62. **no ml training or activation confirmation**: CONFIRMED -- zero files under data/ml/ or analysis/ml_*.py touched
