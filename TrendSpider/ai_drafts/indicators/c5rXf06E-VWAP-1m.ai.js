describe_indicator('VWAP 1m', 'price');

// This indicator reproduces a Pine Script which computes an
// intrabar VWAP using 1 minute data, landed onto the current
// chart's bars. On a 1m (or lower) chart it simply uses OHLC4.
// On higher timeframes, it fetches 1m history and aggregates
// volume-weighted OHLC4 for all 1m bars contained inside each
// chart bar's time range. If no 1m bars are found for a given
// chart bar (data gap), the previous value is carried forward,
// matching the Pine `var float` behavior.

// Resolution of "1" or lower is treated as "already 1 minute or less"
const myIsOneMinuteOrLower = !isNaN(current.resolution) && Number(current.resolution) <= 1;

const myOhlc4 = ohlc4;
const myBarVwap = series_of(null);

if (myIsOneMinuteOrLower) {
	for (let myIndex = 0; myIndex < myOhlc4.length; myIndex += 1) {
		myBarVwap[myIndex] = myOhlc4[myIndex];
	}
}
else {
	const myOneMinData = await request.history(current.ticker, '1');
	assert(!myOneMinData.error, `Error fetching 1m data: "${myOneMinData.error}"`);

	const myOneMinOhlc4 = myOneMinData.open.map((_o, _i) => (myOneMinData.open[_i] + myOneMinData.high[_i] + myOneMinData.low[_i] + myOneMinData.close[_i]) / 4);
	const myOneMinTime = myOneMinData.time;
	const myOneMinVolume = myOneMinData.volume;

	let myPointer = 0;
	let myLastValue = null;

	for (let myBarIndex = 0; myBarIndex < time.length; myBarIndex += 1) {
		const myBarStart = time[myBarIndex];
		const myBarEnd = (myBarIndex + 1 < time.length) ? time[myBarIndex + 1] : Infinity;

		let myPvSum = 0;
		let myVSum = 0;

		while (myPointer < myOneMinTime.length && myOneMinTime[myPointer] < myBarStart) {
			myPointer += 1;
		}

		let myScanPointer = myPointer;
		while (myScanPointer < myOneMinTime.length && myOneMinTime[myScanPointer] < myBarEnd) {
			myPvSum += myOneMinOhlc4[myScanPointer] * myOneMinVolume[myScanPointer];
			myVSum += myOneMinVolume[myScanPointer];
			myScanPointer += 1;
		}

		if (myVSum > 0) {
			myLastValue = myPvSum / myVSum;
		}

		myBarVwap[myBarIndex] = myLastValue;
		myPointer = myScanPointer;
	}
}

const myVwapLinePainted = paint(myBarVwap, { name: 'VWAP1m', color: '#9F10E6', thickness: 3, style: 'line', forceUsePriceAxis: true });

// Signals for scanners, alerts and strategies: price crossing above/below the VWAP
const myCloseAboveVwap = for_every(close, myBarVwap, (_c, _v) => _v !== null && _c > _v);
const myCloseBelowVwap = for_every(close, myBarVwap, (_c, _v) => _v !== null && _c < _v);
const myCrossAbove = for_every(close, myBarVwap, (_c, _v, _prev, _i) => {
	if (_v === null || _i === 0 || myBarVwap[_i - 1] === null) return false;
	return close[_i - 1] <= myBarVwap[_i - 1] && _c > _v;
});
const myCrossBelow = for_every(close, myBarVwap, (_c, _v, _prev, _i) => {
	if (_v === null || _i === 0 || myBarVwap[_i - 1] === null) return false;
	return close[_i - 1] >= myBarVwap[_i - 1] && _c < _v;
});

register_signal(myCloseAboveVwap, 'Close Above VWAP1m');
register_signal(myCloseBelowVwap, 'Close Below VWAP1m');
register_signal(myCrossAbove, 'Cross Above VWAP1m');
register_signal(myCrossBelow, 'Cross Below VWAP1m');