"""RR and chase-distance validation from the locked confirmed entry."""
def validate_reward_risk(*,direction,entry,stop,tp1,tp2=None,minimum_rr=1.5):
    base={"risk_points":None,"tp1_reward_points":None,"tp1_rr":None,"tp2_reward_points":None,"tp2_rr":None,"minimum_required_rr":minimum_rr,"valid":False,"rejection_reasons":[]}
    if entry is None or stop is None or not tp1:return {**base,"rejection_reasons":["Entry, stop, and TP1 are required."]}
    risk=float(entry)-float(stop) if direction=="buy" else float(stop)-float(entry);reward=float(tp1["price"])-float(entry) if direction=="buy" else float(entry)-float(tp1["price"]);reward2=(float(tp2["price"])-float(entry) if direction=="buy" else float(entry)-float(tp2["price"])) if tp2 else None;rr=round(reward/risk,8) if risk>0 else None;rr2=round(reward2/risk,8) if reward2 is not None and risk>0 else None;reasons=[]
    if risk<=0:reasons.append("Risk must be positive.")
    if reward<=0:reasons.append("TP1 is on the wrong side of entry.")
    if rr is None or rr<minimum_rr:reasons.append("TP1 RR is below the minimum requirement.")
    return {**base,"risk_points":risk,"tp1_reward_points":reward,"tp1_rr":rr,"tp2_reward_points":reward2,"tp2_rr":rr2,"valid":not reasons,"rejection_reasons":reasons}

def validate_range_position(*,direction,current_price,m15_candles,window=40,maximum_hostile_position=.75):
    """Reject entries taken at the hostile extreme of the M15 dealing range.

    Buys above ``maximum_hostile_position`` of the range or sells below
    ``1 - maximum_hostile_position`` are chasing the directional extreme.
    Backtest evidence (R_75, 90 days): those entries lose in both directions.
    """
    base={"position":None,"range_low":None,"range_high":None,"window":window,"maximum_hostile_position":maximum_hostile_position,"state":"UNKNOWN","valid":False,"rejection_reasons":[]}
    if direction not in {"buy","sell"} or current_price is None or m15_candles is None or getattr(m15_candles,"empty",True):
        return {**base,"rejection_reasons":["Direction, price, and M15 history are required."]}
    rows=m15_candles[m15_candles.complete.astype(bool)] if "complete" in getattr(m15_candles,"columns",[]) else m15_candles
    rows=rows.tail(window)
    if len(rows)<10:return {**base,"rejection_reasons":["Insufficient completed M15 history for the dealing range."]}
    range_low=float(rows.low.min());range_high=float(rows.high.max());width=range_high-range_low
    if width<=0:return {**base,"range_low":range_low,"range_high":range_high,"rejection_reasons":["M15 dealing range is degenerate."]}
    position=max(0.0,min(1.0,(float(current_price)-range_low)/width));reasons=[]
    if direction=="buy" and position>maximum_hostile_position:reasons.append("Buy entry is at the top extreme of the M15 dealing range.")
    if direction=="sell" and position<1-maximum_hostile_position:reasons.append("Sell entry is at the bottom extreme of the M15 dealing range.")
    state="AT_HOSTILE_EXTREME" if reasons else "ACCEPTABLE_LOCATION"
    return {**base,"position":position,"range_low":range_low,"range_high":range_high,"state":state,"valid":not reasons,"rejection_reasons":reasons}

def validate_chase(*,direction,current_price,entry,execution_zone,tp1,stop,atr,maximum_chase_atr=.35):
    base={"state":"ENTRY_AVAILABLE","distance_points":None,"distance_atr":None,"remaining_reward":None,"remaining_rr":None,"valid":False}
    if None in (current_price,entry,stop) or not tp1:return {**base,"state":"MISSED"}
    distance=abs(float(current_price)-float(entry));distance_atr=distance/max(float(atr or 0),1e-12);risk=(float(entry)-float(stop)) if direction=="buy" else (float(stop)-float(entry));remaining=(float(tp1["price"])-float(current_price)) if direction=="buy" else (float(current_price)-float(tp1["price"]));remaining_rr=remaining/risk if risk>0 else None
    if remaining<=0:state="MISSED";valid=False
    elif distance_atr>maximum_chase_atr:state="TOO_LATE";valid=False
    elif execution_zone and execution_zone["low"]<=current_price<=execution_zone["high"]:state="AT_ENTRY";valid=True
    elif distance_atr<=maximum_chase_atr*.5:state="NEAR_ENTRY";valid=True
    else:state="ENTRY_AVAILABLE";valid=True
    return {**base,"state":state,"distance_points":distance,"distance_atr":distance_atr,"remaining_reward":remaining,"remaining_rr":remaining_rr,"valid":valid}
