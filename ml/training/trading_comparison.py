from __future__ import annotations
import math
import numpy as np

def trading_metrics(frame,accepted=None):
    rows=frame if accepted is None else frame.loc[np.asarray(accepted)];r=rows.realized_r.fillna(0).to_numpy(float);wins=int((r>0).sum());losses=int((r<=0).sum());curve=np.cumsum(r);peaks=np.maximum.accumulate(np.r_[0,curve]);draw=peaks[1:]-curve if len(curve) else np.array([]);gains=r[r>0].sum();loss=-r[r<0].sum()
    return {"trades":len(rows),"wins":wins,"losses":losses,"average_realized_r":float(r.mean()) if len(r) else 0.0,"total_realized_r":float(r.sum()),"expectancy":float(r.mean()) if len(r) else 0.0,"profit_factor":float(gains/loss) if loss else None,"maximum_drawdown_r":float(draw.max()) if len(draw) else 0.0,"buy":_side(rows,"buy"),"sell":_side(rows,"sell")}
def _side(frame,side):
    rows=frame[frame.direction.eq(side)];r=rows.realized_r.fillna(0);return {"trades":len(rows),"wins":int((r>0).sum()),"total_realized_r":float(r.sum()),"expectancy":float(r.mean()) if len(r) else 0.0}
