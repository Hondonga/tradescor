def weight_current_and_historical(current_score,evidence,research_only=False):
    historical=float(evidence.get("score",0)) if evidence.get("eligible_for_ranking") else 0;weight=.15 if evidence.get("eligible_for_ranking") else 0;score=float(current_score)*(1-weight)+historical*weight;return min(score,.65) if research_only else score
