describe_indicator('VWAP 5m', 'price');

// This script reproduces a Pine Script v6 indicator which plots a
// "bar VWAP" built from 5 minute data. On charts whose resolution is
// already 5 minutes or lower, it simply uses the bar's OHLC4 value
// (this matches the Pine logic exactly, which skips any lower
// time frame request in that case). On higher time frames, it
// requests 5 minute history and computes a volume weighted average
// of OHLC4 over all the 5 minute bars contained inside each chart
// candle, replicating the Pine `request.security_lower_tf` loop.
// If a chart candle has no underlying 5m bars (e.g. a data gap),
// the previous value is carried forward, exactly like Pine's `var`.

const myResolutionNumber = Number(current.resolution);
const myIsLowTimeframe = !isNaN(myResolutionNumber) && myResolutionNumber <= 5;

let myBarVwap = series_of(null);

if (myIsLowTimeframe) {
	// Chart is already 5m or lower: nothing smaller to pull, use this bar's OHLC4
	myBarVwap = ohlc4;
}
else {
	const my5mData = await request.history(current.ticker, '5');
	assert(!my5mData.error, `Error fetching 5m data: "${my5mData.error}"`);

	const myLtfPrice = my5mData.close.map((_c, _i) => (my5mData.open[_i] + my5mData.high[_i] + my5mData.low[_i] + my5mData.close[_i]) / 4);
	const myLtfVolume = my5mData.volume;
	const myLtfTime = my5mData.time;

	let myPointer = 0;
	let myLastValue = null;

	for (let myCandleIndex = 0; myCandleIndex < time.length; myCandleIndex += 1) {
		const myCandleStart = time[myCandleIndex];

		// figure out the boundary (start of the next chart candle)
		let myCandleEnd;
		if (myCandleIndex + 1 < time.length) {
			myCandleEnd = time[myCandleIndex + 1];
		}
		else if (myCandleIndex > 0) {
			myCandleEnd = myCandleStart + (time[myCandleIndex] - time[myCandleIndex - 1]);
		}
		else {
			myCandleEnd = myCandleStart + 86400;
		}

		// advance pointer to the first ltf bar belonging to this candle
		while (myPointer < myLtfTime.length && myLtfTime[myPointer] < myCandleStart) {
			myPointer += 1;
		}

		let myPvSum = 0;
		let myVSum = 0;
		let myScanPointer = myPointer;

		while (myScanPointer < myLtfTime.length && myLtfTime[myScanPointer] < myCandleEnd) {
			myPvSum += myLtfPrice[myScanPointer] * myLtfVolume[myScanPointer];
			myVSum += myLtfVolume[myScanPointer];
			myScanPointer += 1;
		}

		if (myVSum > 0) {
			myLastValue = myPvSum / myVSum;
		}

		myBarVwap[myCandleIndex] = myLastValue;
		myPointer = myScanPointer > myPointer ? myScanPointer : myPointer;
	}
}

const myVwapPainted = paint(myBarVwap, { name: 'VWAP 5m', color: '#9F10E6', thickness: 3, style: 'line' });

// signals for scanners, alerts and strategy testing
const myCloseAboveVwap = for_every(close, myBarVwap, (_c, _v) => _v != null && _c > _v);
const myCloseBelowVwap = for_every(close, myBarVwap, (_c, _v) => _v != null && _c < _v);
const myCrossAboveVwap = for_every(close, myBarVwap, (_c, _v, _prev, _i) => _v != null && myBarVwap[_i - 1] != null && _c > _v && close[_i - 1] <= myBarVwap[_i - 1]);
const myCrossBelowVwap = for_every(close, myBarVwap, (_c, _v, _prev, _i) => _v != null && myBarVwap[_i - 1] != null && _c < _v && close[_i - 1] >= myBarVwap[_i - 1]);

register_signal(myCloseAboveVwap, 'Close Above VWAP 5m');
register_signal(myCloseBelowVwap, 'Close Below VWAP 5m');
register_signal(myCrossAboveVwap, 'Cross Above VWAP 5m');
register_signal(myCrossBelowVwap, 'Cross Below VWAP 5m');