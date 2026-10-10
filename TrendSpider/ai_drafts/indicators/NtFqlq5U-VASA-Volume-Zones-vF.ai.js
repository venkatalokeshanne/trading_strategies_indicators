describe_indicator('VASA Volume Zones (Profile lite)', 'price');

// NOTE: TrendSpider Custom JS has no box-drawing primitive, so the
// Pine Script's volume histogram (array of box.new calls) can not be
// reproduced. This port keeps the math identical (same POC / VAH / VAL
// values, same session/lookback logic) but renders POC, VAH and VAL as
// horizontal segments instead of a shaded histogram.

const myProfileTab = input.tab('Profile');
const myAnchorMode = myProfileTab.select('Anchor', 'Session (day)', ['Session (day)', 'Lookback bars']);
const myLookback = myProfileTab.number('Lookback bars (Lookback mode)', 240, { min: 20, max: 5000 });
const myBins = myProfileTab.number('Price rows (bins)', 24, { min: 5, max: 100 });
const myVaPct = myProfileTab.number('Value area percent', 70, { min: 50, max: 95 });

const myStyleTab = input.tab('Style');
const myHistWidth = myStyleTab.number('Line width (bars)', 40, { min: 5, max: 200 });

const myCandleCount = close.length;

// ---------- Compute "session bars" count for every candle (ta.change(time("1D"))) ----------
const mySessBars = series_of(0);
for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myCurrentDay = time_of(time[myIndex]).dayOfYear + '_' + time_of(time[myIndex]).year;
	const myPrevDay = myIndex > 0 ? (time_of(time[myIndex - 1]).dayOfYear + '_' + time_of(time[myIndex - 1]).year) : null;
	const myIsNewDay = myCurrentDay !== myPrevDay;
	mySessBars[myIndex] = myIsNewDay ? 1 : mySessBars[myIndex - 1] + 1;
}

const myLastIndex = myCandleCount - 1;
assert(myLastIndex >= 0, 'No candles available');

const myEffLen = myAnchorMode === 'Session (day)' ? Math.min(mySessBars[myLastIndex], 5000) : myLookback;

let myPocPrice = null;
let myVah = null;
let myVal = null;

if (myEffLen > 1) {
	// pass 1 - window hi/lo from closed bars (i = 0 .. effLen-1, counting back from last)
	let myHi = high[myLastIndex];
	let myLo = low[myLastIndex];

	for (let myI = 0; myI < myEffLen; myI += 1) {
		const myCandle = myLastIndex - myI;
		if (myCandle < 0) {
			break;
		}
		myHi = Math.max(myHi, high[myCandle]);
		myLo = Math.min(myLo, low[myCandle]);
	}

	const myRange = myHi - myLo;

	if (myRange > 0) {
		const myBinSize = myRange / myBins;
		const myVol = Array(myBins).fill(0);

		// pass 2 - accumulate volume into price bins (typical price per bar)
		for (let myI = 0; myI < myEffLen; myI += 1) {
			const myCandle = myLastIndex - myI;
			if (myCandle < 0) {
				break;
			}
			const myTypicalPrice = (high[myCandle] + low[myCandle] + close[myCandle]) / 3.0;
			let myBinIndex = Math.floor((myTypicalPrice - myLo) / myBinSize);
			myBinIndex = Math.max(0, Math.min(myBins - 1, myBinIndex));
			myVol[myBinIndex] += volume[myCandle];
		}

		// POC + totals
		let myPocBin = 0;
		let myMaxV = 0.0;
		let myTotal = 0.0;

		for (let myB = 0; myB < myBins; myB += 1) {
			const myV = myVol[myB];
			myTotal += myV;
			if (myV > myMaxV) {
				myMaxV = myV;
				myPocBin = myB;
			}
		}

		// expand value area outward from POC until it covers vaPct of volume
		let myLowB = myPocBin;
		let myHighB = myPocBin;
		let myAcc = myVol[myPocBin];
		const myTarget = myTotal * myVaPct / 100.0;

		while (myAcc < myTarget && (myLowB > 0 || myHighB < myBins - 1)) {
			const myVBelow = myLowB > 0 ? myVol[myLowB - 1] : -1.0;
			const myVAbove = myHighB < myBins - 1 ? myVol[myHighB + 1] : -1.0;

			if (myVAbove >= myVBelow) {
				myHighB += 1;
				myAcc += myVol[myHighB];
			}
			else {
				myLowB -= 1;
				myAcc += myVol[myLowB];
			}
		}

		myPocPrice = myLo + (myPocBin + 0.5) * myBinSize;
		myVah = myLo + (myHighB + 1) * myBinSize;
		myVal = myLo + myLowB * myBinSize;
	}
}

const myFromIndex = Math.max(0, myLastIndex - myHistWidth);

const myPocLine = myPocPrice !== null ? horizontal_line(myPocPrice, myFromIndex, myLastIndex) : series_of(null);
const myVahLine = myVah !== null ? horizontal_line(myVah, myFromIndex, myLastIndex) : series_of(null);
const myValLine = myVal !== null ? horizontal_line(myVal, myFromIndex, myLastIndex) : series_of(null);

paint(myPocLine, { name: 'POC', color: '#f59e0b', thickness: 2 });
paint(myVahLine, { name: 'VAH', color: '#64748b', style: 'dotted' });
paint(myValLine, { name: 'VAL', color: '#64748b', style: 'dotted' });

// ---------- Signals for scanners/alerts/strategies ----------
const myCloseAbovePoc = myPocPrice !== null ? for_every(close, _c => _c > myPocPrice) : series_of(false);
const myCloseBelowPoc = myPocPrice !== null ? for_every(close, _c => _c < myPocPrice) : series_of(false);
const myCloseAboveVah = myVah !== null ? for_every(close, _c => _c > myVah) : series_of(false);
const myCloseBelowVal = myVal !== null ? for_every(close, _c => _c < myVal) : series_of(false);

register_signal(myCloseAbovePoc, 'Close Above POC');
register_signal(myCloseBelowPoc, 'Close Below POC');
register_signal(myCloseAboveVah, 'Close Above VAH');
register_signal(myCloseBelowVal, 'Close Below VAL');