describe_indicator('BB Strategy with Loss Control', 'price');
// NOTE: TrendSpider Custom JS has no strategy/broker engine like Pine Script.
// This script re-implements the Pine logic manually, bar by bar, using plain
// JS state variables inside a single loop (allowed since we are not calling
// built-in indicator functions inside the loop, only plain math/comparisons).
// Approximations made (see errors_and_warnings_flagged):
//   * Entries are assumed to fill at the signal bar's close (Pine's default
//     "next bar open" fill timing can't be replicated without a broker engine).
//   * Stop-loss exits are checked intrabar using that same bar's low/high.
//   * Opposite-direction signals are treated as "close current & reverse"
//     exactly as Pine's default (non-pyramided) strategy.entry() behavior.
// FIX: register_signal() names must be unique across the whole indicator,
// and they were colliding with the paint() labels names used for the entry
// and exit marks ("Long Entry", "Short Entry", etc). Renamed the signal
// names below so they no longer clash with the painted label names.
const myLength = input.number('Length', 20, { min: 1, max: 500 });
const myMult = input.number('Mult', 2.0, { min: 0.1, max: 10 });
const mySlValue = input.number('Stop Loss ($)', 8.0, { min: 0.01, max: 10000 });

const mySource = close;
const myBasis = sma(mySource, myLength);
const myDev = mult(stdev(mySource, myLength), myMult);
const myUpper = add(myBasis, myDev);
const myLower = sub(myBasis, myDev);

// crossover(source, lower): source crosses above lower
const myLongSignal = for_every(mySource, myLower, (_s, _l, _prev, _i) => {
	if (_i === 0) return false;
	return _s > _l && mySource[_i - 1] <= myLower[_i - 1];
});

// crossunder(source, upper): source crosses below upper
const myShortSignal = for_every(mySource, myUpper, (_s, _u, _prev, _i) => {
	if (_i === 0) return false;
	return _s < _u && mySource[_i - 1] >= myUpper[_i - 1];
});

const myLongEntryMarks = series_of(null);
const myShortEntryMarks = series_of(null);
const myLongExitMarks = series_of(null);
const myShortExitMarks = series_of(null);

const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);
const myLongBlockedSignal = series_of(false);
const myShortBlockedSignal = series_of(false);

let myPosition = 0; // 0 flat, 1 long, -1 short
let myEntryPrice = null;
let myLastDirection = 0;
let myLongLossCount = 0;
let myShortLossCount = 0;
let myLongBlocked = false;
let myShortBlocked = false;

function myProcessClosedTrade(_profit) {
	if (myLastDirection === 1) {
		if (_profit < 0) {
			myLongLossCount += 1;
		}
		else {
			myLongLossCount = 0;
			myShortBlocked = false;
		}
		if (myLongLossCount >= 2) {
			myLongBlocked = true;
		}
	}
	else if (myLastDirection === -1) {
		if (_profit < 0) {
			myShortLossCount += 1;
		}
		else {
			myShortLossCount = 0;
			myLongBlocked = false;
		}
		if (myShortLossCount >= 2) {
			myShortBlocked = true;
		}
	}
}

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	let myDidLongEntry = false;
	let myDidShortEntry = false;
	let myDidLongExit = false;
	let myDidShortExit = false;

	if (myPosition === 1) {
		const myStopPrice = myEntryPrice - mySlValue;
		if (low[myIndex] <= myStopPrice) {
			myProcessClosedTrade(myStopPrice - myEntryPrice);
			myPosition = 0;
			myDidLongExit = true;
		}
		else if (myShortSignal[myIndex] && !myShortBlocked) {
			myProcessClosedTrade(close[myIndex] - myEntryPrice);
			myPosition = 0;
			myDidLongExit = true;
		}
	}
	else if (myPosition === -1) {
		const myStopPrice = myEntryPrice + mySlValue;
		if (high[myIndex] >= myStopPrice) {
			myProcessClosedTrade(myEntryPrice - myStopPrice);
			myPosition = 0;
			myDidShortExit = true;
		}
		else if (myLongSignal[myIndex] && !myLongBlocked) {
			myProcessClosedTrade(myEntryPrice - close[myIndex]);
			myPosition = 0;
			myDidShortExit = true;
		}
	}

	if (myPosition === 0) {
		if (myLongSignal[myIndex] && !myLongBlocked) {
			myPosition = 1;
			myEntryPrice = close[myIndex];
			myLastDirection = 1;
			myDidLongEntry = true;
		}
		else if (myShortSignal[myIndex] && !myShortBlocked) {
			myPosition = -1;
			myEntryPrice = close[myIndex];
			myLastDirection = -1;
			myDidShortEntry = true;
		}
	}

	myLongEntryMarks[myIndex] = myDidLongEntry ? low[myIndex] : null;
	myShortEntryMarks[myIndex] = myDidShortEntry ? high[myIndex] : null;
	myLongExitMarks[myIndex] = myDidLongExit ? high[myIndex] : null;
	myShortExitMarks[myIndex] = myDidShortExit ? low[myIndex] : null;

	myLongEntrySignal[myIndex] = myDidLongEntry;
	myShortEntrySignal[myIndex] = myDidShortEntry;
	myLongExitSignal[myIndex] = myDidLongExit;
	myShortExitSignal[myIndex] = myDidShortExit;
	myLongBlockedSignal[myIndex] = myLongBlocked;
	myShortBlockedSignal[myIndex] = myShortBlocked;
}

paint(myBasis, { name: 'Basis', color: 'gray', style: 'dotted' });

fill(
	paint(myUpper, { name: 'Upper', color: 'silver' }),
	paint(myLower, { name: 'Lower', color: 'silver' }),
	'blue',
	0.08
);

paint(myLongEntryMarks, { name: 'Long Entry', style: 'labels_below', color: 'green' });
paint(myShortEntryMarks, { name: 'Short Entry', style: 'labels_above', color: 'red' });
paint(myLongExitMarks, { name: 'Long Exit', style: 'labels_above', color: 'orange' });
paint(myShortExitMarks, { name: 'Short Exit', style: 'labels_below', color: 'orange' });

register_signal(myLongEntrySignal, 'Signal Long Entry');
register_signal(myShortEntrySignal, 'Signal Short Entry');
register_signal(myLongExitSignal, 'Signal Long Exit SL');
register_signal(myShortExitSignal, 'Signal Short Exit SL');
register_signal(myLongBlockedSignal, 'Signal Long Blocked');
register_signal(myShortBlockedSignal, 'Signal Short Blocked');