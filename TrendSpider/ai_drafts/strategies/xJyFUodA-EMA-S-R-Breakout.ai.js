describe_indicator('EMA S/R Breakout', 'price');

// ─── INPUTS ───────────────────────────────────────────────────────────────────
const myEma9Len = input.number('EMA Fast', 9, { min: 1, max: 200 });
const myEma20Len = input.number('EMA Slow', 20, { min: 1, max: 200 });
const mySrLookback = input.number('SR Lookback Bars', 20, { min: 2, max: 200 });

// Target % and Stop Loss % are kept as inputs for documentation purposes only;
// actual trade management (limit/stop orders) cannot be replicated here,
// see note below.
const myTargetPct = input.number('Target Percent', 12.0, { min: 0, max: 1000, step: 0.5 });
const mySlPct = input.number('Stop Loss Percent', 6.0, { min: 0, max: 1000, step: 0.5 });

// ─── EMA ──────────────────────────────────────────────────────────────────────
const myEma9 = ema(close, myEma9Len);
const myEma20 = ema(close, myEma20Len);

paint(myEma9, { name: 'EMA9', color: 'orange', thickness: 2 });
paint(myEma20, { name: 'EMA20', color: 'blue', thickness: 2 });

// ─── S/R LEVELS (no lag - rolling highest/lowest of COMPLETED bars) ───────────
// Pine uses high[1]/low[1] inside ta.highest/ta.lowest, which means
// "highest/lowest of the previous sr_lookback completed bars".
// We reproduce that by shifting high/low by 1 bar before applying highest/lowest.
const myRes = shift(highest(shift(high, 1), mySrLookback), 0);
const mySup = shift(lowest(shift(low, 1), mySrLookback), 0);

paint(myRes, { name: 'Resistance', color: 'red', style: 'dotted', thickness: 1 });
paint(mySup, { name: 'Support', color: 'green', style: 'dotted', thickness: 1 });

// ─── PIVOT POINTS (approximation of line.new dotted segments) ────────────────
// Pine draws short dotted segments at pivot high/low points using
// line.new with fixed offsets. The Custom JS API has no equivalent of
// drawing arbitrary short line segments anchored at historical bars with
// a +/-4 bar extension, so we approximate this visually by plotting the
// pivot high/low points themselves as dotted markers.
const myPivotHigh = pivot_high(high, mySrLookback, mySrLookback);
const myPivotLow = pivot_low(low, mySrLookback, mySrLookback);

paint(myPivotHigh, { name: 'Pivot High', style: 'dotted', color: 'red', thickness: 2 });
paint(myPivotLow, { name: 'Pivot Low', style: 'dotted', color: 'green', thickness: 2 });

// ─── BREAKOUT CONDITIONS ──────────────────────────────────────────────────────
// crossover(close, res): close crosses above res this bar
// crossunder(close, sup): close crosses below sup this bar
const myLongSignal = for_every(close, myRes, shift(close, 1), shift(myRes, 1), myEma9, myEma20,
	(_c, _r, _pc, _pr, _e9, _e20) => {
		const myCrossOver = _pc !== null && _pr !== null && _pc <= _pr && _c > _r;
		return myCrossOver && _e9 > _e20;
	});

const myShortSignal = for_every(close, mySup, shift(close, 1), shift(mySup, 1), myEma9, myEma20,
	(_c, _s, _pc, _ps, _e9, _e20) => {
		const myCrossUnder = _pc !== null && _ps !== null && _pc >= _ps && _c < _s;
		return myCrossUnder && _e9 < _e20;
	});

// ─── VISUAL SIGNALS (plotshape equivalent) ────────────────────────────────────
const myLongMarks = for_every(myLongSignal, _l => _l ? constants.icons.triangle_up : null);
const myShortMarks = for_every(myShortSignal, _s => _s ? constants.icons.triangle_down : null);

paint(myLongMarks, { name: 'LongEntry', style: 'labels_below', color: 'green' });
paint(myShortMarks, { name: 'ShortEntry', style: 'labels_above', color: 'red' });

// ─── SIGNALS FOR SCANNER/ALERTS/STRATEGY ──────────────────────────────────────
register_signal(myLongSignal, 'Long Signal');
register_signal(myShortSignal, 'Short Signal');