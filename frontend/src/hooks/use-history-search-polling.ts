import { useEffect } from "react";
import { latestSetupSearch } from "@/lib/api";
import { useTerminalStore } from "@/store/terminal-store";

export function useHistorySearchPolling() {
  const progress=useTerminalStore((state)=>state.historicalSearch);
  const setProgress=useTerminalStore((state)=>state.setHistoricalSearch);
  const showHistorical=useTerminalStore((state)=>state.showHistorical);
  useEffect(()=>{
    if(!progress || !["queued","running"].includes(progress.state)) return;
    const timer=setInterval(async()=>{
      const payload=await latestSetupSearch(progress.job_id);
      setProgress(payload.progress);
      if(payload.result?.decision) showHistorical(payload.progress.job_id,payload.result.decision,payload.result.candles);
    },750);
    return()=>clearInterval(timer);
  },[progress?.job_id,progress?.state,setProgress,showHistorical]);
}
