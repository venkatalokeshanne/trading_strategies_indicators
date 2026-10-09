describe_indicator('Thermometer Oscillator', 'lower', { decimals: 0 });

// Component 1: Close vs Previous Close (+2 / 0 / -2)
const myPrevClose = shift(close, 1);
const myComp1 = for_every(close, myPrevClose, (_c, _pc) => _c > _pc ? 2 : (_c < _pc ? -2 : 0));

// Component 2: Close vs Today's Open (+2 / 0 / -2)
const myComp2 = for_every(close, open, (_c, _o) => _c > _o ? 2 : (_c < _o ? -2 : 0));

// Component 3: Today's range vs Previous Close (+1 / 0 / -1)
const myComp3 = for_every(low, high, myPrevClose, (_l, _h, _pc) => _l > _pc ? 1 : (_h < _pc ? -1 : 0));

// Thermometer value, range -5 to +5
const myThermo = for_every(myComp1, myComp2, myComp3, (_c1, _c2, _c3) => _c1 + _c2 + _c3);

// MA inputs
const myMaLength = input.number('MA Length', 9, { min: 1, max: 500 });
const myMaType = input.select('MA Type', 'EMA', ['EMA', 'SMA', 'WMA', 'RMA']);

let myMa;
if (myMaType === 'EMA') {
	myMa = ema(myThermo, myMaLength);
}
else if (myMaType === 'SMA') {
	myMa = sma(myThermo, myMaLength);
}
else if (myMaType === 'WMA') {
	myMa = wma(myThermo, myMaLength);
}
else {
	myMa = wildma(myThermo, myMaLength);
}

// Reference lines (fixed scale -5 to +5)
paint(horizontal_line(5), { name: 'Plus5', color: 'rgba(239,83,80,0.6)', style: 'dotted' });
paint(horizontal_line(3), { name: 'Plus3', color: 'rgba(239,83,80,0.3)', style: 'dotted' });
paint(horizontal_line(0), { name: 'Zero', color: 'gray', style: 'line' });
paint(horizontal_line(-3), { name: 'Minus3', color: 'rgba(38,166,154,0.3)', style: 'dotted' });
paint(horizontal_line(-5), { name: 'Minus5', color: 'rgba(38,166,154,0.6)', style: 'dotted' });

// Main lines
paint(myThermo, { name: 'Thermometer', color: '#2196f3', thickness: 2, style: 'line' });
paint(myMa, { name: 'MA', color: '#ffeb3b', thickness: 1, style: 'line' });

// Signals for scanners, alerts, strategies
const mySignalAbovePlus5 = for_every(myThermo, _t => _t >= 5);
const mySignalBelowMinus5 = for_every(myThermo, _t => _t <= -5);
const mySignalCrossAboveMa = for_every(myThermo, myMa, (_t, _m, _prev, _idx) => _idx > 0 && myThermo[_idx - 1] <= myMa[_idx - 1] && _t > _m);
const mySignalCrossBelowMa = for_every(myThermo, myMa, (_t, _m, _prev, _idx) => _idx > 0 && myThermo[_idx - 1] >= myMa[_idx - 1] && _t < _m);
const mySignalBullish = for_every(myThermo, _t => _t > 0);
const mySignalBearish = for_every(myThermo, _t => _t < 0);

register_signal(mySignalAbovePlus5, 'Thermo At Or Above Plus5');
register_signal(mySignalBelowMinus5, 'Thermo At Or Below Minus5');
register_signal(mySignalCrossAboveMa, 'Thermo Crosses Above MA');
register_signal(mySignalCrossBelowMa, 'Thermo Crosses Below MA');
register_signal(mySignalBullish, 'Thermo Bullish Positive');
register_signal(mySignalBearish, 'Thermo Bearish Negative');