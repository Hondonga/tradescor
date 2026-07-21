import pandas as pd
from analysis.smc.smc_swing_engine import confirmed_swings
from analysis.smc.smc_displacement_engine import measure_displacement
from analysis.smc.smc_liquidity_engine import structural_liquidity,classify_reference_event
from analysis.smc.smc_structure_engine import analyze_structure
from analysis.smc.smc_fvg_engine import detect_fvgs
from analysis.smc.smc_order_block_engine import detect_order_blocks
from analysis.smc.smc_dealing_range_engine import build_dealing_range
from analysis.smc.smc_setup_engine import build_smc_setup
from analysis.smc.smc_normalizer import normalize_smc_result
from analysis.smc.smc_target_engine import evaluate_structural_targets

def evaluate_shared(*,symbol,family,frames,tick_size,requested_strategy,adapter_id,model_name,fvg_supported=True,ob_supported=True,structural_array_supported=False,excluded_times=None,event=None,research_only=False):
    h4=_rows(frames.get("H4"));h1=_rows(frames.get("H1"));m15=_rows(frames.get("M15"));m5=_rows(frames.get("M5"));atr=float((m15.high-m15.low).tail(14).mean()) if len(m15) else tick_size;external_h4=confirmed_swings(h4,atr=atr,tick_size=tick_size,left_strength=2,right_strength=2,scope="external_h4");external=confirmed_swings(h1,atr=atr,tick_size=tick_size,left_strength=3,right_strength=3,scope="external");internal=confirmed_swings(m15,atr=atr,tick_size=tick_size,left_strength=2,right_strength=2,scope="internal");execution=confirmed_swings(m5,atr=atr,tick_size=tick_size,left_strength=2,right_strength=2,scope="execution");swings=external_h4+external+internal+execution;liquidity=structural_liquidity(swings,atr=atr,tick_size=tick_size);last_close=float(m15.iloc[-1].close) if len(m15) else None
    provisional=measure_displacement(m15,atr=atr,tick_size=tick_size);candidate_ref=_nearest_reference(liquidity,last_close,provisional.get("direction"));event_ref=classify_reference_event(m15,candidate_ref,acceptance_buffer=atr*.05) if candidate_ref else {"type":"none","qualified":False};provisional["structure_broken"]=event_ref.get("type")=="accepted_breakout";structure=analyze_structure(m15,swings,provisional,event_ref,buffer=atr*.03)
    m5_disp=measure_displacement(m5,atr=float((m5.high-m5.low).tail(14).mean()) if len(m5) else atr,tick_size=tick_size);m5_disp["structure_broken"]=bool(structure.get("last_bos") or event_ref.get("qualified"));m5_structure=analyze_structure(m5,execution,m5_disp,event_ref,buffer=atr*.01)
    direction=(m5_structure.get("last_mss") or m5_structure.get("last_bos") or structure.get("last_bos") or {}).get("direction") or ("bullish" if structure.get("external_structure")=="bullish" else "bearish" if structure.get("external_structure")=="bearish" else "")
    displacements=[x for x in (provisional,m5_disp) if x.get("passed")];fvgs=detect_fvgs(m15,atr=atr,tick_size=tick_size,displacements=displacements,excluded_times=excluded_times,supported=fvg_supported,research_only=research_only);events=[structure.get("last_bos"),structure.get("last_mss"),m5_structure.get("last_bos"),m5_structure.get("last_mss")];order_blocks=detect_order_blocks(m15,displacements,events) if ob_supported else [];entry_array=_entry_array(direction,fvgs,order_blocks)
    if not entry_array and structural_array_supported:entry_array=_structural_array(direction,internal,tick_size)
    accepted=event_ref if event_ref.get("type")=="accepted_breakout" else None;dealing=build_dealing_range(external,accepted);combined={**structure,"last_mss":m5_structure.get("last_mss") or structure.get("last_mss"),"last_bos":m5_structure.get("last_bos") or structure.get("last_bos"),"internal_structure":m5_structure.get("internal_structure") or structure.get("internal_structure")}
    projected_entry,projected_stop=_projected_geometry(direction,entry_array,event_ref,tick_size);setup_type="range_reaction" if structure.get("external_structure")=="range" else "liquidity_reversal" if event_ref.get("type")=="sweep" else "structure_pullback"
    target_result=evaluate_structural_targets(symbol=symbol,direction=direction,entry=projected_entry,stop=projected_stop,swings=swings,liquidity=liquidity,dealing_range=dealing,candles_by_timeframe=frames,setup_type=setup_type,event={**(event or {}),"blocking":bool(research_only)},tick_size=tick_size);target=target_result.get("tp1") or {}
    setup=build_smc_setup(symbol=symbol,strategy_id="smc_auto" if str(requested_strategy).lower()=="auto" else "smc",family_adapter=adapter_id,direction=direction,htf_structure=structure.get("external_structure"),structural_target=target,secondary_target=target_result.get("tp2"),sweep=event_ref,displacement=m5_disp if m5_disp.get("passed") else provisional,structure=combined,entry_array=entry_array,current_price=float(m5.iloc[-1].close) if len(m5) else last_close,tick_size=tick_size,event_risk="EVENT_RISK_ACTIVE" if (event or {}).get("risk_state") in {"ACTIVE","BLOCKING","EVENT_RISK_ACTIVE"} else None,research_only=research_only)
    setup.update({"target_trace":target_result["target_trace"],"target_source_audit":target_result["target_source_audit"],"history_depth_audit":target_result["history_depth_audit"],"target_scope":target_result["target_scope"],"target_timeframe":target_result["target_timeframe"],"target_source":target_result["target_source"],"tp2_structural_target":target_result.get("tp2"),"setup_type":setup_type})
    if not target:
        setup["state"]="WAITING_FOR_TARGET";setup["next_required_condition"]=_target_blocker_message(target_result["target_trace"])
    return normalize_smc_result(requested_strategy=requested_strategy,adapter_id=adapter_id,family=family,model_name=model_name,setup=setup,structure=combined,liquidity=liquidity,swings=swings,displacements=displacements,fvgs=fvgs,order_blocks=order_blocks,dealing_range=dealing,event=event,candidates=[{"setup_type":"structure_pullback","eligible":bool(direction)},{"setup_type":"liquidity_reversal","eligible":event_ref.get("type")=="sweep"},{"setup_type":"range_reaction","eligible":structure.get("external_structure")=="range"}],selection_reason=f"Registry-first family {family.get('family')} routes exclusively to {model_name}.")
def _rows(rows):
    rows=rows.copy() if rows is not None else pd.DataFrame();return rows[rows.complete.astype(bool)].reset_index(drop=True) if "complete" in rows else rows.reset_index(drop=True)
def _nearest_reference(refs,price,direction=None):
    if price is None or not refs:return None
    preferred="buy_side" if direction=="bullish" else "sell_side" if direction=="bearish" else None;eligible=[x for x in refs if not preferred or x["type"]==preferred] or refs;return min(eligible,key=lambda x:abs(float(x["price"])-price))
def _target(refs,price,direction):
    if price is None:return {}
    candidates=[x for x in refs if (direction=="bullish" and x["type"]=="buy_side" and x["price"]>price) or (direction=="bearish" and x["type"]=="sell_side" and x["price"]<price)]
    return min(candidates,key=lambda x:abs(x["price"]-price)) if candidates else {}
def _projected_geometry(direction,array,event,tick_size):
    if not array:return None,None
    entry=(float(array["low"])+float(array["high"]))/2;buffer=max(float(tick_size)*2,abs(float(array["high"])-float(array["low"]))*0.1)
    stop=min(float(array["low"]),float(event.get("extreme",array["low"])))-buffer if direction=="bullish" else max(float(array["high"]),float(event.get("extreme",array["high"])))+buffer if direction=="bearish" else None
    return entry,stop
def _target_blocker_message(trace):
    blocker=trace.get("first_blocker")
    if blocker=="TARGET_EXISTS_RR_REJECTED":
        rejected=next((row for row in trace.get("candidates_rejected",[]) if row.get("rejection_code")=="RR_BELOW_MINIMUM"),None)
        return (rejected or {}).get("rejection_explanation") or "Structural target exists but reward-to-risk is below the minimum."
    return {"TARGET_EXISTS_WRONG_SIDE":"Structural targets exist, but none is on the profitable side.","TARGET_EXISTS_ALREADY_CONSUMED":"Structural targets exist, but completed-candle evidence shows they were consumed.","TARGET_EXISTS_EVENT_INVALIDATED":"Structural target ownership is blocked by active event risk."}.get(blocker,"No valid structural target is available.")
def _entry_array(direction,fvgs,blocks):
    arrays=[{**x,"type":"fvg"} for x in fvgs if x["direction"]==direction and not x["invalidated"]]+[{**x,"type":"order_block"} for x in blocks if x["direction"]==direction and not x["invalidated"]]
    return arrays[-1] if arrays else {}
def _structural_array(direction,swings,tick_size):
    kind="low" if direction=="bullish" else "high" if direction=="bearish" else None;matches=[row for row in swings if row["type"]==kind]
    if not matches:return {}
    swing=matches[-1];width=max(float(tick_size)*3,float(swing.get("prominence_ticks",1))*float(tick_size)*.1);price=float(swing["price"]);return {"structural_array_id":"structural-"+swing["swing_id"],"type":"structural_retrace","direction":direction,"low":price-width,"high":price+width,"invalidated":False,"origin_time":swing["candle_time"]}
