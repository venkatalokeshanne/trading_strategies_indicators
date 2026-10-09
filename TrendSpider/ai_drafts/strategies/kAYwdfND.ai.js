describe_indicator('Simplified 30m Event Strategy Reverse', 'price');

// NOTE: This is a best-effort translation of a Pine Script v6 strategy.
// Pine's ta.valuewhen()/ta.pivothigh() carry-forward behavior is approximated
// using pivot_high()/pivot_low() plus a constant-interpolated carry-forward of
// the 30m pivot values landed onto the current chart's time axis. The bar-by-bar
// position simulation (entries/exits/pyramiding) is reproduced with an explicit
// sequential loop mirroring strategy.position_size, strategy.entry and
// strategy.close logic. Results should be very close to Pine's but exact tick by
// tick repainting behavior of ta.pivothigh/low (which only confirms after
// "right" bars) might differ slightly in edge cases.

const myLeft = input.number('Pivot Left', 2, { min: 1, max: 50 });
const myRight = input.number('Pivot Right', 3, { min: 1, max: 50 });
const myExitBars = input.number('Exit After X Bars', 6, { min: 1, max: 500 });
const myMinRange = input.number('Min Pivot Range', 5, { min: 0, max: 100000 });

const my30mData = await request.history(current.ticker, '30');
assert(!my30mData.error, 'Error fetching 30m data: ' + my30mData.error);

// Pivot highs/lows on the 30m time frame
const myPH30 = pivot_high(my30mData.high, myLeft, myRight);
const myPL30 = pivot_low(my30mData.low, myLeft, myRight);

// Carry-forward (valuewhen equivalent) on the 30m series itself
const myLastPH30 = interpolate_sparse_series(myPH30, 'constant');
const myLastPL30 = interpolate_sparse_series(myPL30, 'constant');

// Land the 30m carried-forward values onto the current chart's time axis
const myLastPHLanded = land_points_onto_series(my30mData.time, myLastPH30, time, 'le');
const myLastPLLanded = land_points_onto_series(my30mData.time, myLastPL30, time, 'le');
const myLastPH = interpolate_sparse_series(myLastPHLanded, 'constant');
const myLastPL = interpolate_sparse_series(myLastPLLanded, 'constant');

// Simplified delta
const myDelta = for_every(close, open, volume, (_c, _o, _v) => {
	if (_c > _o) return _v;
	if (_c < _o) return -_v;
	return 0;
});

const myValid = for_every(myLastPH, myLastPL, (_ph, _pl) => (
	_ph !== null && _pl !== null && (_ph - _pl) >= myMinRange
));

const myLongSignalRaw = for_every(myValid, close, myLastPL, myDelta, (_valid, _c, _pl, _d) => (
	_valid && _pl !== null && _c > _pl && _d < 0
));

const myShortSignalRaw = for_every(myValid, close, myLastPH, myDelta, (_valid, _c, _ph, _d) => (
	_valid && _ph !== null && _c < _ph && _d > 0
));

// Sequential simulation of position state, mirroring strategy.position_size,
// strategy.entry("Long"/"Short") and strategy.close("Long"/"Short")
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

let myPosition = 0;
let myLongBarCount = 0;
let myShortBarCount = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPosition > 0) {
		myLongBarCount += 1;
	}
	else {
		myLongBarCount = 0;
	}

	if (myPosition < 0) {
		myShortBarCount += 1;
	}
	else {
		myShortBarCount = 0;
	}

	if (myLongBarCount >= myExitBars && myPosition > 0) {
		myPosition = 0;
		myLongExitSignal[myIndex] = true;
	}

	if (myShortBarCount >= myExitBars && myPosition < 0) {
		myPosition = 0;
		myShortExitSignal[myIndex] = true;
	}

	if (myLongSignalRaw[myIndex]) {
		myPosition = 1;
		myLongEntrySignal[myIndex] = true;
	}

	if (myShortSignalRaw[myIndex]) {
		myPosition = -1;
		myShortEntrySignal[myIndex] = true;
	}
}

// Visualization of pivot levels
paint(myLastPH, { name: 'Last Pivot High', color: '#26A69A', thickness: 1 });
paint(myLastPL, { name: 'Last Pivot Low', color: '#EF5350', thickness: 1 });

// Buy/Sell marks
const myBuyMarks = for_every(myLongEntrySignal, low, (_sig, _l) => _sig ? _l : null);
const mySellMarks = for_every(myShortEntrySignal, high, (_sig, _h) => _sig ? _h : null);

paint(myBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'Sell Signal', style: 'labels_above', color: '#EF5350' });

// Scanning / backtesting signals
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');