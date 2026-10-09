describe_indicator('Range Trading SOLUSD Pine Conversion', 'price');

// This converts a TradingView Pine strategy into an indicator with signals.
// Pine strategy state (strategy.position_size, strategy.position_avg_price)
// is approximated here with a simple position-tracking loop that assumes a
// single open position at a time (long or short), opened at the close price
// of the signal bar. Pyramiding (up to 3 entries) from the original script
// is NOT replicated; this is a single-position approximation.

const myLookback = input.number('Lookback', 72, { min: 1, max: 500 });
const myOffsetLong = input.number('Offsetlong', 9, { min: 0, max: 1000 });
const myOffsetShort = input.number('Offsetshort', 12, { min: 0, max: 1000 });
const myMaxLoss = input.number('Max Verlust pro Trade', 7, { min: 0, max: 100000 });

// high1 = ta.highest(high[12], length) -> shift high by 12, then rolling highest
const myHigh1 = highest(shift(high, 12), myLookback);
const myLow1 = lowest(shift(low, 12), myLookback);

const myAbsHigh = add(myHigh1, myOffsetLong);
const myAbsLow = sub(myLow1, myOffsetShort);

// crossunder(close, high1) and crossover(close, low1)
const myShortCondition = for_every(close, myHigh1, (_c, _h1, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevClose = close[_i - 1];
	const myPrevHigh1 = myHigh1[_i - 1];
	if (myPrevClose === null || myPrevHigh1 === null || _h1 === null) return false;
	return myPrevClose >= myPrevHigh1 && _c < _h1;
});

const myLongCondition = for_every(close, myLow1, (_c, _l1, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevClose = close[_i - 1];
	const myPrevLow1 = myLow1[_i - 1];
	if (myPrevClose === null || myPrevLow1 === null || _l1 === null) return false;
	return myPrevClose <= myPrevLow1 && _c > _l1;
});

// Position state simulation: 0 = flat, 1 = long, -1 = short
const myPositionSide = series_of(0);
const myPositionAvgPrice = series_of(null);

const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitRangeSignal = series_of(false);
const myShortExitRangeSignal = series_of(false);
const myShortExitRiskSignal = series_of(false);
const myLongExitRiskSignal = series_of(false);
const myCloseAllMaxLossSignal = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	let mySide = myIndex > 0 ? myPositionSide[myIndex - 1] : 0;
	let myAvgPrice = myIndex > 0 ? myPositionAvgPrice[myIndex - 1] : null;

	// Entries (only if flat, since pyramiding is not replicated)
	if (mySide === 0 && myShortCondition[myIndex]) {
		mySide = -1;
		myAvgPrice = close[myIndex];
		myShortEntrySignal[myIndex] = true;
	}
	else if (mySide === 0 && myLongCondition[myIndex]) {
		mySide = 1;
		myAvgPrice = close[myIndex];
		myLongEntrySignal[myIndex] = true;
	}

	// Range exits
	if (mySide === 1 && myHigh1[myIndex] !== null && high[myIndex] > myHigh1[myIndex]) {
		myLongExitRangeSignal[myIndex] = true;
		mySide = 0;
		myAvgPrice = null;
	}
	if (mySide === -1 && myLow1[myIndex] !== null && low[myIndex] < myLow1[myIndex]) {
		myShortExitRangeSignal[myIndex] = true;
		mySide = 0;
		myAvgPrice = null;
	}

	// Risk management exits
	if (mySide === -1 && myAbsHigh[myIndex] !== null && high[myIndex] > myAbsHigh[myIndex]) {
		myShortExitRiskSignal[myIndex] = true;
		mySide = 0;
		myAvgPrice = null;
	}
	if (mySide === 1 && myAbsLow[myIndex] !== null && low[myIndex] < myAbsLow[myIndex]) {
		myLongExitRiskSignal[myIndex] = true;
		mySide = 0;
		myAvgPrice = null;
	}

	// Max loss failsafe close-all
	if (mySide !== 0 && myAvgPrice !== null) {
		const myCurrentLoss = mySide > 0 ? (myAvgPrice - close[myIndex]) : (close[myIndex] - myAvgPrice);
		if (myCurrentLoss > myMaxLoss) {
			myCloseAllMaxLossSignal[myIndex] = true;
			mySide = 0;
			myAvgPrice = null;
		}
	}

	myPositionSide[myIndex] = mySide;
	myPositionAvgPrice[myIndex] = myAvgPrice;
}

paint(myHigh1, { name: 'VAH', color: '#ef5350' });
paint(myLow1, { name: 'VAL', color: '#26a69a' });
paint(myAbsHigh, { name: 'AbsHigh', color: '#dd17c3' });
paint(myAbsLow, { name: 'AbsLow', color: '#1239e9' });

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitRangeSignal, 'Long Exit Range');
register_signal(myShortExitRangeSignal, 'Short Exit Range');
register_signal(myShortExitRiskSignal, 'Short Exit Risk');
register_signal(myLongExitRiskSignal, 'Long Exit Risk');
register_signal(myCloseAllMaxLossSignal, 'Close All Max Loss');