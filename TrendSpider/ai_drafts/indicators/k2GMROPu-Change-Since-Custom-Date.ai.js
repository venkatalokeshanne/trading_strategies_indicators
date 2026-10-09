describe_indicator('Change Since Custom Date', 'lower');

// Date inputs matching the Pine Script target date
const myTargetYear = input.number('Year', 2023, { min: 1970, max: 2100 });
const myTargetMonth = input.number('Month', 10, { min: 1, max: 12 });
const myTargetDay = input.number('Day', 15, { min: 1, max: 31 });

// Build a Unix timestamp (UTC midnight) for the target date, equivalent
// to Pine's timestamp(year, month, day, 0, 0)
const myTargetTime = Date.UTC(myTargetYear, myTargetMonth - 1, myTargetDay, 0, 0, 0) / 1000;

// Find the first candle whose time is >= target_time, and lock in its close,
// exactly like Pine's "var float price_at_date" logic (sticky, set once)
let myPriceAtDate = null;
const myPctChange = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPriceAtDate === null && time[myIndex] >= myTargetTime) {
		myPriceAtDate = close[myIndex];
	}

	if (myPriceAtDate !== null) {
		myPctChange[myIndex] = ((close[myIndex] - myPriceAtDate) / myPriceAtDate) * 100;
	}
}

const myPctChangeLinePainted = paint(myPctChange, { name: 'Percent Gained', color: '#2E86DE', thickness: 2 });

// Registering it as a signal makes the value usable in Scanners,
// Alerts and Strategy Tester, mapping the "plot for screener" intent
// from the original Pine script.
register_signal(myPctChange, 'Percent Gained Value');

// Additional convenience signals for scanning/strategy use: whether price
// is currently above or below the price recorded on the target date
const myIsAboveTargetPrice = for_every(myPctChange, _p => _p !== null && _p > 0);
const myIsBelowTargetPrice = for_every(myPctChange, _p => _p !== null && _p < 0);

register_signal(myIsAboveTargetPrice, 'Above Target Date Price');
register_signal(myIsBelowTargetPrice, 'Below Target Date Price');