describe_indicator('Stochastic Bot with SL/TP', 'lower');

// --- Inputs ---
const myKLength = input.number('%K Length', 14, { min: 1, max: 200 });
const mySmoothK = input.number('%K Smoothing', 3, { min: 1, max: 50 });
const myDLength = input.number('%D Smoothing', 3, { min: 1, max: 50 });
const mySlPct = input.number('Stop Loss (%)', 2.5, { min: 0.1, max: 50, step: 0.1 });
const myTpPct = input.number('Take Profit (%)', 6.0, { min: 0.1, max: 100, step: 0.1 });

// --- Stochastic calculation (matches TradingView's ta.stoch + ta.sma smoothing) ---
const myRawStoch = stochastic(close, high, low, myKLength);
const myK = sma(myRawStoch, mySmoothK);
const myD = sma(myK, myDLength);

// --- Crossover / Crossunder detection ---
const myCrossOver = for_every(myK, myD, (_k, _d, _prev, _i) => {
	if (_i === 0) return false;
	return myK[_i - 1] <= myD[_i - 1] && _k > _d;
});

const myCrossUnder = for_every(myK, myD, (_k, _d, _prev, _i) => {
	if (_i === 0) return false;
	return myK[_i - 1] >= myD[_i - 1] && _k < _d;
});

// Buy Signal: K crosses above D while K < 20
const myBuySignal = for_every(myCrossOver, myK, (_co, _k) => _co && _k < 20);

// Sell Signal: K crosses below D while K > 60
const mySellSignal = for_every(myCrossUnder, myK, (_cu, _k) => _cu && _k > 60);

// --- Position simulation (mirrors the Pine strategy logic) ---
// We track position state sequentially since exits depend on entry price,
// stop/take-profit levels and the sell signal, exactly like the Pine script.
const myLongEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myStopLevelSeries = series_of(null);
const myProfitLevelSeries = series_of(null);

let myInPosition = false;
let myEntryPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	let myDidExitThisBar = false;

	if (myInPosition) {
		const myStopLevel = myEntryPrice * (1 - mySlPct / 100);
		const myProfitLevel = myEntryPrice * (1 + myTpPct / 100);

		myStopLevelSeries[myIndex] = myStopLevel;
		myProfitLevelSeries[myIndex] = myProfitLevel;

		// Check SL/TP hit using this candle's range (intrabar, like TradingView stop/limit orders)
		const myHitStop = low[myIndex] <= myStopLevel;
		const myHitProfit = high[myIndex] >= myProfitLevel;
		const myHitSell = mySellSignal[myIndex];

		if (myHitStop || myHitProfit || myHitSell) {
			myLongExitSignal[myIndex] = true;
			myInPosition = false;
			myEntryPrice = null;
			myDidExitThisBar = true;
		}
	}
	else {
		myStopLevelSeries[myIndex] = null;
		myProfitLevelSeries[myIndex] = null;
	}

	// Enter a new long position on a buy signal, only if currently flat
	if (!myInPosition && !myDidExitThisBar && myBuySignal[myIndex]) {
		myLongEntrySignal[myIndex] = true;
		myInPosition = true;
		myEntryPrice = close[myIndex];
	}
}

// --- Painting ---
paint(myK, { name: 'StochK', color: '#2E93fA', thickness: 2 });
paint(myD, { name: 'StochD', color: '#F6A623', thickness: 2 });
paint(horizontal_line(20), { name: 'Oversold', color: 'gray', style: 'dotted' });
paint(horizontal_line(60), { name: 'Overbought', color: 'gray', style: 'dotted' });

const myStopLinePainted = paint(myStopLevelSeries, { name: 'StopLevel', color: '#EF5350', style: 'ladder', forceUsePriceAxis: true });
const myProfitLinePainted = paint(myProfitLevelSeries, { name: 'ProfitLevel', color: '#26A69A', style: 'ladder', forceUsePriceAxis: true });

// --- Signals for scanner, alerts, strategy tester ---
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myLongExitSignal, 'Long Exit');