describe_indicator('Range MTF BG', 'price');

// ───────────────────────────── Inputs ─────────────────────────────
const myDisplayGroup = input.group('Display');
const myUpColor = input.color('Up shade', 'rgba(0,255,0,0.18)');
const myDnColor = input.color('Down shade', 'rgba(255,0,0,0.18)');

const myTfGroup = input.tab('Timeframes');
const myRow1 = myTfGroup.row();
const myEn1 = myRow1.boolean('Use TF 1', true);
const myTf1 = myRow1.select('TF 1', '5', constants.time_frames);
const myRow2 = myTfGroup.row();
const myEn2 = myRow2.boolean('Use TF 2', true);
const myTf2 = myRow2.select('TF 2', '15', constants.time_frames);
const myRow3 = myTfGroup.row();
const myEn3 = myRow3.boolean('Use TF 3', true);
const myTf3 = myRow3.select('TF 3', '30', constants.time_frames);
const myRow4 = myTfGroup.row();
const myEn4 = myRow4.boolean('Use TF 4', true);
const myTf4 = myRow4.select('TF 4', '60', constants.time_frames);

// ───────────────────────── Core state machine ──────────────────────
// Reproduces the Pine "rangeState()" logic: the first candle defines a
// range (high/low). The range survives while closes stay inside it.
// The first close outside the range creates a new range and sets a
// direction: 1 = broke up, -1 = broke down. The very first range has
// direction 0 (neutral), which can never satisfy "all up" or "all down".
function myComputeDir(myHighSeries, myLowSeries, myCloseSeries) {
	const myDirOut = series_of(0);
	let myRangeHigh = myHighSeries[0];
	let myRangeLow = myLowSeries[0];
	let myCurrentDir = 0;

	myDirOut[0] = 0;

	for (let myIndex = 1; myIndex < myCloseSeries.length; myIndex += 1) {
		if (myCloseSeries[myIndex] > myRangeHigh || myCloseSeries[myIndex] < myRangeLow) {
			myCurrentDir = myCloseSeries[myIndex] > myRangeHigh ? 1 : -1;
			myRangeHigh = myHighSeries[myIndex];
			myRangeLow = myLowSeries[myIndex];
		}
		myDirOut[myIndex] = myCurrentDir;
	}

	return myDirOut;
}

// ──────────────────── Chart (native) timeframe direction ───────────
// Pine holds the last confirmed value on the still-forming bar
// (barstate.isconfirmed ? nd : nd[1]). We approximate that by lagging
// only the very last (currently forming) candle by one bar.
const myChartDirRaw = myComputeDir(high, low, close);
const myChartDirFinal = myChartDirRaw.map((myValue, myIndex) => {
	if (myIndex === myChartDirRaw.length - 1) {
		return myChartDirRaw[myIndex - 1] ?? 0;
	}
	return myValue;
});

// ─────────────────── Other timeframe directions (MTF) ──────────────
const mySlotDefs = [
	{ enabled: myEn1, tf: myTf1 },
	{ enabled: myEn2, tf: myTf2 },
	{ enabled: myEn3, tf: myTf3 },
	{ enabled: myEn4, tf: myTf4 }
];

const myNonChartSlots = mySlotDefs.filter(mySlot => mySlot.tf !== current.resolution);

const myHistoryResults = await Promise.all(
	myNonChartSlots.map(mySlot => request.history(current.ticker, mySlot.tf))
);

myHistoryResults.forEach((myHistoryData, myIndex) => {
	assert(!myHistoryData.error, `Error fetching data for TF ${myNonChartSlots[myIndex].tf}: ${myHistoryData.error}`);
});

// Build a landed (and lagged by one bar, mirroring Pine's `d[1]` closed-bar
// read inside request.security) direction series for every non-chart slot.
const myLandedDirsBySlot = {};
myNonChartSlots.forEach((mySlot, myIndex) => {
	const myHistoryData = myHistoryResults[myIndex];
	const myRawDir = myComputeDir(myHistoryData.high, myHistoryData.low, myHistoryData.close);
	const myLaggedDir = shift(myRawDir, 1);
	const myLanded = land_points_onto_series(myHistoryData.time, myLaggedDir, time, 'le');
	myLandedDirsBySlot[mySlot.tf] = interpolate_sparse_series(myLanded, 'constant');
});

function myDirForSlot(mySlot) {
	if (mySlot.tf === current.resolution) {
		return myChartDirFinal;
	}
	return myLandedDirsBySlot[mySlot.tf];
}

const myDir1 = myDirForSlot(mySlotDefs[0]);
const myDir2 = myDirForSlot(mySlotDefs[1]);
const myDir3 = myDirForSlot(mySlotDefs[2]);
const myDir4 = myDirForSlot(mySlotDefs[3]);

// ─────────────────────────── Alignment logic ───────────────────────
const myAnyOn = myEn1 || myEn2 || myEn3 || myEn4;

const myAllUp = for_every(myDir1, myDir2, myDir3, myDir4, (_d1, _d2, _d3, _d4) =>
	myAnyOn &&
	(!myEn1 || _d1 === 1) &&
	(!myEn2 || _d2 === 1) &&
	(!myEn3 || _d3 === 1) &&
	(!myEn4 || _d4 === 1)
);

const myAllDn = for_every(myDir1, myDir2, myDir3, myDir4, (_d1, _d2, _d3, _d4) =>
	myAnyOn &&
	(!myEn1 || _d1 === -1) &&
	(!myEn2 || _d2 === -1) &&
	(!myEn3 || _d3 === -1) &&
	(!myEn4 || _d4 === -1)
);

// The Custom JS API has no "bgcolor" equivalent; we approximate the Pine
// background shade by coloring the candles instead.
const myCandleColors = for_every(myAllUp, myAllDn, (_up, _dn) => _up ? myUpColor : (_dn ? myDnColor : null));
color_candles(myCandleColors);

// ─────────────────────────────── Signals ────────────────────────────
const myAlignedUpSignal = for_every(myAllUp, (_up, _prev, _index) => _up && !myAllUp[_index - 1]);
const myAlignedDnSignal = for_every(myAllDn, (_dn, _prev, _index) => _dn && !myAllDn[_index - 1]);

register_signal(myAllUp, 'All Timeframes Up');
register_signal(myAllDn, 'All Timeframes Down');
register_signal(myAlignedUpSignal, 'Aligned Up Just Now');
register_signal(myAlignedDnSignal, 'Aligned Down Just Now');