describe_indicator('ATH / 52W High Breakout Strategy', 'price');

// ==== INPUTS ====
const myUseATH = input.boolean('Use All-Time High', true);
const myUse52W = input.boolean('Use 52-Week High', true);

const myAtrGroup = input.group('ATR Settings');
const myAtrLength = myAtrGroup.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMult = myAtrGroup.number('ATR Multiplier', 2.0, { min: 0.1, max: 20, step: 0.1 });

const myExitGroup = input.group('Exit Settings');
const myUseEmaExit = myExitGroup.boolean('Use EMA Exit Instead of ATR', false);
const myEmaLength = myExitGroup.number('EMA Length for Exit', 20, { min: 1, max: 500 });

// ==== ALL TIME HIGH (running highest of high, from the start of history) ====
// Pine's "ta.highest(high, bar_index + 1)" is a cumulative running max.
// We reproduce it with a stateful for_every (cumulative max).
const myAth = for_every(high, (_h, _prev) => {
	if (_prev === null || _prev === undefined) {
		return _h;
	}
	return Math.max(_prev, _h);
});

// ==== 52 WEEK HIGH (weekly data) ====
const myWeeklyData = await request.history(current.ticker, 'W');
assert(!myWeeklyData.error, `Error fetching weekly data: "${myWeeklyData.error}"`);

const myWeeklyHighest = highest(myWeeklyData.high, 52);

// Land weekly highest onto the current time frame candles, using 'le' (last known
// completed weekly bar at or before the current candle time), then fill forward.
const myWeeklyHighLanded = land_points_onto_series(myWeeklyData.time, myWeeklyHighest, time, 'le');
const myWeeklyHigh = interpolate_sparse_series(myWeeklyHighLanded, 'constant');

// Pine compares against the *previous* bar's value ([1])
const myAthPrev = shift(myAth, 1);
const myWeeklyHighPrev = shift(myWeeklyHigh, 1);

// ==== ENTRY CONDITIONS ====
const myBreakAth = for_every(close, myAthPrev, (_c, _a) => myUseATH && _a !== null && _c > _a);
const myBreak52W = for_every(close, myWeeklyHighPrev, (_c, _w) => myUse52W && _w !== null && _c > _w);
const myLongCondition = for_every(myBreakAth, myBreak52W, (_a, _w) => _a || _w);

// ==== ATR AND EMA ====
const myAtr = atr(high, low, close, myAtrLength);
const myEma = ema(close, myEmaLength);

// ==== STATEFUL SIMULATION ====
// NOTE: This platform does not support full strategy backtesting (position
// sizing, equity curve, strategy.entry/exit) inside a Custom JS indicator.
// We approximate the Pine strategy logic with a single-position simulation
// that tracks entry price and either an ATR trailing-style stop or an EMA
// exit, generating entry/exit signals bar-by-bar.
let myInPosition = false;
let myEntryPrice = null;

const mySignalRaw = for_every(close, myLongCondition, myAtr, myEma, (_c, _long, _a, _e) => {
	let myEntryFired = false;
	let myExitFired = false;

	if (!myInPosition && _long) {
		myInPosition = true;
		myEntryPrice = _c;
		myEntryFired = true;
	}

	if (myInPosition && !myEntryFired) {
		if (!myUseEmaExit) {
			const myStopLevel = myEntryPrice - (_a * myAtrMult);
			if (_c <= myStopLevel) {
				myExitFired = true;
				myInPosition = false;
			}
		}
		else {
			if (_c < _e) {
				myExitFired = true;
				myInPosition = false;
			}
		}
	}

	if (myEntryFired) return 1;
	if (myExitFired) return -1;
	return 0;
});

const myEntrySignal = for_every(mySignalRaw, _s => _s === 1);
const myExitSignal = for_every(mySignalRaw, _s => _s === -1);

const myEntryMarks = for_every(mySignalRaw, low, (_s, _l) => _s === 1 ? _l : null);
const myExitMarks = for_every(mySignalRaw, high, (_s, _h) => _s === -1 ? _h : null);

// ==== REGISTER SIGNALS (for scanners, alerts, strategy tester) ====
register_signal(myEntrySignal, 'Long Entry');
register_signal(myExitSignal, 'Long Exit');

// ==== PLOTS ====
paint(myUseATH ? myAth : constants.empty_series, { name: 'ATH', color: 'maroon', thickness: 2 });
paint(myUse52W ? myWeeklyHigh : constants.empty_series, { name: 'High52W', color: 'red', thickness: 2 });
paint(myUseEmaExit ? myEma : constants.empty_series, { name: 'EMAExit', color: 'blue' });

paint(myEntryMarks, { name: 'LongEntry', style: 'labels_below', color: 'green' });
paint(myExitMarks, { name: 'LongExit', style: 'labels_above', color: 'red' });