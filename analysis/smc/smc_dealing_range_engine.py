import hashlib,json

def build_dealing_range(swings,accepted_breakout=None):
    highs=[x for x in swings if x["type"]=="high" and x.get("scope")=="external"];lows=[x for x in swings if x["type"]=="low" and x.get("scope")=="external"]
    if not highs or not lows:return None
    high=highs[-1];low=lows[-1]
    if high["confirmation_time"]<low["confirmation_time"]:pass
    top=float(high["price"]);bottom=float(low["price"])
    if bottom>=top:return None
    events=sorted([("high",x.get("confirmation_time")) for x in highs[-3:]]+[("low",x.get("confirmation_time")) for x in lows[-3:]],key=lambda x:str(x[1]));alternations=sum(a[0]!=b[0] for a,b in zip(events,events[1:]));identity=hashlib.sha256(json.dumps([low["swing_id"],high["swing_id"]]).encode()).hexdigest()[:20];invalid=bool(accepted_breakout and accepted_breakout.get("type")=="accepted_breakout");valid=alternations>=2 and not invalid
    return {"range_id":"dealing-"+identity,"low":bottom,"high":top,"equilibrium":(bottom+top)/2,"premium_boundary":bottom+(top-bottom)*.5,"discount_boundary":bottom+(top-bottom)*.5,"valid":valid,"active":valid,"alternating_interactions":alternations,"accepted_breakout":invalid,"archived":invalid,"invalidation_reason":"Accepted structural breakout." if invalid else "Insufficient alternating boundary interaction." if not valid else None}
