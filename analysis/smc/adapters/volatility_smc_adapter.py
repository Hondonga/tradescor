from analysis.smc.adapters._shared import evaluate_shared
def evaluate_volatility_smc(*,symbol,family,candles_by_timeframe,tick_size=.01,requested_strategy="auto",**_):return evaluate_shared(symbol=symbol,family=family,frames=candles_by_timeframe,tick_size=tick_size,requested_strategy=requested_strategy,adapter_id="volatility_smc_adapter",model_name="Volatility SMC",fvg_supported=True,ob_supported=True)

