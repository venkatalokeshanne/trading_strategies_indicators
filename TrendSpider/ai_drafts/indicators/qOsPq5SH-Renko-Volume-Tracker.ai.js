// EXPERIMENTAL / APPROXIMATE PORT.
// TrendSpider's Custom JS API has no equivalent of Pine's
// ticker.renko() / request.security() against a synthetic Renko
// instrument. There is no way to request a true Renko-constructed
// chart (open/high/low/close of bricks) from this engine.
// This indicator therefore RECONSTRUCTS a close-based Renko series
// manually, bar by bar, using the same box-size logic (ATR or a
// fixed/"Traditional" box size), and reproduces the brick/trend/
// chunk-volume logic on top of it. Because the underlying Renko
// series is approximated (one potential brick per bar, built off
// `close` only, not off true OHLC renko bricks), bar-for-bar values
// may differ slightly from the original Pine script, especially on
// fast multi-brick moves within one real-time bar.
describe_indicator('Renko Volume Tracker', 'price');

const myChunkTab = input.tab('Renko Volume Chunking');
const myParamType = myChunkTab.select('Box Size Method', 'ATR', ['ATR', 'Traditional']);
const myRenkoAtrLength = myChunkTab.number('Renko ATR Period', 14, { min: 1, max: 200 });
const myTraditionalBoxSize = myChunkTab.number('Traditional Box Size', 1.0, { min: 0.0001, max: 100000 });
const myRow = myChunkTab.row();
const myNBricks = myRow.number('Chunk Window (N Bricks)', 3, { min: 1, max: 50 });
const myColorRow = myChunkTab.row();
const myPivotColorUp = myColorRow.color('Pivot Color (Up Trend)', 'teal');
const myPivotColorDn = myColorRow.color('Pivot Color (Down Trend)', 'purple');

const myAtrSeries = atr(high, low, close, myRenkoAtrLength);
const myLength = close.length;

// Reconstruct an approximate Renko close series, bar by bar.
// Note: using Array(n).fill(...) instead of "new Array(n).fill(...)"
// since the "new" keyword is prohibited by the execution engine.
// Calling Array() as a plain function (no "new") behaves identically.
const myRenkoClose = Array(myLength).fill(null);
const myRenkoTrend = Array(myLength).fill(1);
const myNewBrick = Array(myLength).fill(false);

let myCurrentRenkoClose = close.length > 0 ? close[0] : 0;
let myCurrentTrend = 1;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myBoxSize = myParamType === 'ATR' ? (myAtrSeries[myIndex] || myTraditionalBoxSize) : myTraditionalBoxSize;
	const myDiff = close[myIndex] - myCurrentRenkoClose;

	if (myIndex === 0) {
		myRenkoClose[myIndex] = myCurrentRenkoClose;
		myRenkoTrend[myIndex] = myCurrentTrend;
		myNewBrick[myIndex] = false;
		continue;
	}

	if (myBoxSize > 0 && Math.abs(myDiff) >= myBoxSize) {
		myCurrentTrend = myDiff > 0 ? 1 : -1;
		myCurrentRenkoClose = myCurrentRenkoClose + myCurrentTrend * myBoxSize;
		myNewBrick[myIndex] = true;
	}
	else {
		myNewBrick[myIndex] = false;
	}

	myRenkoClose[myIndex] = myCurrentRenkoClose;
	myRenkoTrend[myIndex] = myCurrentTrend;
}

// Core volume chunking logic, mirroring the Pine script state machine.
const myUpPivot = Array(myLength).fill(null);
const myDownPivot = Array(myLength).fill(null);
const myPivotSignal = Array(myLength).fill(false);
const myUpPivotSignal = Array(myLength).fill(false);
const myDownPivotSignal = Array(myLength).fill(false);

let myBrickCount = 0;
let myChunkMaxVol = 0.0;
let myChunkMaxBar = null;
let myChunkMaxPivot = null;
let myChunkMaxTrend = null;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myCurrentVol = volume[myIndex] || 0;

	if (myCurrentVol > myChunkMaxVol || myChunkMaxVol === 0) {
		myChunkMaxVol = myCurrentVol;
		myChunkMaxBar = myIndex;
		myChunkMaxPivot = myRenkoTrend[myIndex] === 1 ? low[myIndex] : high[myIndex];
		myChunkMaxTrend = myRenkoTrend[myIndex];
	}

	if (myNewBrick[myIndex]) {
		myBrickCount += 1;

		if (myBrickCount >= myNBricks) {
			if (myChunkMaxBar !== null) {
				if (myChunkMaxTrend === 1) {
					myUpPivot[myChunkMaxBar] = myChunkMaxPivot;
					myUpPivotSignal[myChunkMaxBar] = true;
				}
				else {
					myDownPivot[myChunkMaxBar] = myChunkMaxPivot;
					myDownPivotSignal[myChunkMaxBar] = true;
				}
				myPivotSignal[myChunkMaxBar] = true;
			}

			myBrickCount = 0;
			myChunkMaxVol = 0.0;
			myChunkMaxBar = null;
			myChunkMaxPivot = null;
			myChunkMaxTrend = null;
		}
	}
}

paint(myUpPivot, { style: 'labels_below', color: myPivotColorUp, name: 'TopVolUp' });
paint(myDownPivot, { style: 'labels_above', color: myPivotColorDn, name: 'TopVolDown' });

register_signal(myPivotSignal, 'Top Volume Pivot');
register_signal(myUpPivotSignal, 'Top Volume Pivot Up Trend');
register_signal(myDownPivotSignal, 'Top Volume Pivot Down Trend');