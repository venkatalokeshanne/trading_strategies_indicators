describe_indicator('TradeWise Price Action', 'price');

// ===== INPUTS =====
const mySwingLen = input.number('Swing Lookback', 10, { min: 1, max: 200 });
const myMinSL = input.number('Min SL ($)', 3.0, { min: 0, max: 1000 });
const myMaxSL = input.number('Max SL ($)', 7.0, { min: 0, max: 1000 });
const myRR1 = 1.0;
const myRR2 = 1.5;
const myRR3 = 2.0;

// ===== SWINGS =====
// swingHigh/swingLow use trailing highest/lowest, then shifted by 1
// to replicate Pine's [1] historical reference (no future data used)
const mySwingHigh = shift(highest(high, mySwingLen), 1);
const mySwingLow = shift(lowest(low, mySwingLen), 1);

// ===== LIQUIDITY SWEEPS =====
const mySweepHigh = for_every(high, mySwingHigh, (_h, _sh) => _sh !== null && _h > _sh);
const mySweepLow = for_every(low, mySwingLow, (_l, _sl) => _sl !== null && _l < _sl);

// ===== REJECTION CANDLES =====
const myBullReject = for_every(mySweepLow, close, open, mySwingLow, (_sweep, _c, _o, _sl) => _sweep && _c > _o && _sl !== null && _c > _sl);
const myBearReject = for_every(mySweepHigh, close, open, mySwingHigh, (_sweep, _c, _o, _sh) => _sweep && _c < _o && _sh !== null && _c < _sh);

// ===== SIGNALS =====
const myBuySignal = myBullReject;
const mySellSignal = myBearReject;

// ===== STOP LOSS / TAKE PROFITS (per candle) =====
const myBuyDistRaw = sub(close, low);
const mySellDistRaw = sub(high, close);
const myBuyDist = for_every(myBuyDistRaw, _d => Math.max(myMinSL, Math.min(_d, myMaxSL)));
const mySellDist = for_every(mySellDistRaw, _d => Math.max(myMinSL, Math.min(_d, myMaxSL)));

const myBuySL = sub(close, myBuyDist);
const mySellSL = add(close, mySellDist);

const myBuyTP1 = add(close, mult(myBuyDist, myRR1));
const myBuyTP2 = add(close, mult(myBuyDist, myRR2));
const myBuyTP3 = add(close, mult(myBuyDist, myRR3));

const mySellTP1 = sub(close, mult(mySellDist, myRR1));
const mySellTP2 = sub(close, mult(mySellDist, myRR2));
const mySellTP3 = sub(close, mult(mySellDist, myRR3));

// ===== SIGNAL MARKERS (replicates plotshape triangles) =====
const myBuyMarks = for_every(myBuySignal, low, (_sig, _l) => _sig ? _l : null);
const mySellMarks = for_every(mySellSignal, high, (_sig, _h) => _sig ? _h : null);

paint(myBuyMarks, { style: 'labels_below', color: 'lime', name: 'Buy Signal Marker' });
paint(mySellMarks, { style: 'labels_above', color: 'red', name: 'Sell Signal Marker' });

// ===== PROJECTED LINES FOR THE MOST RECENT SIGNAL =====
// We locate the most recent buy/sell signal and draw projected levels
// from that point. The "to_index" is clamped to the last available
// candle to avoid an out-of-range error.
const myLastCandleIndex = close.length - 1;
const myProjectionBars = 25;

let myLastSignalIndex = -1;
let myLastSignalType = null;

for (let myIndex = 0; myIndex <= myLastCandleIndex; myIndex += 1) {
	if (myBuySignal[myIndex]) {
		myLastSignalIndex = myIndex;
		myLastSignalType = 'buy';
	}
	else if (mySellSignal[myIndex]) {
		myLastSignalIndex = myIndex;
		myLastSignalType = 'sell';
	}
}

let myEntryLine = series_of(null);
let mySlLine = series_of(null);
let myTp1Line = series_of(null);
let myTp2Line = series_of(null);
let myTp3Line = series_of(null);

if (myLastSignalIndex >= 0) {
	const myRightIndex = Math.min(myLastSignalIndex + myProjectionBars, myLastCandleIndex);
	const myEntryValue = close[myLastSignalIndex];
	const mySlValue = myLastSignalType === 'buy' ? myBuySL[myLastSignalIndex] : mySellSL[myLastSignalIndex];
	const myTp1Value = myLastSignalType === 'buy' ? myBuyTP1[myLastSignalIndex] : mySellTP1[myLastSignalIndex];
	const myTp2Value = myLastSignalType === 'buy' ? myBuyTP2[myLastSignalIndex] : mySellTP2[myLastSignalIndex];
	const myTp3Value = myLastSignalType === 'buy' ? myBuyTP3[myLastSignalIndex] : mySellTP3[myLastSignalIndex];

	myEntryLine = line(myLastSignalIndex, myEntryValue, myRightIndex, myEntryValue, false);
	mySlLine = line(myLastSignalIndex, mySlValue, myRightIndex, mySlValue, false);
	myTp1Line = line(myLastSignalIndex, myTp1Value, myRightIndex, myTp1Value, false);
	myTp2Line = line(myLastSignalIndex, myTp2Value, myRightIndex, myTp2Value, false);
	myTp3Line = line(myLastSignalIndex, myTp3Value, myRightIndex, myTp3Value, false);
}

const myEntryLinePainted = paint(myEntryLine, { name: 'Entry', color: 'blue', thickness: 2 });
const mySlLinePainted = paint(mySlLine, { name: 'Stop Loss', color: 'red', thickness: 2 });
const myTp1LinePainted = paint(myTp1Line, { name: 'Take Profit 1', color: 'green', thickness: 2 });
const myTp2LinePainted = paint(myTp2Line, { name: 'Take Profit 2', color: 'green', thickness: 2 });
const myTp3LinePainted = paint(myTp3Line, { name: 'Take Profit 3', color: 'green', thickness: 2 });

if (myLastSignalIndex >= 0) {
	paint_label_at_line(myEntryLinePainted, myLastSignalIndex, 'Entry', { color: 'white', background_color: 'blue' });
	paint_label_at_line(mySlLinePainted, myLastSignalIndex, 'Stop Loss', { color: 'white', background_color: 'red' });
	paint_label_at_line(myTp1LinePainted, myLastSignalIndex, 'Take Profit 1', { color: 'white', background_color: 'green' });
	paint_label_at_line(myTp2LinePainted, myLastSignalIndex, 'Take Profit 2', { color: 'white', background_color: 'green' });
	paint_label_at_line(myTp3LinePainted, myLastSignalIndex, 'Take Profit 3', { color: 'white', background_color: 'green' });
}

// ===== SIGNALS FOR SCANNERS / ALERTS / STRATEGIES =====
// Registered once each, with unique names, to avoid the
// "signal already exists" duplicate registration error.
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');