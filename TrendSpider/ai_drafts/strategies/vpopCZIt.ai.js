describe_indicator('EMA RSI ATR Strategy AXSUSDT D', 'price');

// ─── Inputs, grouped like the Pine script ──────────────────────
const emaTab = input.tab('EMAs');
const emaRow = emaTab.row();
const myEmaFastLen = emaRow.number('EMA Rapida', 21, { min: 1, max: 500 });
const myEmaSlowLen = emaRow.number('EMA Lenta', 89, { min: 1, max: 500 });

const rsiTab = input.tab('RSI');
const rsiRow = rsiTab.row();
const myRsiLen = rsiRow.number('RSI Periodo', 14, { min: 1, max: 100 });
const myRsiLow = rsiRow.number('RSI Minimo', 55, { min: 0, max: 100 });
const myRsiHigh = rsiRow.number('RSI Maximo', 75, { min: 0, max: 100 });

const atrTab = input.tab('ATR');
const atrRow = atrTab.row();
const myAtrLen = atrRow.number('ATR Periodo', 14, { min: 1, max: 200 });
const myAtrMaLen = atrRow.number('ATR Media Periodo', 20, { min: 1, max: 200 });

const riskTab = input.tab('Gestion de riesgo');
const riskRow = riskTab.row();
const mySlMult = riskRow.number('Stop Loss ATR x', 2.5, { min: 0.1, max: 20 });
const myTpMult = riskRow.number('Take Profit ATR x', 4.0, { min: 0.1, max: 20 });

// ─── Core indicators (computed once, outside any loop) ─────────
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);
const myRsi = rsi(close, myRsiLen);
const myAtr = atr(high, low, close, myAtrLen);
const myAtrMa = sma(myAtr, myAtrMaLen);

// ─── Entry condition (same logic as Pine's longSignal) ──────────
const myTrendOk = for_every(myEmaFast, myEmaSlow, close, (_f, _s, _c) => _f > _s && _c > _f);
const myMomentumOk = for_every(myRsi, (_r) => _r > myRsiLow && _r < myRsiHigh);
const myVolatOk = for_every(myAtr, myAtrMa, (_a, _m) => _a > _m);
const myLongSignal = for_every(myTrendOk, myMomentumOk, myVolatOk, (_t, _mo, _v) => _t && _mo && _v);

// ─── Simulate the strategy's position state bar by bar ─────────
// Pine enters on next bar open after a signal closes, and tracks a single
// Long position with ATR-based stop/target fixed at entry. We reproduce
// that state machine here (position size, entry price, entry ATR).
const myPositionOpen = series_of(false);
const myEntryPrice = series_of(null);
const myEntryAtr = series_of(null);
const myStopPrice = series_of(null);
const myTpPrice = series_of(null);
const myEntryMarker = series_of(null);
const myExitMarker = series_of(null);

let myInPosition = false;
let myCurrentEntryPrice = null;
let myCurrentEntryAtr = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	// Check exit first (stop/limit), using previous bar's levels
	if (myInPosition) {
		const myStop = myCurrentEntryPrice - mySlMult * myCurrentEntryAtr;
		const myTp = myCurrentEntryPrice + myTpMult * myCurrentEntryAtr;

		if (low[myIndex] <= myStop || high[myIndex] >= myTp) {
			myInPosition = false;
			myExitMarker[myIndex] = (low[myIndex] <= myStop) ? myStop : myTp;
			myCurrentEntryPrice = null;
			myCurrentEntryAtr = null;
		}
	}

	// Entry: signal confirmed on this bar, executes conceptually at this bar's close context
	// (Pine enters on next bar open; here we flag the signal bar itself for scanning purposes)
	if (!myInPosition && myLongSignal[myIndex]) {
		myInPosition = true;
		myCurrentEntryPrice = close[myIndex];
		myCurrentEntryAtr = myAtr[myIndex];
		myEntryMarker[myIndex] = close[myIndex];
	}

	myPositionOpen[myIndex] = myInPosition;
	myEntryPrice[myIndex] = myCurrentEntryPrice;
	myEntryAtr[myIndex] = myCurrentEntryAtr;
	myStopPrice[myIndex] = myInPosition ? (myCurrentEntryPrice - mySlMult * myCurrentEntryAtr) : null;
	myTpPrice[myIndex] = myInPosition ? (myCurrentEntryPrice + myTpMult * myCurrentEntryAtr) : null;
}

// ─── Paint EMAs ──────────────────────────────────────────────
paint(myEmaFast, { name: 'EMA21', color: '#FF9800', thickness: 1 });
paint(myEmaSlow, { name: 'EMA89', color: '#2196F3', thickness: 2 });

// ─── Paint Stop Loss / Take Profit levels while in position ────
paint(myStopPrice, { name: 'StopLoss', color: '#EF5350', thickness: 1, style: 'ladder' });
paint(myTpPrice, { name: 'TakeProfit', color: '#26A69A', thickness: 1, style: 'ladder' });

// ─── Highlight entry signal candles (bgcolor equivalent) ────────
const myCandleColors = for_every(myLongSignal, (_l) => _l ? 'rgba(0,200,0,0.15)' : null);
color_candles(myCandleColors);

// ─── Signals for scanners, alerts and strategy tester ───────────
register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myPositionOpen, 'In Long Position');