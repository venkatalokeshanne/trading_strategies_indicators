describe_indicator('ZC Footprint Delta', 'lower');

// NOTE: TrendSpider Custom JS API has no strategy/backtesting engine
// (no strategy.entry/strategy.exit, no position tracking, no TP/SL
// order simulation). This script reproduces the Pine Script's
// footprint Delta calculation and the Long/Short entry CONDITIONS
// as an indicator with signals, labels and a plotted Delta line.
// The TP/SL exit logic from the original strategy can not be
// reproduced here; use TrendSpider's Strategy Tester (visual
// scripting) with these signals instead.

const myThreshold = input.number('Delta Threshold', 500, { min: 0 });
const myStartYear = input.number('Start Year', 2026, { min: 1970, max: 2100 });
const myStartMonth = input.number('Start Month', 1, { min: 1, max: 12 });
const myStartDay = input.number('Start Day', 1, { min: 1, max: 31 });
const myCnum = input.number('Bins Count', 10, { min: 2, max: 100 });

// start_date equivalent, assumed UTC midnight for the given Y/M/D
const myStartDateMs = Date.UTC(myStartYear, myStartMonth - 1, myStartDay, 0, 0, 0);
const myStartDateSeconds = myStartDateMs / 1000;

// Fetch 1 minute data to build the footprint bins, mirroring
// request.security_lower_tf(syminfo.tickerid, "1", ...) from Pine.
const myLowerTfData = await request.history(current.ticker, '1');
assert(!myLowerTfData.error, 'Error fetching 1 min data: ' + myLowerTfData.error);

// Precompute signed volume for every 1 min candle (close>open -> +volume, close<open -> -volume, else 0)
const myLowerSignedVolume = myLowerTfData.close.map((_c, _i) => {
	if (myLowerTfData.close[_i] > myLowerTfData.open[_i]) return myLowerTfData.volume[_i];
	if (myLowerTfData.close[_i] < myLowerTfData.open[_i]) return -myLowerTfData.volume[_i];
	return 0.0;
});

const myTotalDelta = series_of(null);

// For every main candle, bucket the lower timeframe candles whose
// time falls within [time[i], time[i+1]) (or [time[i], now] for the last candle)
let myLowerIndexCursor = 0;

for (let myCandleIndex = 0; myCandleIndex < time.length; myCandleIndex += 1) {
	const myFromTime = time[myCandleIndex];
	const myToTime = myCandleIndex + 1 < time.length ? time[myCandleIndex + 1] : current.now + 1;

	// advance cursor to the first lower tf candle at/after myFromTime
	while (myLowerIndexCursor < myLowerTfData.time.length && myLowerTfData.time[myLowerIndexCursor] < myFromTime) {
		myLowerIndexCursor += 1;
	}

	const myBucketCloses = [];
	const myBucketOpens = [];
	const myBucketSignedVol = [];

	let myScanIndex = myLowerIndexCursor;
	while (myScanIndex < myLowerTfData.time.length && myLowerTfData.time[myScanIndex] < myToTime) {
		myBucketCloses.push(myLowerTfData.close[myScanIndex]);
		myBucketOpens.push(myLowerTfData.open[myScanIndex]);
		myBucketSignedVol.push(myLowerSignedVolume[myScanIndex]);
		myScanIndex += 1;
	}

	if (myBucketCloses.length > 0) {
		// main_high/main_low initialized like Pine: main_high = low, main_low = high (swapped on purpose)
		let myMainHigh = low[myCandleIndex];
		let myMainLow = high[myCandleIndex];

		for (let myI = 0; myI < myBucketCloses.length; myI += 1) {
			const myC = myBucketCloses[myI];
			const myO = myBucketOpens[myI];
			myMainHigh = Math.max(myMainHigh, Math.max(myC, myO));
			myMainLow = Math.min(myMainLow, Math.min(myC, myO));
		}

		const myPriceRange = myMainHigh - myMainLow;
		const myBinSize = myPriceRange / myCnum;

		const myBins = Array(myCnum).fill(0.0);

		if (myBinSize > 0) {
			for (let myI = 0; myI < myBucketCloses.length; myI += 1) {
				const myC = myBucketCloses[myI];
				const myO = myBucketOpens[myI];

				const myLowerBin = Math.min(Math.floor((Math.min(myC, myO) - myMainLow) / myBinSize), myCnum - 1);
				const myHigherBin = Math.min(Math.floor((Math.max(myC, myO) - myMainLow) / myBinSize), myCnum - 1);

				const myWidth = Math.max(Math.abs(myLowerBin - myHigherBin), 1);
				const myUnitVolume = myBucketSignedVol[myI] / myWidth;

				const myStartBin = Math.max(Math.min(myHigherBin, myLowerBin), 0);
				const myEndBin = Math.min(Math.max(myHigherBin, myLowerBin), myCnum - 1);

				for (let myJ = myStartBin; myJ <= myEndBin; myJ += 1) {
					myBins[myJ] += myUnitVolume;
				}
			}
		}

		myTotalDelta[myCandleIndex] = myBins.reduce((_myAcc, _myVal) => _myAcc + _myVal, 0.0);
	}
	else {
		myTotalDelta[myCandleIndex] = close[myCandleIndex] > open[myCandleIndex] ? volume[myCandleIndex] : -volume[myCandleIndex];
	}
}

const myInDateRange = for_every(time, _t => _t >= myStartDateSeconds);

// position_size == 0 can not be tracked without a strategy engine;
// we approximate the "flat" requirement by just evaluating the raw
// delta threshold crossing condition every bar (no position state).
const myLongCondition = for_every(myTotalDelta, myInDateRange, (_d, _r) => _d !== null && _r && _d > myThreshold);
const myShortCondition = for_every(myTotalDelta, myInDateRange, (_d, _r) => _d !== null && _r && _d < -myThreshold);

paint(myTotalDelta, { name: 'Delta', color: '#ffd54f', style: 'line' });

const myBuyMarks = for_every(myLongCondition, _l => _l ? 1 : null);
const mySellMarks = for_every(myShortCondition, _s => _s ? 1 : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: '#26a69a' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: '#ef5350' });

register_signal(myLongCondition, 'Long Condition');
register_signal(myShortCondition, 'Short Condition');