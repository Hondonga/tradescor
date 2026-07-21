from collections import defaultdict
def build_derived_performance_report(records):
    groups=defaultdict(list)
    for row in records:groups[(row.get("family"),row.get("strategy"),row.get("direction"))].append(row)
    result=[]
    for key,rows in groups.items():
        count=len(rows);label="INSUFFICIENT EVIDENCE" if count<20 else "EARLY EVIDENCE" if count<50 else "MODERATE EVIDENCE" if count<100 else "STRONGER EVIDENCE";values=[float(row.get("realized_r",0)) for row in rows]
        result.append({"family":key[0],"strategy":key[1],"direction":key[2],"sample_size":count,"evidence_label":label,"average_r":sum(values)/count if count else None})
    return result
