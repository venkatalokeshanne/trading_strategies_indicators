describe_indicator('RSI Range Compression (Momentum Coil Breakout)', 'lower');

// ───────────────────────── INPUTS ─────────────────────────
const myRsiTab = input.tab('RSI Coil');
const myRsiLen = myRsiTab.number('RSI Length', 14, { min: 1, max: 200 });
const myCoilLen = myRsiTab.number('RSI Range Lookback', 20, { min: 1, max: 500 });
const myPctLen = myRsiTab.number('Percentile Lookback', 100, { min: 2, max: 1000 });
const myCoilPct = myRsiTab.number('Contraction Percentile', 20, { min: 1, max: 50 });
const myCoilMemory = myRsiTab.number('Squeeze Memory Bars', 5, { min: 0, max: 100 });

const myTrendTab = input.tab('Trend / Direction Filter');
const myEmaLen = myTrendTab.number('EMA Length', 50, { min: 1, max: 500 });
const mySlopeLen = myTrendTab.number('EMA Slope Lookback', 5, { min: 1, max: 100 });

const myFiltTab = input.tab('Optional Extra Filter');
const myUseADX = myFiltTab.boolean('Require Min ADX', true);
const myAdxLen = myFiltTab.number('ADX Length', 14, { min: 1, max: 200 });
const myAdxMin = myFiltTab.number('Minimum ADX', 15, { min: 0, max: 100 });

const myRiskTab = input.tab('Risk Management');
const myAllowLongs = myRiskTab.boolean('Allow Longs', true);
const myAllowShorts = myRiskTab.boolean('Allow Shorts', true);

// ───────────────────────── CALCULATIONS ─────────────────────────
const myRsi = rsi(close, myRsiLen);
const myRsiHigh = highest(myRsi, myCoilLen);
const myRsiLow = lowest(myRsi, myCoilLen);
const myRsiRange = sub(myRsiHigh, myRsiLow);

// Percent rank approximation: percentage of values in the trailing window
// (including current) that are lower than the current value.
const myRangePctRank = sliding_window_function(myRsiRange, myPctLen, _values => {
	const myCurrent = _values[_values.length - 1];
	const myCount = _values.filter(_v => _v < myCurrent).length;
	return (myCount / myPctLen) * 100;
});

const myIsSqueeze = for_every(myRangePctRank, _r => (_r !== null && _r <= myCoilPct));

// Bars since last squeeze (custom replacement for ta.barssince)
const myBarsSinceSqueeze = for_every(myIsSqueeze, (_sq, _prev, _i) => {
	if (_sq) return 0;
	if (_i === 0) return null;
	return (_prev === null) ? null : _prev + 1;
});

const mySqueezeRecent = for_every(myBarsSinceSqueeze, _b => (_b !== null && _b <= myCoilMemory));

const myEma = ema(close, myEmaLen);
const myEmaShifted = shift(myEma, mySlopeLen);
const myEmaSlopeUp = for_every(myEma, myEmaShifted, (_e, _es) => _e > _es);
const myEmaSlopeDown = for_every(myEma, myEmaShifted, (_e, _es) => _e < _es);

const myAdxObject = indicators.adx(myAdxLen);
const myAdxOK = for_every(myAdxObject.adx, _a => (!myUseADX || _a >= myAdxMin));

// crossover / crossunder of RSI vs its own shifted high/low band
const myRsiHighShifted = shift(myRsiHigh, 1);
const myRsiLowShifted = shift(myRsiLow, 1);
const myRsiShiftedPrev = shift(myRsi, 1);

const myCrossOver = for_every(myRsi, myRsiShiftedPrev, myRsiHighShifted, shift(myRsiHighShifted, 1),
	(_rsi, _rsiPrev, _band, _bandPrev) => (_rsi > _band && _rsiPrev <= _bandPrev));

const myCrossUnder = for_every(myRsi, myRsiShiftedPrev, myRsiLowShifted, shift(myRsiLowShifted, 1),
	(_rsi, _rsiPrev, _band, _bandPrev) => (_rsi < _band && _rsiPrev >= _bandPrev));

const myLongTrigger = for_every(myCrossOver, mySqueezeRecent, myEmaSlopeUp, myAdxOK,
	(_co, _sq, _slope, _adx) => (_co && _sq && _slope && _adx && myAllowLongs));

const myShortTrigger = for_every(myCrossUnder, mySqueezeRecent, myEmaSlopeDown, myAdxOK,
	(_cu, _sq, _slope, _adx) => (_cu && _sq && _slope && _adx && myAllowShorts));

// ───────────────────────── PAINTING ─────────────────────────
const myRsiColor = for_every(myRsi, shift(myRsi, 1), (_r, _rPrev) => (_r > _rPrev ? '#00ff88' : '#ff3366'));
const myRsiLinePainted = paint(myRsi, { name: 'RSI Core', color: myRsiColor, thickness: 2 });

paint(horizontal_line(70), { name: 'Overbought', color: 'gray', style: 'dotted', thickness: 1 });
paint(horizontal_line(50), { name: 'Midline', color: 'gray', style: 'dotted', thickness: 1 });
paint(horizontal_line(30), { name: 'Oversold', color: 'gray', style: 'dotted', thickness: 1 });

const myBandTopPainted = paint(myRsiHigh, { name: 'Coil High', color: '#4dd0e1', thickness: 1 });
const myBandBotPainted = paint(myRsiLow, { name: 'Coil Low', color: '#4dd0e1', thickness: 1 });
fill(myBandTopPainted, myBandBotPainted, '#4dd0e1', 0.15);

const myLongMarks = for_every(myLongTrigger, myRsi, (_t, _r) => (_t ? _r : null));
const myShortMarks = for_every(myShortTrigger, myRsi, (_t, _r) => (_t ? _r : null));

paint(myLongMarks, { name: 'Long Signal', style: 'labels_above', color: '#00e676', thickness: 10 });
paint(myShortMarks, { name: 'Short Signal', style: 'labels_below', color: '#ff5252', thickness: 10 });

// ───────────────────────── SIGNALS ─────────────────────────
register_signal(myLongTrigger, 'Long Breakout');
register_signal(myShortTrigger, 'Short Breakout');
register_signal(myIsSqueeze, 'Squeeze Active');