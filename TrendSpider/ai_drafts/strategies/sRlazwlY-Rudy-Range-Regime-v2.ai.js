describe_indicator('Rudy Range Regime v2', 'price');

// NOTE: This is a direct, best-effort translation of a TradingView Pine
// Script v6 strategy. TrendSpider Custom JS does not have a native
// strategy engine (position/order simulation), so position tracking
// (strategy.entry / strategy.close, holdCount, basisPrice) is replicated
// with a manual bar-by-bar loop that mirrors the Pine logic as closely
// as possible. Also, Pine's strategy.entry() typically fills on the
// NEXT bar's open in real trading, while this reproduction (like the
// Pine backtester in "bar magnifier off" mode) applies entries/exits on
// the same bar the condition becomes true, matching the simplified
// Pine logic shown (no barstate.isconfirmed guard was used in source).

const myAdxLookback = input.number('ADX Lookback', 14, { min: 1, max: 200 });
const myAdxCeiling = input.number('ADX Ceiling', 25, { min: 1, max: 100 });
const myRsiLookback = input.number('RSI Lookback', 14, { min: 1, max: 200 });
const myRsiFloor = input.number('RSI Floor', 35, { min: 0, max: 100 });
const myRsiCeiling = input.number('RSI Ceiling', 65, { min: 0, max: 100 });
const myBbLookback = input.number('BB Lookback', 20, { min: 1, max: 200 });
const myBbWidthCeiling = input.number('BB Width Ceiling Pct', 8, { min: 0, max: 100 });
const myHoldDuration = input.number('Hold Duration Bars', 21, { min: 1, max: 500 });

// --- Core calculations ---
const myAdxObject = indicators.adx(myAdxLookback);
const myAdxValue = myAdxObject.adx;
const myRsiValue = rsi(close, myRsiLookback);

const myBbMid = sma(close, myBbLookback);
const myBbBand = compute_band(myBbMid, 'St.Dev.', 2, myBbLookback);
const myBbUpper = myBbBand.upper;
const myBbLower = myBbBand.lower;
const myBbWidth = for_every(myBbUpper, myBbLower, myBbMid, (_u, _l, _m) => _m ? ((_u - _l) / _m) * 100 : null);

// HV proxy: stdev(log(close/close[-1]), 20) * sqrt(252) * 100
const myLogReturn = for_every(close, shift(close, 1), (_c, _p) => (_p ? Math.log(_c / _p) : null));
const myStdevLogReturn = stdev(myLogReturn, 20);
const myHvProxy = mult(myStdevLogReturn, Math.sqrt(252) * 100);

// --- Regime detection ---
const myIsFlat = for_every(
	myAdxValue, myRsiValue, myBbWidth,
	(_adx, _rsi, _bw) => (_adx < myAdxCeiling && _rsi > myRsiFloor && _rsi < myRsiCeiling && _bw < myBbWidthCeiling)
);

// --- Manual position/strategy simulation ---
const myCollectSignal = series_of(false);
const myInPosition = series_of(false);
const myExitSignal = series_of(false);
const myExitReason = series_of(null);

let myHoldCount = 0;
let myBasisPrice = 0;
let myPositionSize = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myFlatHere = myIsFlat[myIndex];
	let myEntryHere = false;
	let myExitHere = false;
	let myExitReasonHere = null;

	if (myFlatHere && myPositionSize === 0) {
		myPositionSize = 1;
		myHoldCount = 0;
		myBasisPrice = close[myIndex];
		myEntryHere = true;
	}

	if (myPositionSize > 0) {
		myHoldCount += 1;
		const myDrawdown = ((close[myIndex] - myBasisPrice) / myBasisPrice) * 100;

		if (myHoldCount >= myHoldDuration) {
			myExitHere = true;
			myExitReasonHere = 'Duration Exit';
			myPositionSize = 0;
			myHoldCount = 0;
		}
		else if (myDrawdown < -5.0) {
			myExitHere = true;
			myExitReasonHere = 'Protective Exit';
			myPositionSize = 0;
			myHoldCount = 0;
		}
	}

	myCollectSignal[myIndex] = myEntryHere;
	myInPosition[myIndex] = myPositionSize > 0;
	myExitSignal[myIndex] = myExitHere;
	myExitReason[myIndex] = myExitReasonHere;
}

// --- Visuals ---
paint(myBbUpper, { name: 'BB Upper', color: '#9E9E9E', thickness: 1 });
paint(myBbLower, { name: 'BB Lower', color: '#9E9E9E', thickness: 1 });
paint(myBbMid, { name: 'BB Mid', color: '#9E9E9E', style: 'dotted', thickness: 1 });
paint(myAdxValue, { name: 'ADX', color: '#9C27B0', thickness: 2 });

// Candle coloring approximates Pine's bgcolor (flat = green tint, trend = red tint)
const myCandleColors = for_every(myIsFlat, _flat => (_flat ? '#4CAF50' : '#F44336'));
color_candles(myCandleColors);

// Collect shape (diamond above bar) on entries into "flat" regime while flat
const myCollectShape = for_every(myCollectSignal, _c => (_c ? constants.icons.diamond : null));
paint(myCollectShape, { name: 'Collect', style: 'labels_above', color: '#4CAF50' });

// --- Signals for scanner / alerts / strategy tester ---
register_signal(myIsFlat, 'Range Regime (isFlat)');
register_signal(myCollectSignal, 'Collect Entry');
register_signal(myInPosition, 'In Position');
register_signal(myExitSignal, 'Exit (Duration or Protective)');

// --- Dashboard overlay (static field layout, values computed from last candle) ---
const myLastAdx = myAdxValue[myAdxValue.length - 1];
const myLastRsi = myRsiValue[myRsiValue.length - 1];
const myLastBbWidth = myBbWidth[myBbWidth.length - 1];
const myLastHv = myHvProxy[myHvProxy.length - 1];
const myLastIsFlat = myIsFlat[myIsFlat.length - 1];

const myAdxColor = (myLastAdx < myAdxCeiling) ? '#00FF00' : '#FF0000';
const myRsiColor = (myLastRsi > myRsiFloor && myLastRsi < myRsiCeiling) ? '#00FF00' : '#FF0000';
const myBbwColor = (myLastBbWidth < myBbWidthCeiling) ? '#00FF00' : '#FF0000';
const myModeColor = myLastIsFlat ? '#00FF00' : '#FFA500';
const myModeText = myLastIsFlat ? 'RANGE' : 'TREND';

paint_overlay('RudyDashboard', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'ADX', color: '#FFFFFF' }, { text: (myLastAdx || 0).toFixed(1), color: myAdxColor }] },
		{ cells: [{ text: 'RSI', color: '#FFFFFF' }, { text: (myLastRsi || 0).toFixed(1), color: myRsiColor }] },
		{ cells: [{ text: 'BB W', color: '#FFFFFF' }, { text: (myLastBbWidth || 0).toFixed(1) + '%', color: myBbwColor }] },
		{ cells: [{ text: 'HV', color: '#FFFFFF' }, { text: (myLastHv || 0).toFixed(1) + '%', color: '#FFFFFF' }] },
		{ cells: [{ text: 'Mode', color: '#FFFFFF' }, { text: myModeText, color: myModeColor }] }
	]
});