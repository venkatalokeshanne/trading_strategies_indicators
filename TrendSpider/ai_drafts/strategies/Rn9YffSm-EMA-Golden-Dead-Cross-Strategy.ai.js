describe_indicator('EMA Golden Dead Cross', 'price');

// ── Inputs ──────────────────────────────────────────────────────────────
const myFastLen = input.number('Fast EMA Length', 50, { min: 1, max: 500 });
const mySlowLen = input.number('Slow EMA Length', 200, { min: 1, max: 500 });
const myTradeDir = input.select('Trade Direction', 'Both', ['Long Only', 'Short Only', 'Both']);

// ── EMAs ────────────────────────────────────────────────────────────────
const myFastEMA = ema(close, myFastLen);
const mySlowEMA = ema(close, mySlowLen);

paint(myFastEMA, { name: 'FastEMA', color: 'orange', thickness: 2 });
paint(mySlowEMA, { name: 'SlowEMA', color: 'blue', thickness: 2 });

// ── Cross Signals ─────────────────────────────────────────────────────────
// crossover: fast was <= slow previous bar, now fast > slow
// crossunder: fast was >= slow previous bar, now fast < slow
const myGoldenCross = for_every(myFastEMA, mySlowEMA, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return myFastEMA[_i - 1] <= mySlowEMA[_i - 1] && _fast > _slow;
});

const myDeadCross = for_every(myFastEMA, mySlowEMA, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return myFastEMA[_i - 1] >= mySlowEMA[_i - 1] && _fast < _slow;
});

// ── Visual Markers ──────────────────────────────────────────────────────
const myBuyMarks = for_every(myGoldenCross, _g => _g ? constants.icons.triangle_up : null);
const mySellMarks = for_every(myDeadCross, _d => _d ? constants.icons.triangle_down : null);

paint(myBuyMarks, { name: 'GoldenCross', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'DeadCross', style: 'labels_above', color: 'red' });

// ── Trend background coloring ────────────────────────────────────────────
const myInBull = for_every(myFastEMA, mySlowEMA, (_fast, _slow) => _fast > _slow);
const myCandleColors = for_every(myInBull, _bull => _bull ? 'rgba(0,180,0,0.08)' : 'rgba(255,0,0,0.08)');
color_candles(myCandleColors);

// ── Signals for scanning / alerts / strategy ───────────────────────────────
// Long entry condition (per trade direction setting)
const myLongEntry = for_every(myGoldenCross, _g => (myTradeDir === 'Long Only' || myTradeDir === 'Both') && _g);
const myShortEntry = for_every(myDeadCross, _d => (myTradeDir === 'Short Only' || myTradeDir === 'Both') && _d);

// Exit signals: close short on golden cross, close long on dead cross
const myLongExit = for_every(myDeadCross, _d => (myTradeDir === 'Short Only' || myTradeDir === 'Both') && _d);
const myShortExit = for_every(myGoldenCross, _g => (myTradeDir === 'Long Only' || myTradeDir === 'Both') && _g);

// Signal names must be alphanumeric only (no spaces/punctuation),
// which is why they were renamed below. This also fixes the
// duplicate-signal registration error reported by the platform.
register_signal(myLongEntry, 'LongEntry');
register_signal(myShortEntry, 'ShortEntry');
register_signal(myLongExit, 'LongExit');
register_signal(myShortExit, 'ShortExit');
register_signal(myGoldenCross, 'GoldenCrossSignal');
register_signal(myDeadCross, 'DeadCrossSignal');
register_signal(myInBull, 'BullTrend');