from dataclasses import dataclass
import pandas as pd

@dataclass
class DerivedReplayClock:
    candle_times:list
    interval_seconds:int
    current_index:int=-1
    def __post_init__(self):self.candle_times=[int(pd.Timestamp(value).timestamp()) if not isinstance(value,(int,float)) else int(value) for value in self.candle_times]
    def __iter__(self):
        while self.current_index+1<len(self.candle_times):yield self.advance()
    def advance(self):
        if self.current_index+1>=len(self.candle_times):raise StopIteration
        self.current_index+=1;close=self.candle_times[self.current_index]+self.interval_seconds
        return {"current_time":pd.Timestamp(close,unit="s",tz="UTC").isoformat(),"current_index":self.current_index,"total_candles":len(self.candle_times),"progress_percent":round(100*(self.current_index+1)/max(1,len(self.candle_times)),4),"completed_timeframes":completed_timeframes(close)}

def completed_timeframes(epoch):
    sizes={"M5":300,"M15":900,"M30":1800,"H1":3600,"H2":7200,"H4":14400,"D1":86400}
    return [name for name,size in sizes.items() if epoch%size==0]
