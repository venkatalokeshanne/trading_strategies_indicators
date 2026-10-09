describe_indicator('Rudy Range Regime v2', 'lower');

// --- Parameters ---
const myAdxTab = input.tab('Regime Parameters');
const myAdxRow = myAdxTab.row();
const myAdxLen = myAdxRow.number('ADX Lookback', 14, { min: 1, max: 100 });
const myAdxLim = myAdxRow.number('ADX Ceiling', 25, { min: 1, max: 100 });

const myRsiRow = myAdxTab.row();
const myRsiLen = myRsiRow.number('RSI Lookback', 14, { min: 1, max: 100 });
const myRsiLo = myRsiRow.number('RSI Floor', 35, { min: 0, max: 100 });
const myRsiHi = myRsiRow.number('RSI Ceiling', 65, { min: 0, max: 100 });

const myBbRow = myAdxTab.row();
const myBbLen = myBbRow.number('BB Lookback', 20, { min: 1, max: 200 });
const myBbLim = myBbRow.number('BB Width Ceiling Pct', 8.0, { min: 0, max: 100 });

const myHoldDuration = myAdxTab.number('Hold Duration Bars', 21, { min: 1, max: 500 });

// --- Calculations ---
const myAdxObject = indicators.adx(myAdxLen);
const myAdxValue = myAdxObject.adx;
const myRsiValue = rsi(close, myRsiLen);

const myBbMid = sma(close, myBbLen);
const myBbStdev = stdev(close, myBbLen);
const myBbUpper = add(myBbMid, mult(myBbStdev, 2));
const myBbLower = sub(myBbMid, mult(myBbStdev, 2));
const myBbWidth = mult(div(sub(myBbUpper, myBbLower), myBbMid), 100);

// HV proxy: stdev of log returns over 20 bars, annualized
const myLogReturns = for_every(close, (_c, _prev, _i) => {
	// placeholder, computed below properly
	return null;
});
const myCloseShifted = shift(close, 1);
const myLogReturnSeries = for_every(close, myCloseShifted, (_c, _cPrev) => {
	if (_cPrev === null || _cPrev === undefined || _cPrev === 0 || _c === null) return null;
	return Math.log(_c / _cPrev);
});
const myHvStdev = stdev(myLogReturnSeries, 20);
const myHvProxy = mult(myHvStdev, Math.sqrt(252) * 100);

// --- Regime Detection ---
const myIsFlat = for_every(myAdxValue, myRsiValue, myBbWidth, (_adx, _rsi, _bbw) => {
	if (_adx === null || _rsi === null || _bbw === null) return false;
	return _adx < myAdxLim && _rsi > myRsiLo && _rsi < myRsiHi && _bbw < myBbLim;
});

// --- Position Tracking (sequential state machine, replicating Pine strategy logic) ---
// NOTE: this emulates the strategy's position/entry/exit logic as signal series,
// since this is an indicator script (not an actual strategy / backtester).
const myPositionActive = series_of(null);
const myEntrySignal = series_of(null);
const myDurationExitSignal = series_of(null);
const myProtectiveExitSignal = series_of(null);
const myHoldCountSeries = series_of(null);

let myHoldCount = 0;
let myBasisPrice = 0;
let myInPosition = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	let myEntryHappened = false;
	let myDurationExitHappened = false;
	let myProtectiveExitHappened = false;

	if (myIsFlat[myIndex] && !myInPosition) {
		myInPosition = true;
		myHoldCount = 0;
		myBasisPrice = close[myIndex];
		myEntryHappened = true;
	}

	if (myInPosition) {
		myHoldCount += 1;
		const myDrawdownPct = (close[myIndex] - myBasisPrice) / myBasisPrice * 100;

		if (myHoldCount >= myHoldDuration) {
			myInPosition = false;
			myHoldCount = 0;
			myDurationExitHappened = true;
		}
		else if (myDrawdownPct < -5.0) {
			myInPosition = false;
			myHoldCount = 0;
			myProtectiveExitHappened = true;
		}
	}

	myPositionActive[myIndex] = myInPosition;
	myEntrySignal[myIndex] = myEntryHappened;
	myDurationExitSignal[myIndex] = myDurationExitHappened;
	myProtectiveExitSignal[myIndex] = myProtectiveExitHappened;
	myHoldCountSeries[myIndex] = myHoldCount;
}

const myCollectShape = for_every(myIsFlat, myPositionActive, (_flat, _pos) => (_flat && !_pos) ? true : false);

// --- Signals for Scanner/Alerts/Strategy Tester ---
register_signal(myIsFlat, 'Range Regime Active');
register_signal(myEntrySignal, 'Entry Collect Premium');
register_signal(myDurationExitSignal, 'Duration Exit');
register_signal(myProtectiveExitSignal, 'Protective Exit');
register_signal(myPositionActive, 'Position Active');

// --- Visuals ---
paint(myBbUpper, { name: 'BB Upper', color: '#9E9E9E', thickness: 1, forceUsePriceAxis: true });
paint(myBbLower, { name: 'BB Lower', color: '#9E9E9E', thickness: 1, forceUsePriceAxis: true });
paint(myBbMid, { name: 'BB Mid', color: '#BDBDBD', thickness: 1, style: 'dotted', forceUsePriceAxis: true });
paint(myAdxValue, { name: 'ADX', color: '#9C27B0', thickness: 2 });

// Approximate bgcolor regime coloring via candle coloring (closest substitute available)
const myRegimeCandleColors = for_every(myIsFlat, _flat => _flat ? 'rgba(76,175,80,0.25)' : 'rgba(244,67,54,0.1)');
color_candles(myRegimeCandleColors);

const myCollectMarks = for_every(myCollectShape, close, (_flagged, _c) => _flagged ? _c : null);
paint(myCollectMarks, { name: 'Collect', style: 'labels_above', color: '#4CAF50', forceUsePriceAxis: true });

// --- Dashboard ---
const myLastIndex = myAdxValue.length - 1;
const myAdxText = myAdxValue[myLastIndex] !== null ? myAdxValue[myLastIndex].toFixed(1) : 'NA';
const myRsiText = myRsiValue[myLastIndex] !== null ? myRsiValue[myLastIndex].toFixed(1) : 'NA';
const myBbWidthText = myBbWidth[myLastIndex] !== null ? myBbWidth[myLastIndex].toFixed(1) + '%' : 'NA';
const myHvText = myHvProxy[myLastIndex] !== null ? myHvProxy[myLastIndex].toFixed(1) + '%' : 'NA';
const myModeText = myIsFlat[myLastIndex] ? 'RANGE' : 'TREND';

const myAdxColor = (myAdxValue[myLastIndex] !== null && myAdxValue[myLastIndex] < myAdxLim) ? '#00FF00' : '#FF0000';
const myRsiColor = (myRsiValue[myLastIndex] !== null && myRsiValue[myLastIndex] > myRsiLo && myRsiValue[myLastIndex] < myRsiHi) ? '#00FF00' : '#FF0000';
const myBbColor = (myBbWidth[myLastIndex] !== null && myBbWidth[myLastIndex] < myBbLim) ? '#00FF00' : '#FF0000';
const myModeColor = myIsFlat[myLastIndex] ? '#00FF00' : '#FFA500';

paint_overlay('RudyDashboard', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'ADX', color: '#FFFFFF' }, { text: myAdxText, color: myAdxColor }] },
		{ cells: [{ text: 'RSI', color: '#FFFFFF' }, { text: myRsiText, color: myRsiColor }] },
		{ cells: [{ text: 'BB W', color: '#FFFFFF' }, { text: myBbWidthText, color: myBbColor }] },
		{ cells: [{ text: 'HV', color: '#FFFFFF' }, { text: myHvText, color: '#FFFFFF' }] },
		{ cells: [{ text: 'Mode', color: '#FFFFFF' }, { text: myModeText, color: myModeColor }] }
	]
});