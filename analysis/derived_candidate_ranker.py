"""Rank eligible candidates without allowing evidence to revive rejected ones."""
def rank_derived_candidates(candidates,historical_evidence=None):
    evidence=historical_evidence or {};rows=[]
    for row in candidates:
        if not row or not row.get("eligible"):continue
        sample=evidence.get(row.get("strategy"),{});multiplier=float(sample.get("multiplier",1)) if int(sample.get("sample_size",0))>=20 else 1
        rows.append({**row,"rank_score":round(float(row.get("quality",0))*multiplier,2)})
    rows.sort(key=lambda row:row["rank_score"],reverse=True);return rows
