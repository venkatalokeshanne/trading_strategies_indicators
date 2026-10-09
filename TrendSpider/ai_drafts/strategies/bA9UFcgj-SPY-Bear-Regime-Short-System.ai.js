describe_indicator('SPY Bear Regime Short System', 'lower');

// NOTE: TrendSpider Custom JS has no notion of "process orders on next bar
// open" like Pine strategies do. This indicator evaluates entry/exit
// conditions and simulated position state on each candle's close, so
// signal bars match the Pine conditions, but order fills are modeled as
// happening on the same bar's close (an approximation of Pine's "next
// bar open" fill behavior).

const myMaLongLen = input.number('Long MA length', 250, { min: 1, max: 1000 });
const myMaShortLen = input.number('Short MA length', 5, { min: 1, max: 200 });
const myRsiLen = input.number('RSI length', 3, { min: 1, max: 100 });
const myRsiThresh = input.number('RSI overbought', 70, { min: 50, max: 100 });
const myGapPct = input.number('Min % below long MA', 2, { min: 0, max: 50 });

const myMaLong = sma(close, myMaLongLen);
const myMaShort = sma(close, myMaShortLen);
const myRsi = rsi(close, myRsiLen);

const myBelowLongMa = for_every(close, myMaLong, (_c, _ml) => _c < _ml);
const myAboveShortMa = for_every(close, myMaShort, (_c, _ms) => _c > _ms);

// RSI crossing over the overbought threshold (ta.crossover equivalent)
const myRsiPrev = shift(myRsi, 1);
const myRsiCrossOb = for_every(myRsi, myRsiPrev, (_r, _rp) => {
	if (_rp === null || _r === null) return false;
	return _r > myRsiThresh && _rp <= myRsiThresh;
});

const myGapOk = for_every(close, myMaLong, (_c, _ml) => _c <= _ml * (1 - myGapPct / 100));

const myEntrySignal = for_every(myBelowLongMa, myAboveShortMa, myRsiCrossOb, myGapOk, (_b, _a, _rc, _g) => _b && _a && _rc && _g);

const myExitBelowShort = for_every(close, myMaShort, (_c, _ms) => _c < _ms);
const myExitAboveLong = for_every(close, myMaLong, (_c, _ml) => _c > _ml);
const myExitSignal = for_every(myExitBelowShort, myExitAboveLong, (_eb, _ea) => _eb || _ea);

// Sequentially track simulated position state: 0 = flat, -1 = short.
const myPositionState = for_every(myEntrySignal, myExitSignal, (_en, _ex, _prevPos, _idx) => {
	const myPrev = _prevPos === null || _prevPos === undefined ? 0 : _prevPos;
	let myPos = myPrev;
	if (_en && myPrev === 0) {
		myPos = -1;
	}
	else if (_ex && myPrev < 0) {
		myPos = 0;
	}
	return myPos;
});

const myPrevPositionState = shift(myPositionState, 1);

const myEntryFires = for_every(myEntrySignal, myPrevPositionState, (_en, _pp) => {
	const myPrev = _pp === null || _pp === undefined ? 0 : _pp;
	return _en && myPrev === 0;
});

const myExitFires = for_every(myExitSignal, myPrevPositionState, (_ex, _pp) => {
	const myPrev = _pp === null || _pp === undefined ? 0 : _pp;
	return _ex && myPrev < 0;
});

// Markers
const myEntryMarker = for_every(myEntryFires, _en => _en ? constants.icons.triangle_down : null);
const myExitMarker = for_every(myExitFires, _ex => _ex ? constants.icons.triangle_up : null);

// Price-axis moving averages
paint(myMaLong, { name: 'Long MA', color: 'yellow', thickness: 2, forceUsePriceAxis: true });
paint(myMaShort, { name: 'Short MA', color: 'white', thickness: 2, forceUsePriceAxis: true });

// RSI panel
paint(myRsi, { name: 'RSI', color: 'white', thickness: 3 });
paint(horizontal_line(myRsiThresh), { name: 'Overbought', color: '#ff4444', style: 'dotted' });
paint(horizontal_line(50), { name: 'Midline', color: 'gray', style: 'dotted' });
paint(horizontal_line(30), { name: 'Oversold', color: '#00e676', style: 'dotted' });

// Entry and exit markers
paint(myEntryMarker, { name: 'ShortEntry', style: 'labels_above', color: '#ff4444' });
paint(myExitMarker, { name: 'ShortExit', style: 'labels_below', color: '#00e676' });

register_signal(myEntryFires, 'Short Entry');
register_signal(myExitFires, 'Short Exit');