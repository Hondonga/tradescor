from __future__ import annotations

REQUIRED=("family_adapter","structure_definitions","setup_lifecycle","entry_construction","stop_construction","target_hierarchy","feature_semantics","tick_normalized","volatility_normalized")
def audit_symbol_compatibility(candidate,reference):
    checks=[]
    for key in REQUIRED:
        left=reference.get(key);right=candidate.get(key);checks.append({"name":key,"reference":left,"candidate":right,"passed":left is not None and left==right if key not in {"tick_normalized","volatility_normalized"} else bool(left and right)})
    failed=[row for row in checks if not row["passed"]]
    return {"compatible":not failed,"checks":checks,"blocking_requirements":failed,"policy":"Separate models are required when production semantics differ."}
