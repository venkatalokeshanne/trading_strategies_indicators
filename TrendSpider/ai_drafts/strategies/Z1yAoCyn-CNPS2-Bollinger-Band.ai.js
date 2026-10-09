describe_indicator('CNPS2 Bollinger Band Strategy', 'price');

// ==== INPUTS ====
const myLength = input.number('BB Length', 20, { min: 1, max: 500 });
const myMult = input.number('BB Multiplier', 2.0, { min: 0.1, max: 10 });
const mySlPoints = input.number('Stop Loss (points)', 10, { min: 0, max: 100000 });
const myTradeDirection = input.select('Trade Direction', 'Both', ['Buy', 'Sell', 'Both']);

// ==== BOLLINGER BANDS ====
const myBasis = sma(close, myLength);
const myDev = mult(stdev(close, myLength), myMult);

const myUpper = add(myBasis, myDev);
const myLower = sub(myBasis, myDev);

// ==== STRATEGY SIMULATION ====
// We simulate position state bar by bar, reproducing the Pine logic:
// entries happen when close crosses outside the bands, exits happen
// either via the opposite band touch or via the fixed point stop loss.
// Only one position (Long or Short) can be open at a time, same as
// strategy.entry() behavior in Pine with default netting.
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

const myLongSlLine = series_of(null);
const myShortSlLine = series_of(null);

let myPositionSize = 0; // 0 = flat, 1 = long, -1 = short
let myPositionAvgPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myClose = close[myIndex];
	const myUpperValue = myUpper[myIndex];
	const myLowerValue = myLower[myIndex];

	const myLongCondition = myClose > myUpperValue;
	const myShortCondition = myClose < myLowerValue;

	const myAllowLong = myTradeDirection === 'Buy' || myTradeDirection === 'Both';
	const myAllowShort = myTradeDirection === 'Sell' || myTradeDirection === 'Both';

	// ==== ENTRY ====
	if (myAllowLong && myLongCondition && myPositionSize <= 0) {
		myPositionSize = 1;
		myPositionAvgPrice = myClose;
		myLongEntrySignal[myIndex] = true;
	}

	if (myAllowShort && myShortCondition && myPositionSize >= 0) {
		myPositionSize = -1;
		myPositionAvgPrice = myClose;
		myShortEntrySignal[myIndex] = true;
	}

	// ==== STOP LOSS LEVELS ====
	const myLongSl = myPositionAvgPrice !== null ? myPositionAvgPrice - mySlPoints : null;
	const myShortSl = myPositionAvgPrice !== null ? myPositionAvgPrice + mySlPoints : null;

	// ==== EXIT CONDITIONS ====
	if (myPositionSize > 0) {
		const myLongExit = myClose < myLowerValue;
		const myLongSlHit = myLongSl !== null && myClose <= myLongSl;

		if (myLongExit || myLongSlHit) {
			myPositionSize = 0;
			myPositionAvgPrice = null;
			myLongExitSignal[myIndex] = true;
		}
	}

	if (myPositionSize < 0) {
		const myShortExit = myClose > myUpperValue;
		const myShortSlHit = myShortSl !== null && myClose >= myShortSl;

		if (myShortExit || myShortSlHit) {
			myPositionSize = 0;
			myPositionAvgPrice = null;
			myShortExitSignal[myIndex] = true;
		}
	}

	myLongSlLine[myIndex] = myPositionSize > 0 ? myLongSl : null;
	myShortSlLine[myIndex] = myPositionSize < 0 ? myShortSl : null;
}

// ==== PLOT BB ====
paint(myBasis, { name: 'BB Basis', color: 'orange', thickness: 1 });
paint(myUpper, { name: 'BB Upper', color: 'blue', thickness: 1 });
paint(myLower, { name: 'BB Lower', color: 'blue', thickness: 1 });

// ==== PLOT STOP LOSS ====
paint(myLongSlLine, { name: 'Long Stop Loss', color: 'red', style: 'ladder' });
paint(myShortSlLine, { name: 'Short Stop Loss', color: 'red', style: 'ladder' });

// ==== SIGNALS FOR SCANNER STRATEGY ====
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');