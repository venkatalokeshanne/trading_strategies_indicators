describe_indicator('Swing Breakout Strategy (quant-core)', 'price');
// NOTE: this is a best-effort translation of a TradingView Pine Script
// strategy into TrendSpider Custom JS. TrendSpider does not have a
// strategy/backtest engine object (strategy.*), so position state,
// peak/trail and entry/exit are reproduced manually with a stateful
// plain loop (not for_every(), since for_every() turned out to not
// reliably carry an object as "previous value" across candles, which
// was the root cause of the "Cannot read properties of null" error).
// Order fills, commission and slippage from the original Pine
// strategy() declaration are NOT simulated here, only the signal
// logic. Entry is assumed to happen on the same bar as the goLong
// signal (Pine actually fills next bar open in real backtests) and
// the ATR trailing stop is checked (low <= trail) on the same bar it
// is updated, which is an approximation of Pine's intrabar stop order
// behavior.
// FIX: register_signal() and paint() names must be unique across the
// whole indicator (they share one namespace). "Breakout Entry" was
// used both for a paint() call and a register_signal() call, which
// caused the "signal already exists" error. Painted lines now use
// distinct names ("Breakout Entry Marker" / "Developing Marker").
const myBreakoutLen = input.number('Breakout lookback', 50, { min: 5 });
const myVolMult = input.number('Volume x 50d avg', 1.5, { min: 0.5, step: 0.1 });
const myFastLen = input.number('Fast MA', 50, { min: 2 });
const mySlowLen = input.number('Slow MA', 200, { min: 5 });
const myAtrLen = input.number('ATR length', 14, { min: 2 });
const myTrailMult = input.number('ATR trailing multiple', 4.0, { min: 0.5, step: 0.5 });
const myWatchPct = input.number('Watch percent below BO', 3.0, { min: 0.5, step: 0.5 });

const mySmaFast = sma(close, myFastLen);
const mySmaSlow = sma(close, mySlowLen);
const myAtr = atr(high, low, close, myAtrLen);
const myVolAvg = sma(volume, 50);

// priorHigh = ta.highest(close, breakoutLen)[1] -> highest of close over N
// bars, taken from the previous bar (shifted by 1, no lookahead)
const myHighestClose = highest(close, myBreakoutLen);
const myPriorHigh = shift(myHighestClose, 1);

const myWarm = for_every(mySmaSlow, myVolAvg, myPriorHigh, (_s, _v, _p) => (
	_s !== null && !isNaN(_s) && _v !== null && !isNaN(_v) && _p !== null && !isNaN(_p)
));

const myUptrend = for_every(close, mySmaFast, mySmaSlow, (_c, _f, _s) => (
	_c > _f && _c > _s && _f > _s
));

const myBreakout = for_every(close, myPriorHigh, volume, myVolAvg, (_c, _p, _v, _va) => (
	_p !== null && _c > _p && _v >= myVolMult * _va
));

const myGoLongRaw = for_every(myWarm, myUptrend, myBreakout, (_w, _u, _b) => (_w && _u && _b));

const myDeveloping = for_every(myWarm, myUptrend, myBreakout, close, myPriorHigh, (_w, _u, _b, _c, _p) => (
	_w && _u && !_b && _p !== null && _c < _p && ((_p / _c - 1.0) <= myWatchPct / 100.0)
));

// Stateful simulation of strategy.position_size, peak and trail, done
// via a plain loop instead of for_every() to avoid the object-shaped
// "previous value" issue that caused the reported null error.
const myTrailLine = series_of(null);
const myEntrySignal = series_of(false);
const myExitSignal = series_of(false);
const myInPositionSignal = series_of(false);

let myInPos = false;
let myPeak = null;
let myTrail = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	let myEntered = false;
	let myExited = false;

	if (!myInPos && myGoLongRaw[myIndex]) {
		myInPos = true;
		myEntered = true;
		myPeak = null;
		myTrail = null;
	}

	if (myInPos) {
		myPeak = (myPeak === null) ? high[myIndex] : Math.max(myPeak, high[myIndex]);
		const myCand = myPeak - myTrailMult * myAtr[myIndex];
		myTrail = (myTrail === null) ? myCand : Math.max(myTrail, myCand);

		if (low[myIndex] <= myTrail) {
			myInPos = false;
			myExited = true;
		}
	}

	if (!myInPos) {
		myPeak = null;
		myTrail = null;
	}

	myTrailLine[myIndex] = myTrail;
	myEntrySignal[myIndex] = myEntered;
	myExitSignal[myIndex] = myExited;
	myInPositionSignal[myIndex] = myInPos;
}

paint(mySmaFast, { name: 'Fast MA', color: 'orange', thickness: 2 });
paint(mySmaSlow, { name: 'Slow MA', color: 'blue', thickness: 2 });
paint(myTrailLine, { name: 'Trail Stop', color: 'red', style: 'line', thickness: 2 });

const myBuyShapeSeries = for_every(myEntrySignal, low, (_e, _l) => (_e ? _l : null));
const myDevShapeSeries = for_every(myDeveloping, low, (_d, _l) => (_d ? _l : null));

paint(myBuyShapeSeries, { name: 'Breakout Entry Marker', style: 'labels_below', color: 'green', thickness: 3 });
paint(myDevShapeSeries, { name: 'Developing Marker', style: 'labels_below', color: 'yellow', thickness: 2 });

register_signal(myEntrySignal, 'Breakout Entry');
register_signal(myDeveloping, 'Approaching Breakout');
register_signal(myExitSignal, 'Trail Stop Exit');
register_signal(myInPositionSignal, 'In Position');
register_signal(myUptrend, 'Uptrend Regime');