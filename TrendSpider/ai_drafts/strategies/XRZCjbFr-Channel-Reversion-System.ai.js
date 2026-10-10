describe_indicator('Channel Reversion System', 'price');

// ─────────────────────────────────────────────────────────────
// Converted from a Pine Script v6 strategy. Since Custom JS
// indicators cannot place real orders or manage strategy equity,
// this reproduces the exact same signal logic (entries/exits)
// as plain boolean series, mapped out for scanners/alerts via
// register_signal(). The channel/trend lines and the "BUY" labels
// are painted exactly as in the original script.
// ─────────────────────────────────────────────────────────────

const myChanLenTab = input.tab('Channel Reversion System');
const myChanLenRow = myChanLenTab.row();
const myChanLen = myChanLenRow.number('Channel length (days)', 50, { min: 10, max: 500 });
const myZonePct = myChanLenRow.number('Entry zone (% of channel)', 25, { min: 5, max: 50, step: 5 });

const mySmaLenRow = myChanLenTab.row();
const mySmaLen = mySmaLenRow.number('Trend SMA length', 200, { min: 50, max: 500 });
const myAtrLen = mySmaLenRow.number('ATR length', 14, { min: 5, max: 100 });
const myAtrMult = mySmaLenRow.number('Stop: ATR below channel', 1.0, { min: 0.25, max: 10, step: 0.25 });

// Donchian channel using PRIOR bar's highest/lowest (the Pine [1] shift)
const myUpperD = shift(highest(high, myChanLen), 1);
const myLowerD = shift(lowest(low, myChanLen), 1);
const myMidD = div(add(myUpperD, myLowerD), 2);
const myZoneTop = add(myLowerD, mult(sub(myUpperD, myLowerD), myZonePct / 100));

const myAtr = atr(high, low, close, myAtrLen);
const mySmaT = sma(close, mySmaLen);
const myTrendOK = for_every(close, mySmaT, (_c, _s) => _c > _s);

// ─────────────────────────────────────────────────────────────
// Sequential state machine (mirrors strategy.position_size logic).
// Plain arithmetic loop only, no indicator calls inside it.
// Note: "new Array(...)" is not allowed by the engine (no "new"
// keyword permitted), so we build arrays via Array(n).fill(...)
// instead, which works the same way without using "new".
// ─────────────────────────────────────────────────────────────
const myCandleCount = close.length;
const myInPosEntering = Array(myCandleCount).fill(false);
const myBuySignal = Array(myCandleCount).fill(false);
const myExitTarget = Array(myCandleCount).fill(false);
const myExitStop = Array(myCandleCount).fill(false);
const myExitTrend = Array(myCandleCount).fill(false);

let myState = false;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	myInPosEntering[myIndex] = myState;

	const myCloseValue = close[myIndex];
	const myZoneTopValue = myZoneTop[myIndex];
	const myMidDValue = myMidD[myIndex];
	const myLowerDValue = myLowerD[myIndex];
	const myAtrValue = myAtr[myIndex];
	const mySmaTValue = mySmaT[myIndex];
	const myTrendOKValue = myTrendOK[myIndex];

	const myDataReady = myZoneTopValue != null && myMidDValue != null && myLowerDValue != null && myAtrValue != null && mySmaTValue != null;

	if (!myState) {
		const myBuy = myDataReady && myTrendOKValue && myCloseValue <= myZoneTopValue;
		myBuySignal[myIndex] = myBuy;
		myState = myBuy;
	}
	else {
		if (myCloseValue >= myMidDValue) {
			myExitTarget[myIndex] = true;
			myState = false;
		}
		else if (myCloseValue < myLowerDValue - myAtrValue * myAtrMult) {
			myExitStop[myIndex] = true;
			myState = false;
		}
		else if (myCloseValue < mySmaTValue) {
			myExitTrend[myIndex] = true;
			myState = false;
		}
	}
}

register_signal(myBuySignal, 'Buy Signal');
register_signal(myExitTarget, 'Exit Target');
register_signal(myExitStop, 'Exit Stop');
register_signal(myExitTrend, 'Exit Trend Break');
register_signal(myInPosEntering, 'In Position');

// ─────────────────────────────────────────────────────────────
// Painting
// ─────────────────────────────────────────────────────────────
const myUpperLine = paint(myUpperD, { name: 'Channel High', color: '#787b86', thickness: 1 });
const myLowerLine = paint(myLowerD, { name: 'Channel Low', color: '#787b86', thickness: 1 });
const myZoneLine = paint(myZoneTop, { name: 'Buy Zone Top', color: '#26a69a', thickness: 1 });
paint(myMidD, { name: 'Channel Mid', color: '#f0b90b', thickness: 1 });

const myTrendColor = for_every(myTrendOK, _t => _t ? '#26a69a' : '#ef5350');
paint(mySmaT, { name: 'Trend SMA', color: myTrendColor, thickness: 2 });

fill(myUpperLine, myZoneLine, '#787b86', 0.08);
fill(myZoneLine, myLowerLine, '#26a69a', 0.12);

const myBuyMarks = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
paint(myBuyMarks, { name: 'Buy Marker', style: 'labels_below', color: '#26a69a' });

const myLastIndex = myCandleCount - 1;
const myPosPct = ((close[myLastIndex] - myLowerD[myLastIndex]) / Math.max(myUpperD[myLastIndex] - myLowerD[myLastIndex], 0.0001)) * 100;

paint_overlay('CRSTable', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'CRS' }, { text: myTrendOK[myLastIndex] ? 'TREND OK' : 'NO TREND', color: myTrendOK[myLastIndex] ? '#26a69a' : '#ef5350' }] },
		{ cells: [{ text: 'Channel pos' }, { text: myPosPct.toFixed(0) + '%' }] },
		{ cells: [{ text: 'Buy zone' }, { text: '< ' + myZoneTop[myLastIndex].toFixed(2) }] },
		{ cells: [{ text: 'Target' }, { text: myMidD[myLastIndex].toFixed(2) }] }
	]
});