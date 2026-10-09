describe_indicator('Trend Efficiency Framework', 'lower');

// ───── Inputs ─────
const tabTrend = input.tab('Trend');
const myFastLen = tabTrend.number('Fast EMA', 20, { min: 1, max: 500 });
const mySlowLen = tabTrend.number('Slow EMA', 50, { min: 1, max: 500 });

const tabEff = input.tab('Efficiency');
const myLookback = tabEff.number('Efficiency Lookback', 20, { min: 1, max: 500 });
const myEffThreshold = tabEff.number('Efficiency Threshold', 0.55, { min: 0, max: 1, step: 0.05 });

const tabRisk = input.tab('Risk');
const myAtrLen = tabRisk.number('ATR Length', 14, { min: 1, max: 500 });
const myAtrMult = tabRisk.number('ATR Stop Multiplier', 1.5, { min: 0.1, max: 10, step: 0.1 });
const myRR = tabRisk.number('Risk Reward', 2.0, { min: 0.1, max: 10, step: 0.1 });

// ───── Trend ─────
const myFastEMA = ema(close, myFastLen);
const mySlowEMA = ema(close, mySlowLen);
const myBullTrend = for_every(myFastEMA, mySlowEMA, (_f, _s) => _f > _s);
const myBearTrend = for_every(myFastEMA, mySlowEMA, (_f, _s) => _f < _s);

// ───── Trend Efficiency ─────
// netMove = |close - close[lookback]|
const myNetMove = for_every(close, shift(close, myLookback), (_c, _cLag) => Math.abs(_c - _cLag));
// totalMove = sum of |close[i] - close[i+1]| over the lookback window
const myBarMove = for_every(close, shift(close, 1), (_c, _cPrev) => Math.abs(_c - _cPrev));
const myTotalMove = sum(myBarMove, myLookback);
const myEfficiency = for_every(myNetMove, myTotalMove, (_net, _total) => _total !== 0 ? _net / _total : 0);

// ───── Entry Conditions ─────
const myLongCondition = for_every(myBullTrend, myEfficiency, (_bull, _eff) => _bull && _eff > myEffThreshold);
const myShortCondition = for_every(myBearTrend, myEfficiency, (_bear, _eff) => _bear && _eff > myEffThreshold);

// ───── Risk Management ─────
const myAtrValue = atr(high, low, close, myAtrLen);

// NOTE: the Custom JS API has no strategy engine (no strategy.entry/exit,
// position sizing or order simulation). The block below approximates a
// single-position simulation (long/short, reversing on opposite signal)
// purely for visualization of stop/target levels. It is NOT a real
// backtest and does not reflect actual fills, slippage or equity.
//
// FIX: `for_every`'s "previous value" argument is `null` for the very
// first candle AND can also be `null` for subsequent candles since this
// is the actual output we return (an object). The original code assumed
// `_prev` would always be falsy-checked correctly, but once a real state
// object had been returned, `_prev` is never null again, so that wasn't
// actually the source of the crash. The real crash happened afterwards,
// in `myPositionState.map(...)`, because `for_every` can still yield a
// `null` entry if the engine ever skips a candle (e.g. missing/undefined
// input values upstream), and `.pos` was read directly on that `null`
// without a guard. Added defensive guards both in the reducer and in all
// `.map()` calls below so `null` state entries can never crash the script.
const myPositionState = for_every(myLongCondition, myShortCondition, close, (_long, _short, _close, _prev) => {
	const myState = _prev && typeof _prev === 'object' ? _prev : { pos: 0, entry: 0 };
	let myPos = myState.pos;
	let myEntry = myState.entry;

	if (_long && myPos <= 0) {
		myPos = 1;
		myEntry = _close;
	}
	else if (_short && myPos >= 0) {
		myPos = -1;
		myEntry = _close;
	}

	return { pos: myPos, entry: myEntry };
});

const myLongStop = myPositionState.map((_state, _index) => (_state && _state.pos === 1) ? _state.entry - myAtrValue[_index] * myAtrMult : null);
const myLongTarget = myPositionState.map((_state, _index) => (_state && _state.pos === 1) ? _state.entry + myAtrValue[_index] * myAtrMult * myRR : null);
const myShortStop = myPositionState.map((_state, _index) => (_state && _state.pos === -1) ? _state.entry + myAtrValue[_index] * myAtrMult : null);
const myShortTarget = myPositionState.map((_state, _index) => (_state && _state.pos === -1) ? _state.entry - myAtrValue[_index] * myAtrMult * myRR : null);

// ───── Signals (for Scanner, Alerts, Strategy Tester) ─────
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');

// ───── Visuals ─────
paint(myFastEMA, { name: 'Fast EMA', color: 'orange', thickness: 2, forceUsePriceAxis: true });
paint(mySlowEMA, { name: 'Slow EMA', color: 'blue', thickness: 2, forceUsePriceAxis: true });
paint(myEfficiency, { name: 'Trend Efficiency', color: 'green', thickness: 2 });
paint(horizontal_line(myEffThreshold), { name: 'Efficiency Threshold', color: 'gray', style: 'dotted' });
paint(myLongStop, { name: 'Long Stop', color: 'red', style: 'dotted', forceUsePriceAxis: true });
paint(myLongTarget, { name: 'Long Target', color: 'teal', style: 'dotted', forceUsePriceAxis: true });
paint(myShortStop, { name: 'Short Stop', color: 'red', style: 'dotted', forceUsePriceAxis: true });
paint(myShortTarget, { name: 'Short Target', color: 'teal', style: 'dotted', forceUsePriceAxis: true });