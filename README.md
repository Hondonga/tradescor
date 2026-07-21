# ICT 2022 Flask Scanner

Beginner-friendly Flask charting app for loading one selected Twelve Data chart,
displaying it with Lightweight Charts, and running a current ICT-style setup
analysis.

This first milestone only does:

1. Run a Flask web app.
2. Load candle data from Twelve Data.
3. Display candles with Lightweight Charts.
4. Detect the current relevant FVG, sweep, MSS, IFVG, risk, and score context.
5. Show one current setup analysis instead of drawing every historical FVG.
6. Rank meaningful liquidity objectives and reject trades below the 1.5R minimum.

It does not place trades or run multi-symbol scans.

## Project Structure

```text
ict_flask_scanner/
├── app.py
├── data_feed.py
├── fvg_detector.py
├── providers/
│   └── symbol_map.py
├── scanner/
│   └── ...
├── requirements.txt
├── README.md
├── .env.example
├── static/
│   ├── app.js
│   └── style.css
└── templates/
    └── index.html
```

## FVG Rules

Bullish FVG:

```text
Candle 1 high < Candle 3 low
```

Bearish FVG:

```text
Candle 1 low > Candle 3 high
```

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create your environment file:

```bash
cp .env.example .env
```

Open `.env` and paste your Twelve Data API key:

```text
TWELVE_DATA_API_KEY=your_real_api_key_here
```

## Run

Start the Flask app:

```bash
python3 app.py
```

Open this URL in your browser:

```text
http://127.0.0.1:5000
```

Choose a symbol and timeframe, then click **Load Chart**. The app does not
preload candles and does not call Twelve Data until you click the button.

Auto-refresh is off by default. If enabled, it refreshes only the currently
loaded chart and uses a 60-second minimum interval.

Data Mode defaults to **Single Timeframe**, which uses one Twelve Data request.
Balanced and Full Context are opt-in because they load additional timeframes
and consume more API credits.

## Replay Mode

After one chart is loaded, use the Replay Lab controls to play, pause, step
forward, step back, or reset through the already-loaded candles. Replay posts
the visible candle slice to `/api/analyze-replay`, so it does not spend
additional Twelve Data credits.

Replay analysis is timestamp-bound: selected candles, higher-timeframe context,
ICT sessions, and local news restrictions are evaluated at the replay candle's
historical timestamp. Higher-timeframe candles are included only after their
close time.

## Example Symbols

```text
EUR/USD
GBP/USD
USD/JPY
AUD/USD
USD/CAD
GBP/JPY
BTC/USD
ETH/USD
NASDAQ 100
Dow Jones 30
S&P 500
Russell 2000
```

Index symbols are mapped in `providers/symbol_map.py`. If Twelve Data rejects an
index, your plan may not include it or the mapping may need to be adjusted.

## API

Candles:

```text
http://127.0.0.1:5000/api/candles?symbol=EUR/USD&timeframe=M5&bars=300
```

Fair Value Gaps:

```text
http://127.0.0.1:5000/api/fvg?symbol=EUR/USD&timeframe=M5&bars=300
```

Current ICT analysis:

```text
http://127.0.0.1:5000/api/analyze?symbol=EUR/USD&timeframe=M5&bars=300
```

Replay analysis:

```text
POST http://127.0.0.1:5000/api/analyze-replay
```

Query parameters:

```text
symbol    default EUR/USD
timeframe default M5
bars      default 300
```

Supported timeframe labels:

```text
M1, M5, M15, H1, H4, D1
```

The Flask app converts those labels into Twelve Data intervals:

```text
M1  -> 1min
M5  -> 5min
M15 -> 15min
H1  -> 1h
H4  -> 4h
D1  -> 1day
```

The candle API returns Lightweight Charts records:

```text
time
open
high
low
close
```

The analysis API returns one current setup object:

```text
candles
analysis.symbol
analysis.display_symbol
analysis.api_symbol
analysis.asset_type
analysis.bias
analysis.setup_status
analysis.levels_mode
analysis.levels
analysis.overlays
analysis.setup_quality
analysis.trade_quality
analysis.trade_decision
analysis.objective_plan
analysis.trader_answers
analysis.answer_qa
analysis.answer_validation
analysis.temporal_validation
analysis.analysis_timestamp
analysis.time_metadata
analysis.summary
```

`setup_quality` measures the technical pattern. `trade_quality` measures whether
the available objective, stop distance, and reward-to-risk make the trade worth
taking. A setup can be technically complete while `trade_decision` is `REJECT`;
in that case TradeScor hides entry, stop, and target levels and explains why.

The default dashboard is driven by `trader_answers`, a rule-based explanation
layer that summarizes trend, price location, market intent, trade status, and
the reasons behind the current conclusion. Detailed strategy output remains
available in the collapsed **More Details** section.

The collapsed **Answer QA** lab shows answer provenance, missing-data warnings,
clarity reasoning, and validation results. During Replay Mode it stores the
answers for each analyzed replay candle and logs when trend, price location,
trade status, or the next action changes. Replay continues to use only the
already-loaded candles.
