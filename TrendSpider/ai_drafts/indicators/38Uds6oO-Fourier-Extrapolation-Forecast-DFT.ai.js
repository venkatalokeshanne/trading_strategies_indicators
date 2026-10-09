describe_indicator('DFT Forecast', 'price');

// ------------------------------------------------------------------
// This indicator reproduces a TradingView Pine Script which runs a
// truncated inverse Discrete Fourier Transform (DFT) over a detrended
// window of closing prices, then extrapolates that cyclical model
// forward in time ("forecast_length" bars), anchored to the most
// recent close. Because TrendSpider scripts do not expose a concept
// equivalent to Pine's "barstate.islast" update loop, the model is
// simply (re)computed every time the script runs, always using the
// most recent "length" closes available - this is functionally
// equivalent to Pine's "if barstate.islast" block, since that block
// also only runs on the latest bar.
// ------------------------------------------------------------------

const myLength = input.number('DFT Length', 128, { min: 8, max: 2000 });
const myForecastLength = input.number('Forecast Length', 14, { min: 1, max: 100 });
const myNumHarmonics = input.number('Harmonics Used', 8, { min: 1, max: 100 });
const myAnchorToClose = input.boolean('Anchor Forecast to Last Close', true);

// Reconstructs the value of the truncated inverse DFT at time index myT_,
// using the real/imag coefficients computed over a window of size myN_,
// keeping only the first myM_ harmonics.
function myRecon(myRe, myIm, myN, myM, myT) {
	let myTotal = myRe[0] / myN;
	for (let myK = 1; myK <= myM; myK += 1) {
		const myAngle = 2 * Math.PI * myK * myT / myN;
		myTotal += (2.0 / myN) * (myRe[myK] * Math.cos(myAngle) - myIm[myK] * Math.sin(myAngle));
	}
	return myTotal;
}

const myN = Math.min(myLength, close.length);
assert(myN >= 8, 'Not enough candles to compute the DFT window');

// Build the chronological window: index 0 is the oldest candle in the
// window, index myN-1 is the current (last) candle. This matches
// Pine's "s" array after it un-reverses the series indexing.
const myS = [];
for (let myT = 0; myT < myN; myT += 1) {
	myS.push(close[close.length - myN + myT]);
}

// Least-squares linear trend over the window.
let mySumX = 0;
let mySumY = 0;
let mySumXY = 0;
let mySumX2 = 0;
for (let myT = 0; myT < myN; myT += 1) {
	const myY = myS[myT];
	mySumX += myT;
	mySumY += myY;
	mySumXY += myT * myY;
	mySumX2 += myT * myT;
}
const mySlope = (myN * mySumXY - mySumX * mySumY) / (myN * mySumX2 - mySumX * mySumX);
const myIntercept = (mySumY - mySlope * mySumX) / myN;

// Detrended residual.
const myResid = [];
for (let myT = 0; myT < myN; myT += 1) {
	myResid.push(myS[myT] - (myIntercept + mySlope * myT));
}

// DFT coefficients for the low harmonics only.
const myM = Math.min(myNumHarmonics, Math.floor(myN / 2) - 1);
assert(myM >= 0, 'Harmonics count is too large for the chosen DFT Length');

const myRe = [];
const myIm = [];
for (let myK = 0; myK <= myM; myK += 1) {
	let myReSum = 0;
	let myImSum = 0;
	for (let myT = 0; myT < myN; myT += 1) {
		const myAngle = 2 * Math.PI * myK * myT / myN;
		myReSum += myResid[myT] * Math.cos(myAngle);
		myImSum -= myResid[myT] * Math.sin(myAngle);
	}
	myRe.push(myReSum);
	myIm.push(myImSum);
}

// Shift the whole forecast so it starts exactly at the last close.
const myLastClose = close[close.length - 1];
const myModelNow = myIntercept + mySlope * (myN - 1) + myRecon(myRe, myIm, myN, myM, myN - 1);
const myOffset = myAnchorToClose ? (myLastClose - myModelNow) : 0.0;

// First forecast point is the next bar (h = 1).
const myForecastValues = [];
for (let myH = 1; myH <= myForecastLength; myH += 1) {
	const myT = myN - 1 + myH;
	const myY = myIntercept + mySlope * myT + myRecon(myRe, myIm, myN, myM, myT) + myOffset;
	myForecastValues.push(myY);
}

paint_projection(myForecastValues, { name: 'DFTForecast', color: 'red', thickness: 2 });

// Scanning / strategy signal: forecast implies an uptrend if the last
// forecasted point sits above the current close.
const myForecastEnd = myForecastValues.length > 0 ? myForecastValues[myForecastValues.length - 1] : myLastClose;
const myUptrendSignal = series_of(myForecastEnd > myLastClose);
const myDowntrendSignal = series_of(myForecastEnd < myLastClose);

register_signal(myUptrendSignal, 'DFT Forecast Uptrend');
register_signal(myDowntrendSignal, 'DFT Forecast Downtrend');