describe_indicator('Session King ALMA Baseline', 'price');

// NOTE: This is a signal/overlay conversion of a TradingView STRATEGY script.
// TrendSpider custom indicators cannot manage simulated positions, equity,
// quantity sizing, or own order/exit state (strategy.position_size,
// strategy.equity, strategy.entry/exit are not available in Custom JS API).
// This indicator reproduces the ALMA baseline, the TTM Squeeze filter and
// the session kill-zone filter EXACTLY as formulas, and exposes Long/Short
// entry conditions as register_signal() outputs so they can be used in
// Scanners/Alerts/Strategy Tester (which handles the actual trade simulation,
// sizing and SL/TP execution). SL/TP reference levels (based on current ATR)
// are plotted as projections for visual reference only.

const myMoment = library('moment-timezone');

// ─── ALMA baseline inputs ───
const almaTab = input.tab('ALMA');
const myAlmaWindow = almaTab.number('Window', 9, { min: 2, max: 50 });
const myAlmaOffset = almaTab.number('Offset', 0.85, { min: 0, max: 1, step: 0.01 });
const myAlmaSigma = almaTab.number('Sigma', 6.0, { min: 0.5, max: 10, step: 0.1 });

// ─── TTM Squeeze inputs ───
const sqTab = input.tab('TTM Squeeze');
const mySqueezeOn = sqTab.boolean('Enable Squeeze Filter', false);
const mySqLen = sqTab.number('Length', 20, { min: 1, max: 200 });
const mySqBBMult = sqTab.number('BB Multiplier', 2.0, { min: 0.5, max: 10, step: 0.1 });
const mySqKCMult = sqTab.number('KC Multiplier', 1.5, { min: 0.5, max: 10, step: 0.1 });

// ─── Session filter inputs ───
const sessTab = input.tab('Session Filter');
const myUseLondon = sessTab.boolean('London 05:45-09:45 GMT', true);
const myUseNYAM = sessTab.boolean('NY AM 12:00-16:00 GMT', true);
const myUseNYPM = sessTab.boolean('NY PM 19:00-21:00 GMT', false);

// ─── Exits inputs ───
const exitTab = input.tab('Exits');
const myAtrLen = exitTab.number('ATR Length', 14, { min: 1, max: 100 });
const mySlMult = exitTab.number('SL ATR Multiplier', 3.0, { min: 0.5, max: 20, step: 0.1 });
const myTpMult = exitTab.number('TP ATR Multiplier (2R)', 6.0, { min: 0.5, max: 20, step: 0.1 });

// ─── ALMA baseline ───
const myAlmaLine = alma(close, myAlmaWindow, myAlmaOffset, myAlmaSigma);
const myAlmaBull = for_every(close, myAlmaLine, (_c, _a) => _a !== null && _c > _a);
const myAlmaBear = for_every(close, myAlmaLine, (_c, _a) => _a !== null && _c < _a);

// ─── TTM Squeeze ───
const mySqBasis = sma(close, mySqLen);
const mySqBBHalf = mult(stdev(close, mySqLen), mySqBBMult);
const mySqBBUpper = add(mySqBasis, mySqBBHalf);
const mySqBBLower = sub(mySqBasis, mySqBBHalf);
const mySqKCHalf = mult(atr(high, low, close, mySqLen), mySqKCMult);
const mySqKCUpper = add(mySqBasis, mySqKCHalf);
const mySqKCLower = sub(mySqBasis, mySqKCHalf);

const mySqCompressed = for_every(mySqBBUpper, mySqKCUpper, mySqBBLower, mySqKCLower,
	(_bu, _ku, _bl, _kl) => _bu <= _ku && _bl >= _kl);
const mySqueezeActive = for_every(mySqCompressed, _c => !_c);

// ─── Session kill zones (converted to Europe/London local time) ───
// Windows are evaluated against the "Europe/London" clock time, same as
// the original Pine script's timestamp("Europe/London", ...) calls.
const myInSession = time.map(_t => {
	const myLondonTime = myMoment.tz(_t * 1000, 'Europe/London');
	const myMinutesOfDay = myLondonTime.hours() * 60 + myLondonTime.minutes();

	const myLondonWin = myUseLondon && myMinutesOfDay >= (5 * 60 + 45) && myMinutesOfDay < (9 * 60 + 45);
	const myNYAMWin = myUseNYAM && myMinutesOfDay >= (12 * 60) && myMinutesOfDay < (16 * 60);
	const myNYPMWin = myUseNYPM && myMinutesOfDay >= (19 * 60) && myMinutesOfDay < (21 * 60);

	return myLondonWin || myNYAMWin || myNYPMWin;
});

// ─── ATR for exits ───
const myAtrVal = atr(high, low, close, myAtrLen);

// ─── Entry conditions ───
// Note: "strategy.position_size == 0" (no open position) cannot be
// replicated here since this indicator has no position state; that part
// of the gate is omitted. Use the Strategy Tester module to simulate the
// actual position management, sizing and exits.
const mySqGate = for_every(mySqueezeActive, _active => mySqueezeOn ? _active : true);

const myLongCond = for_every(myAlmaBull, mySqGate, myInSession, (_bull, _gate, _sess) => _bull && _gate && _sess);
const myShortCond = for_every(myAlmaBear, mySqGate, myInSession, (_bear, _gate, _sess) => _bear && _gate && _sess);

register_signal(myLongCond, 'Long Entry');
register_signal(myShortCond, 'Short Entry');

// ─── Reference SL/TP levels for last signal (visual reference only) ───
const myLongStop = for_every(close, myAtrVal, (_c, _a) => _c - mySlMult * _a);
const myLongTarget = for_every(close, myAtrVal, (_c, _a) => _c + myTpMult * _a);
const myShortStop = for_every(close, myAtrVal, (_c, _a) => _c + mySlMult * _a);
const myShortTarget = for_every(close, myAtrVal, (_c, _a) => _c - myTpMult * _a);

paint(myAlmaLine, { name: 'ALMA', color: '#2962FF', thickness: 1 });
paint(for_every(myLongCond, myLongStop, (_cond, _v) => _cond ? _v : null), { name: 'Long Stop Reference', color: '#EF5350', style: 'dotted' });
paint(for_every(myLongCond, myLongTarget, (_cond, _v) => _cond ? _v : null), { name: 'Long Target Reference', color: '#26A69A', style: 'dotted' });
paint(for_every(myShortCond, myShortStop, (_cond, _v) => _cond ? _v : null), { name: 'Short Stop Reference', color: '#EF5350', style: 'dotted' });
paint(for_every(myShortCond, myShortTarget, (_cond, _v) => _cond ? _v : null), { name: 'Short Target Reference', color: '#26A69A', style: 'dotted' });