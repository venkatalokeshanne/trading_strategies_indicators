describe_indicator('HS SPX 1.6x Long Benchmark Signals', 'price');

// NOTE: TrendSpider Custom JS indicators cannot place broker orders,
// manage equity, leverage, commissions or slippage like a TradingView
// strategy() script. This indicator reproduces the ENTRY/EXIT LOGIC
// (date window based) as signals and markers only. Position sizing
// (160% of equity), 0.075% commission, 2 tick slippage and 50%/100%
// margin are not representable here and are therefore not simulated.

const myStartTime = input.number('Backtest start (unix seconds)', 1521158400, { min: 0 });
const myEndTime = input.number('Backtest end (unix seconds)', 1779753600, { min: 0 });

// Whether each candle's time falls inside the configured window
const myInWindow = for_every(time, _t => _t >= myStartTime && _t <= myEndTime);

// Simulate position state (long only, no pyramiding), mirroring
// the Pine logic: enter when in window and flat/short, close when
// outside the window and currently long.
const myEntrySignal = series_of(false);
const myExitSignal = series_of(false);
const myPositionLong = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevLong = myIndex > 0 ? myPositionLong[myIndex - 1] : false;
	let myCurrentLong = myPrevLong;

	if (myInWindow[myIndex] && !myPrevLong) {
		myEntrySignal[myIndex] = true;
		myCurrentLong = true;
	}
	else if (!myInWindow[myIndex] && myPrevLong) {
		myExitSignal[myIndex] = true;
		myCurrentLong = false;
	}

	myPositionLong[myIndex] = myCurrentLong;
}

// Markers for entries/exits
const myEntryMarks = for_every(myEntrySignal, _e => _e ? low : null);
const myExitMarks = for_every(myExitSignal, _e => _e ? high : null);

paint(myEntryMarks, { style: 'labels_below', color: 'green', name: 'EntryLong' });
paint(myExitMarks, { style: 'labels_above', color: 'red', name: 'ExitLong' });

// Signals for scanners, alerts and strategy tester
register_signal(myEntrySignal, 'Enter Long');
register_signal(myExitSignal, 'Exit Long');
register_signal(myPositionLong, 'In Long Position');