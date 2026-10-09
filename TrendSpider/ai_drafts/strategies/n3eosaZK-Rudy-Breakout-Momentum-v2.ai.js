describe_indicator('Rudy Breakout Momentum v2', 'price');

// --- Parameters ---
const myLookback = input.number('High Lookback Bars', 126, { min: 1, max: 1000 });
const myEmaFastLen = input.number('Fast EMA Period', 21, { min: 1, max: 500 });
const myEmaSlowLen = input.number('Slow EMA Period', 50, { min: 1, max: 500 });
const myRsiLen = input.number('RSI Period', 14, { min: 1, max: 500 });
const myProfitPct = input.number('Profit Target Percent', 15.0, { min: 0, max: 1000 });
const myStopPct = input.number('Stop Loss Percent', 8.0, { min: 0, max: 100 });

// --- Core calculations (mirrors Pine's ta.highest/ta.ema/ta.rsi) ---
const myHigh126 = highest(high, myLookback);
const myEma21 = ema(close, myEmaFastLen);
const myEma50 = ema(close, myEmaSlowLen);
const myRsiVal = rsi(close, myRsiLen);

const myTrendUp = for_every(myEma21, myEma50, (_e21, _e50) => _e21 > _e50);

// newHigh compares current high to PREVIOUS bar's 126-high (Pine's high126[1])
const myHigh126Prev = shift(myHigh126, 1);
const myNewHigh = for_every(high, myHigh126Prev, (_h, _hprev) => _hprev !== null && _h >= _hprev);

const myRsiOk = for_every(myRsiVal, _r => _r < 80 && _r > 40);

const myBreakoutBuy = for_every(myNewHigh, myTrendUp, myRsiOk, (_nh, _tu, _ok) => Boolean(_nh && _tu && _ok));

// trendBroken: close < ema21 and prior close >= prior ema21
const myClosePrev = shift(close, 1);
const myEma21Prev = shift(myEma21, 1);
const myTrendBroken = for_every(close, myEma21, myClosePrev, myEma21Prev, (_c, _e, _cp, _ep) => {
	if (_cp === null || _ep === null) return false;
	return (_c < _e) && (_cp >= _ep);
});

// --- Simulated single-position state machine (sequential, mirrors strategy logic) ---
// NOTE: Pine's limit/stop exits can trigger intrabar (using high/low during the bar).
// This JS engine only has OHLC per candle, so profit target / stop loss are
// approximated by checking against the candle's high/low instead of true intrabar fills.
const myPositionSize = series_of(0);
const myEntryPrice = series_of(null);
const myBuySignal = series_of(false);
const myExitSignal = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevPos = myIndex > 0 ? myPositionSize[myIndex - 1] : 0;
	const myPrevEntry = myIndex > 0 ? myEntryPrice[myIndex - 1] : null;

	let myCurrentPos = myPrevPos;
	let myCurrentEntry = myPrevEntry;
	let myDidBuy = false;
	let myDidExit = false;

	if (myPrevPos === 0) {
		if (myBreakoutBuy[myIndex]) {
			myCurrentPos = 1;
			myCurrentEntry = close[myIndex];
			myDidBuy = true;
		}
	}
	else {
		const myTargetPx = myPrevEntry * (1 + myProfitPct / 100);
		const myStopPx = myPrevEntry * (1 - myStopPct / 100);

		if (high[myIndex] >= myTargetPx || low[myIndex] <= myStopPx || myTrendBroken[myIndex]) {
			myCurrentPos = 0;
			myCurrentEntry = null;
			myDidExit = true;
		}
	}

	myPositionSize[myIndex] = myCurrentPos;
	myEntryPrice[myIndex] = myCurrentEntry;
	myBuySignal[myIndex] = myDidBuy;
	myExitSignal[myIndex] = myDidExit;
}

// --- Visuals ---
paint(myEma21, { name: 'EMA21', color: '#00BCD4', thickness: 2 });
paint(myEma50, { name: 'EMA50', color: 'FF5722', thickness: 2 });
paint(myHigh126, { name: 'High126d', color: '#FFD700', thickness: 1, style: 'line' });

const myBuyLabelSeries = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const myExitLabelSeries = for_every(myExitSignal, high, (_x, _h) => _x ? _h : null);

paint(myBuyLabelSeries, { name: 'Breakout', style: 'labels_below', color: '#00E676' });
paint(myExitLabelSeries, { name: 'TrendBreak', style: 'labels_above', color: '#F44336' });

// --- Signals for scanner / alerts / strategy tester ---
register_signal(myBreakoutBuy, 'Breakout Condition');
register_signal(myTrendBroken, 'Trend Broken Condition');
register_signal(myBuySignal, 'Entry Signal');
register_signal(myExitSignal, 'Exit Signal');

// --- Dashboard overlay ---
const myLastIndex = close.length - 1;
const myNewHighText = myNewHigh[myLastIndex] ? 'YES' : 'NO';
const myTrendText = myTrendUp[myLastIndex] ? 'UP' : 'DOWN';
const myRsiText = myRsiVal[myLastIndex] !== null ? myRsiVal[myLastIndex].toFixed(1) : 'NA';
const myEma21Text = myEma21[myLastIndex] !== null ? myEma21[myLastIndex].toFixed(2) : 'NA';
const mySignalText = myBreakoutBuy[myLastIndex] ? 'BUY' : 'WAIT';

const myNewHighColor = myNewHigh[myLastIndex] ? '#00FF00' : '#FF0000';
const myTrendColor = myTrendUp[myLastIndex] ? '#00FF00' : '#FF0000';
const myRsiColor = myRsiOk[myLastIndex] ? '#00FF00' : '#FF0000';
const mySignalColor = myBreakoutBuy[myLastIndex] ? '#00FF00' : '#808080';

paint_overlay('RudyDashboard', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'New High', color: '#FFFFFF' }, { text: myNewHighText, color: myNewHighColor }] },
		{ cells: [{ text: 'Trend', color: '#FFFFFF' }, { text: myTrendText, color: myTrendColor }] },
		{ cells: [{ text: 'RSI', color: '#FFFFFF' }, { text: myRsiText, color: myRsiColor }] },
		{ cells: [{ text: 'EMA21', color: '#FFFFFF' }, { text: myEma21Text, color: '#FFFFFF' }] },
		{ cells: [{ text: 'Signal', color: '#FFFFFF' }, { text: mySignalText, color: mySignalColor }] }
	]
});