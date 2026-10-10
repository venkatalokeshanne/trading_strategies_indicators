describe_indicator('Qing LRC + S/R + EMA (Trend Cross Logic)', 'price');

// This indicator reproduces the Pine strategy logic as closely as the
// TrendSpider engine allows. Pivot S/R are shown as sparse dotted markers
// (not as extending ray lines with text labels), since built-in line()/label
// calls cannot be issued dynamically inside loops on this platform.

const myLrcLen = input.number('LRC Length', 20, { min: 1, max: 500 });
const myLrcUpperMult = input.number('Upper Multiplier', 1.618, { min: 0, max: 10, step: 0.001 });
const myLrcLowerMult = input.number('Lower Multiplier', 1.618, { min: 0, max: 10, step: 0.001 });
const myLeftBars = input.number('Pivot Left Bars', 5, { min: 1, max: 100 });
const myRightBars = input.number('Pivot Right Bars', 5, { min: 1, max: 100 });

// 1. LRC calculations
const myLrcMid = linreg(close, myLrcLen);
const myLrcDev = stdev(close, myLrcLen);
const myUpperChannel = add(myLrcMid, mult(myLrcDev, myLrcUpperMult));
const myLowerChannel = sub(myLrcMid, mult(myLrcDev, myLrcLowerMult));

// 2. EMA 20 and trend filter
const myEma20 = ema(close, 20);
const myLrcUpperAboveEma = for_every(myUpperChannel, myEma20, (_u, _e) => _u > _e);
const myLrcLowerBelowEma = for_every(myLowerChannel, myEma20, (_l, _e) => _l < _e);

// 3. Support & resistance (Williams pivots, matches ta.pivothigh/pivotlow)
const myPivotHigh = pivot_high(high, myLeftBars, myRightBars);
const myPivotLow = pivot_low(low, myLeftBars, myRightBars);

// var float lastS persisted forward from the last pivot low
const myLastSupport = for_every(myPivotLow, (_p, _prev) => (_p !== null && _p !== undefined) ? _p : (_prev === undefined ? null : _prev));
const myNearSupport = for_every(low, myLastSupport, (_low, _s) => _s !== null && _low <= _s * 1.02);

// 4. Buy / exit conditions
const myBuyCondition = for_every(
	myLrcUpperAboveEma, low, myLowerChannel, myNearSupport, close, open,
	(_ua, _low, _lc, _ns, _c, _o) => _ua && (_low <= _lc || _ns) && _c > _o
);

const myExitCondition = for_every(
	myLrcLowerBelowEma, high, myUpperChannel,
	(_lb, _high, _uc) => _lb || _high >= _uc
);

// Simulate strategy.opentrades == 0 / position_size > 0 as a position state machine
const myPositionState = for_every(myBuyCondition, myExitCondition, (_buy, _exit, _prev, _idx) => {
	let myPos = _idx === 0 ? 0 : (_prev === undefined || _prev === null ? 0 : _prev);
	if (_exit && myPos > 0) {
		myPos = 0;
	}
	if (_buy && myPos === 0) {
		myPos = 1;
	}
	return myPos;
});

const myPositionStatePrev = shift(myPositionState, 1);
const myEntrySignal = for_every(myPositionState, myPositionStatePrev, (_p, _pp) => _p === 1 && _pp !== 1);
const myExitSignal = for_every(myPositionState, myPositionStatePrev, (_p, _pp) => _p === 0 && _pp === 1);

// Directional crosses (upperChannel vs ema20, lowerChannel vs ema20)
const myUpperPrev = shift(myUpperChannel, 1);
const myLowerPrev = shift(myLowerChannel, 1);
const myEmaPrev = shift(myEma20, 1);
const myBullishCross = for_every(myUpperChannel, myEma20, myUpperPrev, myEmaPrev, (_u, _e, _up, _ep) => _u > _e && _up <= _ep);
const myBearishCross = for_every(myLowerChannel, myEma20, myLowerPrev, myEmaPrev, (_l, _e, _lp, _ep) => _l < _e && _lp >= _ep);

// Candle background equivalent (bgcolor)
const myBgColors = for_every(myLrcUpperAboveEma, _ua => _ua ? 'rgba(0,255,0,0.05)' : 'rgba(255,0,0,0.05)');
color_candles(myBgColors);

// Paint EMA and LRC channel
paint(myEma20, { name: 'Trend EMA', color: '#FFD54F', thickness: 2 });
paint(myLrcMid, { name: 'LRC Mid', color: '#BDBDBD', thickness: 1, style: 'dotted' });
const myUpperLinePainted = paint(myUpperChannel, { name: 'LRC Upper', color: '#2962FF', thickness: 1 });
const myLowerLinePainted = paint(myLowerChannel, { name: 'LRC Lower', color: '#EF5350', thickness: 1 });
fill(myUpperLinePainted, myLowerLinePainted, '#2962FF', 0.05);

// Pivot S/R points as sparse markers
paint(myPivotHigh, { name: 'Pivot Resistance', style: 'labels_above', color: '#EF5350' });
paint(myPivotLow, { name: 'Pivot Support', style: 'labels_below', color: '#26A69A' });

// Buy / exit markers
const myBuyMarks = for_every(myEntrySignal, low, (_sig, _low) => _sig ? _low : null);
const mySellMarks = for_every(myExitSignal, high, (_sig, _high) => _sig ? _high : null);
paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: '#EF5350' });

// Trend cross arrows
const myBullMarks = for_every(myBullishCross, low, (_sig, _low) => _sig ? _low : null);
const myBearMarks = for_every(myBearishCross, high, (_sig, _high) => _sig ? _high : null);
paint(myBullMarks, { name: 'Trend Bullish Cross Marker', style: 'labels_below', color: '#2962FF' });
paint(myBearMarks, { name: 'Trend Bearish Cross Marker', style: 'labels_above', color: '#EF5350' });

// Signals for scanner/alerts/strategy tester
// Names here were made distinct from the paint() line names above, since
// paint() and register_signal() output names must be unique across the
// whole indicator, which was the cause of the reported error.
register_signal(myEntrySignal, 'Buy Entry Signal');
register_signal(myExitSignal, 'Sell Exit Signal');
register_signal(myBullishCross, 'Trend Bullish Cross Signal');
register_signal(myBearishCross, 'Trend Bearish Cross Signal');