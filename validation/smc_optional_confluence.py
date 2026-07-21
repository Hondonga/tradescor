def audit_optional_confluence(decisions,outcomes=None):
    fields={"fvg_present":lambda s:bool(s.get("fvgs")),"order_block_present":lambda s:bool(s.get("order_blocks")),"premium_discount_alignment":lambda s:bool(s.get("dealing_range")),"equal_level_cluster":lambda s:any(x.get("source")=="equal_levels" for x in s.get("liquidity") or []),"strong_displacement":lambda s:any(x.get("body_atr",0)>=1 for x in s.get("displacements") or []),"htf_alignment":lambda s:(s.get("structure") or {}).get("external_structure")==((s.get("structure") or {}).get("internal_structure"))};report={}
    contracts=[(row.get("payload") or row).get("smc_contract") or {} for row in decisions]
    for name,test in fields.items():
        present=[x for x in contracts if test(x)];absent=[x for x in contracts if not test(x)];report[name]={"occurrence_count":len(present),"setup_ready_rate_when_present":sum((x.get("setup") or {}).get("state")=="TRADE_READY" for x in present)/len(present) if present else None,"setup_ready_rate_when_absent":sum((x.get("setup") or {}).get("state")=="TRADE_READY" for x in absent)/len(absent) if absent else None,"paper_outcome_statistics":None}
    return report

