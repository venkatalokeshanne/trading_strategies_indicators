describe_indicator('Grid Like Strategy (Pine Port)', 'price');

// NOTE: this is a best-effort port of a Pine Script v4 *strategy* into a
// Custom JS *indicator*. The platform's Custom JS API has no access to a
// real strategy/broker engine (no strategy.losstrades, strategy.entry,
// strategy.exit equivalents), so trade simulation (fills, win/loss
// tracking, martingale sizing) is reproduced manually with a simple
// bar-by-bar simulation loop. Results should match the Pine baseline
// values exactly, but position sizing/win-loss outcomes are an
// approximation of the real strategy engine (intrabar stop/limit fills
// are approximated using high/low of subsequent candles).

const myPoint = input.number('Point', 2, { min: 0.0001, max: 100000 });
const myOrderSize = input.number('Order Size', 1, { min: 0.0001, max: 1000000 });
const myMartingaleMultiplier = input.number('Martingale Multiplier', 2, { min: 0.0001, max: 100 });
const myAntiMartingale = input.boolean('Anti Martingale', false);

const myCandleCount = close.length;

// --- baseline computation (identical to Pine logic) ---
const myBaseline = series_of(null);
for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myPrevBaseline = myIndex === 0 ? 0 : (myBaseline[myIndex - 1] !== null ? myBaseline[myIndex - 1] : 0);
	const myCloseValue = close[myIndex];
	if (myCloseValue > myPrevBaseline + myPoint || myCloseValue < myPrevBaseline - myPoint) {
		myBaseline[myIndex] = myCloseValue;
	}
	else {
		myBaseline[myIndex] = myPrevBaseline;
	}
}

const myUpper = add(myBaseline, myPoint);
const myLower = sub(myBaseline, myPoint);

// --- trade simulation to reproduce size (martingale) and buy/sell signals ---
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);

let mySize = myOrderSize;
let myOpenTrade = null; // { direction: 'long'|'short', entryIndex, stop, limit }

for (let myIndex = 1; myIndex < myCandleCount; myIndex += 1) {
	// check if an open trade gets closed on this candle (stop or limit touch)
	if (myOpenTrade !== null) {
		const myHigh = high[myIndex];
		const myLow = low[myIndex];
		let myClosed = false;
		let myWasWin = false;

		if (myOpenTrade.direction === 'long') {
			const myHitStop = myLow <= myOpenTrade.stop;
			const myHitLimit = myHigh >= myOpenTrade.limit;
			if (myHitStop || myHitLimit) {
				myClosed = true;
				myWasWin = myHitLimit && !myHitStop;
			}
		}
		else {
			const myHitStop = myHigh >= myOpenTrade.stop;
			const myHitLimit = myLow <= myOpenTrade.limit;
			if (myHitStop || myHitLimit) {
				myClosed = true;
				myWasWin = myHitLimit && !myHitStop;
			}
		}

		if (myClosed) {
			if (myAntiMartingale) {
				mySize = myWasWin ? mySize * myMartingaleMultiplier : myOrderSize;
			}
			else {
				mySize = myWasWin ? myOrderSize : mySize * myMartingaleMultiplier;
			}
			myOpenTrade = null;
		}
	}

	// new entries happen when baseline crosses up/down vs previous bar
	const myBaselineUp = myBaseline[myIndex] > myBaseline[myIndex - 1];
	const myBaselineDown = myBaseline[myIndex] < myBaseline[myIndex - 1];

	if (myBaselineUp) {
		myBuySignal[myIndex] = true;
		myOpenTrade = { direction: 'long', entryIndex: myIndex, stop: myLower[myIndex], limit: myUpper[myIndex] };
	}
	else if (myBaselineDown) {
		mySellSignal[myIndex] = true;
		myOpenTrade = { direction: 'short', entryIndex: myIndex, stop: myUpper[myIndex], limit: myLower[myIndex] };
	}
}

// --- painting ---
paint(myBaseline, { name: 'Baseline', color: '#2157f3', thickness: 2 });
paint(myUpper, { name: 'Upper', color: 'silver', style: 'dotted' });
paint(myLower, { name: 'Lower', color: 'silver', style: 'dotted' });

// --- scanner/alert/strategy applicable signals ---
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');