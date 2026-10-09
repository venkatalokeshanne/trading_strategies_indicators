describe_indicator('CNPS Bollinger Band Strategy', 'price');

// Inputs
const myLength = input.number('BB Length', 20, { min: 1, max: 500 });
const myMult = input.number('BB Multiplier', 2.0, { min: 0.1, max: 10, step: 0.1 });
const mySlPoints = input.number('Stop Loss Points', 10, { min: 0, max: 10000 });
const myTradeDirection = input.select('Trade Direction', 'Both', ['Buy', 'Sell', 'Both']);

// Bollinger Bands
const myBasis = sma(close, myLength);
// fixed: first argument of mult() must be a series, so stdev() must come first
const myDev = mult(stdev(close, myLength), myMult);
const myUpper = add(myBasis, myDev);
const myLower = sub(myBasis, myDev);

// State simulation - replicates the Pine Script strategy logic bar by bar.
// Position: 0 = flat, 1 = long, -1 = short
let myPosition = 0;
let myAvgPrice = null;

const myLongSl = series_of(null);
const myShortSl = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

const myAllowLong = (myTradeDirection === 'Buy' || myTradeDirection === 'Both');
const myAllowShort = (myTradeDirection === 'Sell' || myTradeDirection === 'Both');

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myClose = close[myIndex];
	const myUpperValue = myUpper[myIndex];
	const myLowerValue = myLower[myIndex];

	if (myUpperValue == null || myLowerValue == null) {
		myLongSl[myIndex] = null;
		myShortSl[myIndex] = null;
		continue;
	}

	const myLongCondition = myClose > myUpperValue;
	const myShortCondition = myClose < myLowerValue;

	// Entries (Pine allows entry regardless of current position, reversing it)
	if (myAllowLong && myLongCondition) {
		myPosition = 1;
		myAvgPrice = myClose;
		myLongEntrySignal[myIndex] = true;
	}
	if (myAllowShort && myShortCondition) {
		myPosition = -1;
		myAvgPrice = myClose;
		myShortEntrySignal[myIndex] = true;
	}

	// Stop loss levels based on current position avg price
	const myLongSlValue = myAvgPrice != null ? myAvgPrice - mySlPoints : null;
	const myShortSlValue = myAvgPrice != null ? myAvgPrice + mySlPoints : null;

	// Exit conditions
	const myLongExit = myClose < myLowerValue;
	const myShortExit = myClose > myUpperValue;

	if (myPosition > 0 && myLongExit) {
		myPosition = 0;
		myAvgPrice = null;
		myLongExitSignal[myIndex] = true;
	}
	if (myPosition < 0 && myShortExit) {
		myPosition = 0;
		myAvgPrice = null;
		myShortExitSignal[myIndex] = true;
	}

	myLongSl[myIndex] = myPosition > 0 ? myLongSlValue : null;
	myShortSl[myIndex] = myPosition < 0 ? myShortSlValue : null;
}

// Paint Bollinger Bands
paint(myBasis, { name: 'BBBasis', color: 'orange', thickness: 1 });
const myUpperLine = paint(myUpper, { name: 'BBUpper', color: '#4DA3FF', thickness: 1 });
const myLowerLine = paint(myLower, { name: 'BBLower', color: '#4DA3FF', thickness: 1 });
fill(myUpperLine, myLowerLine, '#4DA3FF', 0.05);

// Paint stop loss lines (line breaks automatically when value is null)
paint(myLongSl, { name: 'LongStopLoss', color: 'red', thickness: 1 });
paint(myShortSl, { name: 'ShortStopLoss', color: 'red', thickness: 1 });

// Signals for scanners, alerts and backtesting
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');