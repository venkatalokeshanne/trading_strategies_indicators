describe_indicator('Closing Pattern', 'price');

// NOTE: this is a conversion of a TradingView Pine Script into TrendSpider
// Custom JS. Pine's request.security() with lookahead_on and its table.cell()
// have no 1:1 equivalent here, so this is an approximation (see comments and
// the flagged notes below).

const myDirTab = input.tab('Direction Table');
const myLookbackBars = myDirTab.number('Direction lookback (bars)', 50, { min: 5, max: 500 });

const myAlertTab = input.tab('Alert');
const myAlertTf = myAlertTab.select('Alert timeframe', '240', constants.time_frames);
const myDirInput = myAlertTab.select('Alert direction', 'Both', ['Below', 'Above', 'Both']);

const myAlertBelowOn = myDirInput === 'Below' || myDirInput === 'Both';
const myAlertAboveOn = myDirInput === 'Above' || myDirInput === 'Both';

// ================= Direction scan helper =================
// Replicates f_scanDirection(): walking backwards up to n bars, looking for
// the first bar whose close breaks the high/low of 2 bars prior.
function myScanDirectionSeries(myCloseArr, myHighArr, myLowArr, myN) {
	const myResult = [];
	for (let myJ = 0; myJ < myCloseArr.length; myJ += 1) {
		let myDir = 0;
		for (let myI = 0; myI < myN; myI += 1) {
			const myCcIndex = myJ - (myI + 1);
			const myHlIndex = myJ - (myI + 2);
			if (myCcIndex < 0 || myHlIndex < 0) {
				break;
			}
			const myCc = myCloseArr[myCcIndex];
			const myHh = myHighArr[myHlIndex];
			const myLl = myLowArr[myHlIndex];
			if (myCc != null && myHh != null && myCc > myHh) {
				myDir = 1;
				break;
			}
			if (myCc != null && myLl != null && myCc < myLl) {
				myDir = -1;
				break;
			}
		}
		myResult.push(myDir);
	}
	return myResult;
}

const [myDataD1, myData12H, myDataAlertTf] = await Promise.all([
	request.history(current.ticker, 'D'),
	request.history(current.ticker, '720'),
	request.history(current.ticker, myAlertTf)
]);

assert(!myDataD1.error, 'Error fetching D1 data: ' + myDataD1.error);
assert(!myData12H.error, 'Error fetching 12H data: ' + myData12H.error);
assert(!myDataAlertTf.error, 'Error fetching alert timeframe data: ' + myDataAlertTf.error);

const myDirD1Series = myScanDirectionSeries(myDataD1.close, myDataD1.high, myDataD1.low, myLookbackBars);
const myDir12HSeries = myScanDirectionSeries(myData12H.close, myData12H.high, myData12H.low, myLookbackBars);

const myLastDirD1 = myDirD1Series.length ? myDirD1Series[myDirD1Series.length - 1] : 0;
const myLastDir12H = myDir12HSeries.length ? myDir12HSeries[myDir12HSeries.length - 1] : 0;

function myColorOfDirection(myDir) {
	if (myDir === 1) {
		return '#4CAF4F';
	}
	if (myDir === -1) {
		return '#F44336';
	}
	return 'rgba(255,255,255,0.6)';
}

function myTextOfDirection(myDir) {
	if (myDir === 1) {
		return 'Long';
	}
	if (myDir === -1) {
		return 'Short';
	}
	return 'Neutral';
}

// Displays the Direction table (replaces Pine's table.new / table.cell)
paint_overlay('DirectionTable', { position: 'top_right' }, {
	rows: [{
		cells: [
			{ text: 'D1 Direction', color: 'var(--text-color)' },
			{ text: myTextOfDirection(myLastDirD1), color: myColorOfDirection(myLastDirD1) }
		]
	}, {
		cells: [
			{ text: '12H Direction', color: 'var(--text-color)' },
			{ text: myTextOfDirection(myLastDir12H), color: myColorOfDirection(myLastDir12H) }
		]
	}]
});

// ================= Discrete alert signals =================
// Approximation: "sameTf" compares current.resolution against the alert
// timeframe string directly (Pine compares timeframe.in_seconds()).
const mySameTf = current.resolution === myAlertTf;

// Same-timeframe case: use the current chart's own series directly.
const mySignalBelowSame = for_every(close, shift(low, 1), (myC, myPrevLow) => myAlertBelowOn && myPrevLow != null && myC < myPrevLow);
const mySignalAboveSame = for_every(close, shift(high, 1), (myC, myPrevHigh) => myAlertAboveOn && myPrevHigh != null && myC > myPrevHigh);

// Multi-timeframe case: compute the signal on the fetched htf data, then
// land each htf bar's signal flag onto the matching current-chart candle.
const myHtfClosePrev = shift(myDataAlertTf.close, 1);
const myHtfHighPrev2 = shift(myDataAlertTf.high, 2);
const myHtfLowPrev2 = shift(myDataAlertTf.low, 2);

const myHtfSignalBelow = myDataAlertTf.time.map((myT, myI) => (
	myAlertBelowOn && myHtfClosePrev[myI] != null && myHtfLowPrev2[myI] != null && myHtfClosePrev[myI] < myHtfLowPrev2[myI] ? 1 : 0
));
const myHtfSignalAbove = myDataAlertTf.time.map((myT, myI) => (
	myAlertAboveOn && myHtfClosePrev[myI] != null && myHtfHighPrev2[myI] != null && myHtfClosePrev[myI] > myHtfHighPrev2[myI] ? 1 : 0
));

const myLandedBelow = land_points_onto_series(myDataAlertTf.time, myHtfSignalBelow, time, 'ge');
const myLandedAbove = land_points_onto_series(myDataAlertTf.time, myHtfSignalAbove, time, 'ge');

const mySignalBelowMtf = for_every(myLandedBelow, myV => myV === 1);
const mySignalAboveMtf = for_every(myLandedAbove, myV => myV === 1);

const mySignalBelow = mySameTf ? mySignalBelowSame : mySignalBelowMtf;
const mySignalAbove = mySameTf ? mySignalAboveSame : mySignalAboveMtf;

const myBelowMarks = for_every(mySignalBelow, myFlag => myFlag ? constants.icons.triangle_down : null);
const myAboveMarks = for_every(mySignalAbove, myFlag => myFlag ? constants.icons.triangle_up : null);

paint(myBelowMarks, { style: 'labels_below', color: 'red', name: 'CloseBelowPreviousRange' });
paint(myAboveMarks, { style: 'labels_above', color: 'green', name: 'CloseAbovePreviousRange' });

register_signal(mySignalBelow, 'Close Below Previous Range');
register_signal(mySignalAbove, 'Close Above Previous Range');