def initial_risk(direction,entry,stop):return float(entry)-float(stop) if direction=="buy" else float(stop)-float(entry) if direction=="sell" else None
def planned_r(direction,entry,stop,target):
    risk=initial_risk(direction,entry,stop);reward=float(target)-float(entry) if direction=="buy" else float(entry)-float(target);return reward/risk if risk and risk>0 else None
def realized_r(direction,entry,stop,exit_price,slippage_points=0):
    risk=initial_risk(direction,entry,stop);reward=float(exit_price)-float(entry) if direction=="buy" else float(entry)-float(exit_price);return reward/risk-(float(slippage_points)/risk if risk else 0) if risk and risk>0 else None
