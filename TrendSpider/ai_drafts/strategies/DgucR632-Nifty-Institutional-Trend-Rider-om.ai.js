describe_indicator('Nifty Institutional Trend Rider', 'price');

// --- Inputs ---
const myRsiLen = input.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiUpper = input.number('RSI Bullish (CE) Level', 60, { min: 1, max: 99 });
const myRsiLower = input.number('RSI Bearish (PE) Level', 40, { min: 1, max: 99 });
const myEmaLen = input.number('Trend Filter EMA', 20, { min: 1, max: 500 });
const myTrailPerc = input.number('Trailing Stop Loss (%)', 0.5, { min: 0.01, max: 50, step: 0.1 });

const myTrailFraction = myTrailPerc / 100;

// --- Indicators ---
const myRsiValue = rsi(close, myRsiLen);
const myEmaValue = ema(close, myEmaLen);

// Pine's ta.vwap resets every new session (day). TrendSpider's built-in vwap()
// only supports "from a fixed index to the end", so we approximate Pine's
// session-anchored VWAP manually, resetting cumulative sums at each new
// trading session (as determined by bar_at()).
const myVwapValue = series_of(null);
{
	let myCumPV = 0;
	let myCumVol = 0;
	let myPrevSession = null;

	for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
		const mySession = bar_at(time[myIndex]).session;

		if (mySession !== myPrevSession) {
			myCumPV = 0;
			myCumVol = 0;
			myPrevSession = mySession;
		}

		const myTypicalPrice = hlc3[myIndex];
		myCumPV += myTypicalPrice * volume[myIndex];
		myCumVol += volume[myIndex];

		myVwapValue[myIndex] = myCumVol !== 0 ? myCumPV / myCumVol : close[myIndex];
	}
}

// --- Logic ---
const myLongCondition = series_of(false);
const myShortCondition = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	myLongCondition[myIndex] = close[myIndex] > myVwapValue[myIndex] && close[myIndex] > myEmaValue[myIndex] && myRsiValue[myIndex] > myRsiUpper;
	myShortCondition[myIndex] = close[myIndex] < myVwapValue[myIndex] && close[myIndex] < myEmaValue[myIndex] && myRsiValue[myIndex] < myRsiLower;
}

// --- Strategy simulation (position tracking + trailing stop) ---
// Replicates the Pine strategy.entry/strategy.exit behavior sequentially,
// assuming only one position can be open at a time (long or short).
const myPositionSize = series_of(0);
const myLongStopPrice = series_of(null);
const myShortStopPrice = series_of(null);
const myExitLongSignal = series_of(false);
const myExitShortSignal = series_of(false);

{
	let myPrevPosition = 0;
	let myPrevLongStop = 0;
	let myPrevShortStop = 999999;

	for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
		let myCurrentPosition = myPrevPosition;

		// Entry logic (only enters if currently flat, like a single-position strategy)
		if (myLongCondition[myIndex] && myCurrentPosition <= 0) {
			myCurrentPosition = 1;
		}
		else if (myShortCondition[myIndex] && myCurrentPosition >= 0) {
			myCurrentPosition = -1;
		}

		// Trailing stop computation
		let myLongStop = 0;
		let myShortStop = 999999;

		if (myCurrentPosition > 0) {
			const myStopValue = close[myIndex] * (1 - myTrailFraction);
			myLongStop = Math.max(myStopValue, myPrevPosition > 0 ? myPrevLongStop : 0);

			// Check exit (stop hit)
			if (low[myIndex] <= myLongStop) {
				myExitLongSignal[myIndex] = true;
				myCurrentPosition = 0;
			}
		}
		else if (myCurrentPosition < 0) {
			const myStopValue = close[myIndex] * (1 + myTrailFraction);
			myShortStop = Math.min(myStopValue, myPrevPosition < 0 ? myPrevShortStop : 999999);

			// Check exit (stop hit)
			if (high[myIndex] >= myShortStop) {
				myExitShortSignal[myIndex] = true;
				myCurrentPosition = 0;
			}
		}

		myPositionSize[myIndex] = myCurrentPosition;
		myLongStopPrice[myIndex] = myCurrentPosition > 0 ? myLongStop : null;
		myShortStopPrice[myIndex] = myCurrentPosition < 0 ? myShortStop : null;

		myPrevPosition = myCurrentPosition;
		myPrevLongStop = myLongStop;
		myPrevShortStop = myShortStop;
	}
}

// Combined trailing SL line (long stop when long, short stop when short, null otherwise)
const myTrailingStopLine = for_every(myLongStopPrice, myShortStopPrice, (_myLong, _myShort) => _myLong !== null ? _myLong : (_myShort !== null ? _myShort : null));

// --- Visuals ---
paint(myVwapValue, { name: 'VWAP', color: 'orange', thickness: 2 });
paint(myEmaValue, { name: 'Trend EMA', color: 'blue', thickness: 2 });
paint(myTrailingStopLine, { name: 'Trailing SL', color: 'red', style: 'ladder', thickness: 2 });

// --- Scanner / Strategy signals ---
register_signal(myLongCondition, 'CE Entry Long');
register_signal(myShortCondition, 'PE Entry Short');
register_signal(myExitLongSignal, 'Exit CE');
register_signal(myExitShortSignal, 'Exit PE');