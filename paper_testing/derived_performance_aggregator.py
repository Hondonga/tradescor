from collections import defaultdict
from statistics import median
def aggregate_derived_performance(decisions,setups,outcomes,group_by=("strategy",)):
    setup_by={row["paper_setup_id"]:row for row in setups};groups=defaultdict(list)
    for row in sorted(outcomes,key=lambda item:item.get("terminal_time") or ""):
        setup=setup_by.get(row["paper_setup_id"],{});key=tuple(setup.get(field) for field in group_by);groups[key].append({**row,**{"strategy":setup.get("strategy"),"direction":setup.get("direction"),"research_mode":setup.get("research_mode")}})
    result=[]
    for key,rows in groups.items():
        filled=[row for row in rows if row.get("entry_filled")];rs=[float(row["realized_r"]) for row in filled if row.get("realized_r") is not None];positive=sum(value for value in rs if value>0);negative=abs(sum(value for value in rs if value<0));equity=peak=drawdown=0
        for value in rs:equity+=value;peak=max(peak,equity);drawdown=max(drawdown,peak-equity)
        result.append({**dict(zip(group_by,key)),"filled_trades":len(filled),"tp1_hit_rate":sum(bool(row.get("tp1_hit")) for row in filled)/len(filled) if filled else None,"tp2_hit_rate":sum(bool(row.get("tp2_hit")) for row in filled)/len(filled) if filled else None,"stop_rate":sum(bool(row.get("stop_hit")) for row in filled)/len(filled) if filled else None,"average_r":sum(rs)/len(rs) if rs else None,"median_r":median(rs) if rs else None,"profit_factor":positive/negative if negative else None,"gross_positive_r":positive,"gross_negative_r":negative,"maximum_drawdown_r":drawdown,"ambiguous_outcome_count":sum(bool(row.get("intracandle_ambiguous")) for row in filled)})
    return result
def chronological_drawdown(outcomes):
    rows=sorted((row for row in outcomes if row.get("realized_r") is not None),key=lambda row:row.get("terminal_time") or "");equity=peak=max_dd=0;started=recovered=None
    for row in rows:
        equity+=float(row["realized_r"])
        if equity>=peak:peak=equity;recovered=row.get("terminal_time") if started else None
        elif peak-equity>max_dd:max_dd=peak-equity;started=row.get("terminal_time")
    return {"starting_r":0.0,"ending_r":equity,"peak_r":peak,"maximum_drawdown_r":max_dd,"maximum_drawdown_percent":None,"drawdown_started_at":started,"drawdown_recovered_at":recovered}
