describe_indicator('Hybrid VWAP RSI Strategy Signals', 'price');

// NOTE: This is an indicator, not a strategy. TrendSpider Custom JS API
// has no strategy.entry/strategy.exit/backtest engine for custom scripts.
// This reproduces the Pine signal logic (VWAP, RSI, trend filter,
// volatility filter, long/short conditions) and exposes them as
// register_signal() outputs so they can be used in Scanners, Alerts
// and the Strategy Tester component. Position sizing and trailing
// exits are not reproducible here.

const myRsiLength = input.number('RSI Length', 14, { min: 5, max: 30 });
const myRsiOversold = input.number('RSI Oversold (Long)', 32, { min: 20, max: 40 });
const myRsiOverbought = input.number('RSI Overbought (Short)', 68, { min: 60, max: 80 });
const myVwapResetHour = input.number('VWAP Reset Hour (Local Time)', 9, { min: 0, max: 23 });

const myUseTrendFilter = input.boolean('Use Trend Filter (SPY 200MA)', true);
const myTrendSymbol = input.symbol('Trend Symbol', 'SPY');

const myAtrLength = input.number('ATR Length', 14, { min: 5, max: 50 });

// === VWAP (session anchored to reset hour) ===
const myCumulativePV = series_of(null);
const myCumulativeVol = series_of(null);
const myVwap = series_of(null);

for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myIsNewSession = myIndex === 0 || (myTimeInfo.hours === myVwapResetHour && myTimeInfo.minutes === 0);
	const myHl2Value = (high[myIndex] + low[myIndex]) / 2;

	if (myIsNewSession) {
		myCumulativePV[myIndex] = myHl2Value * volume[myIndex];
		myCumulativeVol[myIndex] = volume[myIndex];
	}
	else {
		myCumulativePV[myIndex] = myCumulativePV[myIndex - 1] + myHl2Value * volume[myIndex];
		myCumulativeVol[myIndex] = myCumulativeVol[myIndex - 1] + volume[myIndex];
	}

	myVwap[myIndex] = myCumulativePV[myIndex] / myCumulativeVol[myIndex];
}

// === Market Trend filter (SPY close > SMA200 on Daily) ===
const myTrendData = myUseTrendFilter ? await request.history(myTrendSymbol, 'D') : null;
assert(!myUseTrendFilter || !myTrendData.error, `Error fetching trend data: "${myTrendData && myTrendData.error}"`);

let myMarketTrendSeries;
if (myUseTrendFilter) {
	const myTrendSma = sma(myTrendData.close, 200);
	const myTrendFlagSparse = myTrendData.close.map((myCloseValue, myI) => myCloseValue > myTrendSma[myI] ? 1 : 0);
	const myLanded = land_points_onto_series(myTrendData.time, myTrendFlagSparse, time, 'le');
	myMarketTrendSeries = interpolate_sparse_series(myLanded, 'constant');
}
else {
	myMarketTrendSeries = series_of(1);
}

// === ATR / Volatility filter ===
const myAtr = atr(high, low, close, myAtrLength);
const myAtrRatio = div(myAtr, close);
const myRsi = rsi(close, myRsiLength);

// === Entry Conditions ===
const myLongCondition = for_every(myMarketTrendSeries, close, myVwap, myRsi, myAtrRatio, (_trend, _close, _vwap, _rsi, _atrr) => {
	const myHighVol = _atrr > 0.01;
	return (!!_trend) && (_close < _vwap) && (_rsi < myRsiOversold) && myHighVol;
});

const myShortCondition = for_every(myMarketTrendSeries, close, myVwap, myRsi, myAtrRatio, (_trend, _close, _vwap, _rsi, _atrr) => {
	const myHighVol = _atrr > 0.01;
	return (!_trend) && (_close > _vwap) && (_rsi > myRsiOverbought) && myHighVol;
});

// === Visuals ===
paint(myVwap, { name: 'VWAP', color: '#9b59b6', thickness: 2 });

const myLongMarks = for_every(myLongCondition, _long => _long ? constants.icons.triangle_up : null);
const myShortMarks = for_every(myShortCondition, _short => _short ? constants.icons.triangle_down : null);

paint(myLongMarks, { name: 'LongSignal', style: 'labels_below', color: 'green' });
paint(myShortMarks, { name: 'ShortSignal', style: 'labels_above', color: 'red' });

// === Signals for Scanners/Alerts/Strategy Tester ===
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');