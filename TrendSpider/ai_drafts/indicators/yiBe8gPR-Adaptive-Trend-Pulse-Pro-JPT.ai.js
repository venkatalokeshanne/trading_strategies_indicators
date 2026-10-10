describe_indicator('Liquidity Sweep Engine Auto Targets', 'price');

// ===== Inputs =====
const myPivotLen = input.number('Swing Length', 5, { min: 2, max: 100 });
const myUseCloseConfirmation = input.boolean('Require Close Back Inside', true);
const myRowRR = input.row();
const myRR1 = myRowRR.number('TP1 RR', 1.0, { min: 0.1, max: 20, step: 0.5 });
const myRR2 = myRowRR.number('TP2 RR', 2.0, { min: 0.1, max: 20, step: 0.5 });
const myRR3 = myRowRR.number('TP3 RR', 3.0, { min: 0.1, max: 20, step: 0.5 });
const myExtendBars = input.number('Line Length', 30, { min: 1, max: 500 });

// ===== Pivots =====
// ta.pivothigh/pivotlow with equal left/right length maps to pivot_high/pivot_low
const myPivotHighs = pivot_high(high, myPivotLen, myPivotLen);
const myPivotLows = pivot_low(low, myPivotLen, myPivotLen);

// ===== Carry forward last swing high/low (var float in Pine) =====
const myLastSwingHigh = for_every(myPivotHighs, high, (_ph, _h, _prev) => _ph !== null ? _ph : (_prev === undefined ? null : _prev));
const myLastSwingLow = for_every(myPivotLows, low, (_pl, _l, _prev) => _pl !== null ? _pl : (_prev === undefined ? null : _prev));

// ===== Sweep detection =====
const myBuySideSweep = for_every(high, close, myLastSwingHigh, (_h, _c, _lsh) => {
	if (_lsh === null || _lsh === undefined) return false;
	const myCloseOk = myUseCloseConfirmation ? _c < _lsh : true;
	return _h > _lsh && myCloseOk;
});

const mySellSideSweep = for_every(low, close, myLastSwingLow, (_l, _c, _lsl) => {
	if (_lsl === null || _lsl === undefined) return false;
	const myCloseOk = myUseCloseConfirmation ? _c > _lsl : true;
	return _l < _lsl && myCloseOk;
});

// ===== Register signals for scanners/alerts/strategies =====
register_signal(myBuySideSweep, 'Buy Side Liquidity Sweep');
register_signal(mySellSideSweep, 'Sell Side Liquidity Sweep');

// ===== Find the most recent sweep event (Pine keeps only one set of lines/labels at a time) =====
let myLastEventIndex = -1;
let myLastEventType = null; // 'sell' triggers BUY setup, 'buy' triggers SELL setup (per Pine logic)

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (mySellSideSweep[myIndex]) {
		myLastEventIndex = myIndex;
		myLastEventType = 'buy_setup';
	}
	if (myBuySideSweep[myIndex]) {
		myLastEventIndex = myIndex;
		myLastEventType = 'sell_setup';
	}
}

// ===== Build Entry/SL/TP lines for the latest active setup =====
let myEntryLine = series_of(null);
let mySlLine = series_of(null);
let myTp1Line = series_of(null);
let myTp2Line = series_of(null);
let myTp3Line = series_of(null);
let myLabelText = 'None';
let myLabelIndexToUse = -1;

if (myLastEventIndex >= 0) {
	const myEntry = close[myLastEventIndex];
	let myStop = null;
	let myTp1 = null;
	let myTp2 = null;
	let myTp3 = null;

	if (myLastEventType === 'buy_setup') {
		myStop = low[myLastEventIndex];
		const myRisk = myEntry - myStop;
		myTp1 = myEntry + myRisk * myRR1;
		myTp2 = myEntry + myRisk * myRR2;
		myTp3 = myEntry + myRisk * myRR3;
		myLabelText = 'BUY Entry';
	}
	else {
		myStop = high[myLastEventIndex];
		const myRisk = myStop - myEntry;
		myTp1 = myEntry - myRisk * myRR1;
		myTp2 = myEntry - myRisk * myRR2;
		myTp3 = myEntry - myRisk * myRR3;
		myLabelText = 'SELL Entry';
	}

	// Clamp the target index to the last available candle, since line()
	// (and label placement) cannot reference an index beyond the data set.
	const myToIndex = Math.min(myLastEventIndex + myExtendBars, close.length - 1);

	myEntryLine = line(myLastEventIndex, myEntry, myToIndex, myEntry, false);
	mySlLine = line(myLastEventIndex, myStop, myToIndex, myStop, false);
	myTp1Line = line(myLastEventIndex, myTp1, myToIndex, myTp1, false);
	myTp2Line = line(myLastEventIndex, myTp2, myToIndex, myTp2, false);
	myTp3Line = line(myLastEventIndex, myTp3, myToIndex, myTp3, false);

	myLabelIndexToUse = myToIndex;
}

// ===== Paint lines (always same number/order of paint calls) =====
const myEntryLinePainted = paint(myEntryLine, { name: 'EntryLine', color: '#2196F3', thickness: 2 });
const mySlLinePainted = paint(mySlLine, { name: 'StopLine', color: 'red', thickness: 2 });
const myTp1LinePainted = paint(myTp1Line, { name: 'TP1Line', color: 'green', thickness: 1 });
const myTp2LinePainted = paint(myTp2Line, { name: 'TP2Line', color: 'green', thickness: 1 });
const myTp3LinePainted = paint(myTp3Line, { name: 'TP3Line', color: 'green', thickness: 1 });

// ===== Labels on the lines (placed at the clamped end point when a setup exists) =====
if (myLastEventIndex >= 0 && myLabelIndexToUse >= 0) {
	paint_label_at_line(myEntryLinePainted, myLabelIndexToUse, myLabelText, { background_color: '#2196F3' });
	paint_label_at_line(mySlLinePainted, myLabelIndexToUse, 'SL', { background_color: 'red' });
	paint_label_at_line(myTp1LinePainted, myLabelIndexToUse, 'TP1', { background_color: 'green' });
	paint_label_at_line(myTp2LinePainted, myLabelIndexToUse, 'TP2', { background_color: 'green' });
	paint_label_at_line(myTp3LinePainted, myLabelIndexToUse, 'TP3', { background_color: 'green' });
}

// ===== Sweep shapes (triangles with text labels on candles) =====
const myBuySideShape = for_every(myBuySideSweep, _s => _s ? constants.icons.triangle_down : null);
const mySellSideShape = for_every(mySellSideSweep, _s => _s ? constants.icons.triangle_up : null);

paint(myBuySideShape, { style: 'labels_above', color: 'red', name: 'BuySideSweep' });
paint(mySellSideShape, { style: 'labels_below', color: 'lime', name: 'SellSideSweep' });

// ===== Background tint on sweep candles =====
const myCandleColors = for_every(myBuySideSweep, mySellSideSweep, (_buy, _sell) => {
	if (_buy) return 'rgba(255,0,0,0.1)';
	if (_sell) return 'rgba(0,255,0,0.1)';
	return null;
});
color_candles(myCandleColors);