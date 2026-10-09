// This is a price-overlay indicator (not a strategy): TrendSpider custom
// scripts cannot submit broker orders, place stop/limit exits, or manage
// position sizing like a Pine strategy() script does. Entry/exit logic is
// reproduced as signals (register_signal) and visual labels only.
describe_indicator('Stable Main Force System v6', 'price');

const myVolMALength = input.number('Volume MA Length', 20, { min: 1, max: 500 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 500 });
const myObvEmaLength = input.number('OBV EMA Length', 5, { min: 1, max: 500 });
const myObvMaLength = input.number('OBV MA Length', 20, { min: 1, max: 500 });
const myBreakoutLookback = input.number('Breakout Lookback', 20, { min: 1, max: 500 });
const mySwingLowLength = input.number('Swing Low Length', 10, { min: 1, max: 500 });

// 1. Basic indicators
const myEma21 = ema(close, 21);
const myEma50 = ema(close, 50);
const myVolMA = sma(volume, myVolMALength);
const myAtr = atr(high, low, close, myAtrLength);

// Session-anchored VWAP (Pine ta.vwap() resets every new session by default)
const mySessionIds = time.map(_t => bar_at(_t).session);
const myVwap = series_of(null);
let myCumPV = 0;
let myCumV = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myIsNewSession = myIndex === 0 || mySessionIds[myIndex] !== mySessionIds[myIndex - 1];

	if (myIsNewSession) {
		myCumPV = 0;
		myCumV = 0;
	}

	const myTypicalPrice = hlc3[myIndex];
	myCumPV += myTypicalPrice * volume[myIndex];
	myCumV += volume[myIndex];
	myVwap[myIndex] = myCumV !== 0 ? myCumPV / myCumV : null;
}

// 2. Hand-rolled OBV (cumulative sum of signed volume), smoothed by EMA
const myObvRaw = for_every(close, volume, (_c, _v, _prev, _i) => {
	if (_i === 0) {
		return 0;
	}
	if (_c > close[_i - 1]) {
		return _prev + _v;
	}
	else if (_c < close[_i - 1]) {
		return _prev - _v;
	}
	return _prev;
});
const myObv = ema(myObvRaw, myObvEmaLength);
const myObvMA = sma(myObv, myObvMaLength);

// 3. Trend structure
const myTrend = for_every(myEma21, myEma50, (_e21, _e50) => _e21 > _e50);
const myAboveStructure = for_every(close, myEma50, (_c, _e50) => _c > _e50);

// 4. Accumulation & wash (shakeout)
const myAccum = for_every(close, myEma50, myEma21, myObv, myObvMA, (_c, _e50, _e21, _o, _oMA) =>
	_c > _e50 && _c < _e21 && _o > _oMA);
const myWash = for_every(close, myEma50, myEma21, volume, myVolMA, (_c, _e50, _e21, _v, _vMA) =>
	_c > _e50 && _c < _e21 && _v < _vMA);

// 5. Breakout (launch)
const myPrevHighHighest = highest(shift(high, 1), myBreakoutLookback);
const myBreakout = for_every(close, myPrevHighHighest, volume, myVolMA, (_c, _hh, _v, _vMA) =>
	_c > _hh && _v > _vMA * 1.2);
const myEntrySignal = for_every(myBreakout, myTrend, myObv, myObvMA, (_b, _t, _o, _oMA) =>
	_b && _t && _o > _oMA);

// 6. Structural stop loss
const mySwingLow = lowest(low, mySwingLowLength);
const myStopLoss = for_every(mySwingLow, myEma50, myAtr, (_sw, _e50, _a) =>
	Math.min(_sw, _e50) - _a * 0.5);

// 7. Risk per share (R)
const myRiskPerShare = for_every(close, myStopLoss, (_c, _sl) => {
	const myRisk = _c - _sl;
	return myRisk > 0 ? myRisk : null;
});
const myTakeProfit = for_every(close, myRiskPerShare, (_c, _r) => _r != null ? _c + _r * 2 : null);

// 8/9. Entry/exit are only representable as signals here (no order execution
// is possible in a custom indicator); register them so they can be used in
// Scanners, Alerts and the Strategy Tester.
register_signal(myEntrySignal, 'Entry Signal');
register_signal(myAccum, 'Accumulation');
register_signal(myWash, 'Wash');

// 10. Visualization
paint(myEma21, { color: '#2962FF', thickness: 2, name: 'EMA21' });
paint(myEma50, { color: '#FF9800', thickness: 2, name: 'EMA50' });
paint(myVwap, { color: '#9C27B0', thickness: 2, name: 'VWAP' });

// 11. Signal labels
const myAccumLabels = for_every(myAccum, low, (_a, _l) => _a ? _l : null);
const myWashLabels = for_every(myWash, low, (_w, _l) => _w ? _l : null);
const myEntryLabels = for_every(myEntrySignal, high, (_e, _h) => _e ? _h : null);

paint(myAccumLabels, { style: 'labels_below', color: 'green', name: 'Accumulation Label' });
paint(myWashLabels, { style: 'labels_below', color: '#CDDC39', name: 'Wash Label' });
paint(myEntryLabels, { style: 'labels_above', color: 'blue', name: 'Entry Label' });

// 12. Info panel - showing current R value as a label on the EMA21 line,
// since a free-floating per-bar text label (Pine's label.new/label.delete
// pattern) is not available in this scripting API.
// Note: thickness must be a positive value (0 is invalid), so this anchor
// line is hidden instead of using a zero thickness.
const myEma21Painted = paint(myEma21, { color: '#2962FF', thickness: 1, hidden: true, name: 'EMA21 Info Anchor' });
const myLastRiskValue = myRiskPerShare[myRiskPerShare.length - 1];

paint_label_at_line(
	myEma21Painted,
	close.length - 1,
	myLastRiskValue != null ? `R ${myLastRiskValue.toFixed(2)}` : 'R na',
	{ color: 'white', background_color: 'black' }
);