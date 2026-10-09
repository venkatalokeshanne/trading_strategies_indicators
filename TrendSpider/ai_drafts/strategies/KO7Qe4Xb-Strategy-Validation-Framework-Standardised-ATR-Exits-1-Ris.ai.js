describe_indicator('Strategy Validation Framework ATR Exits', 'price');

// NOTE: TrendSpider Custom JS indicators cannot execute trades,
// track equity, or manage position sizing like a Pine Script
// strategy() can. This indicator reproduces the entry signal
// logic (EMA 9/21 cross) and plots the standardised ATR based
// Stop Loss / Take Profit levels that would be used by the
// strategy, and exposes signals for use in Scanners/Alerts.
// Position sizing (qty, risk %) and actual equity tracking are
// not reproducible here; use TrendSpider's Strategy Tester with
// this indicator's entry signals instead.

const myExitsTab = input.tab('Exits');
const myAtrLen = myExitsTab.number('ATR Length', 14, { min: 1, max: 200 });
const mySlMult = myExitsTab.number('SL ATR Multiplier', 3.0, { min: 0.1, max: 20, step: 0.1 });
const myTpMult = myExitsTab.number('TP ATR Multiplier', 6.0, { min: 0.1, max: 20, step: 0.1 });
const myRiskPct = myExitsTab.number('Risk Percent per Trade', 1.0, { min: 0.1, max: 100, step: 0.1 });

// Entry logic: EMA 9/21 crossover / crossunder
const myFastEma = ema(close, 9);
const mySlowEma = ema(close, 21);

const myLongCondition = for_every(myFastEma, mySlowEma, (_fast, _slow, _prev, _index) => {
	if (_index === 0) {
		return false;
	}
	return myFastEma[_index] > mySlowEma[_index] && myFastEma[_index - 1] <= mySlowEma[_index - 1];
});

const myShortCondition = for_every(myFastEma, mySlowEma, (_fast, _slow, _prev, _index) => {
	if (_index === 0) {
		return false;
	}
	return myFastEma[_index] < mySlowEma[_index] && myFastEma[_index - 1] >= mySlowEma[_index - 1];
});

// ATR for exit distance calculations
const myAtrVal = atr(high, low, close, myAtrLen);

// Minimum tick approximation (not exposed by the API), using a
// tiny fraction of price as a safe floor to avoid zero distance
const myMinTick = mult(close, 0.00001);
const mySlDistance = max_of(mult(myAtrVal, mySlMult), myMinTick);

// Theoretical quantity sizing is not computable here since there
// is no live equity tracking in a Custom JS indicator. We expose
// the risk-based distance only, for reference / scanner usage.
const myRiskDistance = mySlDistance;

// Long/Short SL and TP levels (only valid/shown on signal bars,
// since there is no persistent "position" state in an indicator)
const myLongSL = for_every(close, myAtrVal, myLongCondition, (_c, _a, _long) => _long ? _c - mySlMult * _a : null);
const myLongTP = for_every(close, myAtrVal, myLongCondition, (_c, _a, _long) => _long ? _c + myTpMult * _a : null);
const myShortSL = for_every(close, myAtrVal, myShortCondition, (_c, _a, _short) => _short ? _c + mySlMult * _a : null);
const myShortTP = for_every(close, myAtrVal, myShortCondition, (_c, _a, _short) => _short ? _c - myTpMult * _a : null);

// Plot EMAs
paint(myFastEma, { name: 'EMA Fast', color: '#26A69A', thickness: 2 });
paint(mySlowEma, { name: 'EMA Slow', color: '#EF5350', thickness: 2 });

// Plot entry markers
const myLongMarks = for_every(low, myAtrVal, myLongCondition, (_l, _a, _long) => _long ? _l - 0.5 * _a : null);
const myShortMarks = for_every(high, myAtrVal, myShortCondition, (_h, _a, _short) => _short ? _h + 0.5 * _a : null);

paint(myLongMarks, { name: 'Long Entry', color: '#26A69A', thickness: 3, style: 'dotted' });
paint(myShortMarks, { name: 'Short Entry', color: '#EF5350', thickness: 3, style: 'dotted' });

// Plot SL/TP levels (sparse, only on signal bars)
paint(myLongSL, { name: 'Long Stop Loss', color: '#FF9800', thickness: 1, style: 'dotted' });
paint(myLongTP, { name: 'Long Take Profit', color: '#4CAF50', thickness: 1, style: 'dotted' });
paint(myShortSL, { name: 'Short Stop Loss', color: '#FF9800', thickness: 1, style: 'dotted' });
paint(myShortTP, { name: 'Short Take Profit', color: '#4CAF50', thickness: 1, style: 'dotted' });

// Signals for use in Scanners/Alerts/Strategy Tester
register_signal(myLongCondition, 'Long Entry Signal');
register_signal(myShortCondition, 'Short Entry Signal');