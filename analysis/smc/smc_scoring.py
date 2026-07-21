def score_smc(validity,quality_components):
    failures=[key for key,value in validity.items() if not value];weights={"htf_alignment":20,"displacement_strength":15,"clean_sweep":15,"fvg_quality":10,"order_block_quality":10,"premium_discount_alignment":10,"target_clarity":10,"low_structural_conflict":10};score=sum(weights.get(key,0)*max(0,min(1,float(value or 0))) for key,value in quality_components.items());valid=not failures;grade="REJECTED" if not valid else "A" if score>=80 else "B" if score>=65 else "C"
    return {"valid":valid,"quality_score":round(score,2),"quality_grade":grade,"essential_failures":failures,"quality_components":quality_components}

