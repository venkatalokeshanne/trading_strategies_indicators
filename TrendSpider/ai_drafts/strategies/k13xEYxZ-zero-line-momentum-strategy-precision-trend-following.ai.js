describe_indicator('Zero Line Momentum Strategy', 'lower');

// Replicates the Pine Script "Zero Line Momentum Strategy" logic.
// ema200 is plotted on price axis (forced), wt1 is the lower oscillator.
const myLength = input.number('WT Length', 9, { min: 1, max: 100 });
const myAvgLength = input.number('WT Average Length', 12, { min: 1, max: 100 });
const myEmaLength = input.number('Trend EMA Length', 200, { min: 1, max: 1000 });

const myEma200 = ema(close, myEmaLength);

const myEsa = ema(close, myLength);
const myAbsDiff = for_every(close, myEsa, (_c, _e) => Math.abs(_c - _e));
const myD = ema(myAbsDiff, myLength);

// ci = (close - esa) / (0.015 * d)
const myCi = for_every(close, myEsa, myD, (_c, _e, _d) => {
	const myDenom = 0.015 * _d;
	return myDenom !== 0 ? (_c - _e) / myDenom : 0;
});

const myWt1 = ema(myCi, myAvgLength);
const myWt1Prev = shift(myWt1, 1);

// crossover(wt1, 0): wt1 crosses above zero
const myCrossover = for_every(myWt1, myWt1Prev, (_w, _wp) => _wp <= 0 && _w > 0);
// crossunder(wt1, 0): wt1 crosses below zero
const myCrossunder = for_every(myWt1, myWt1Prev, (_w, _wp) => _wp >= 0 && _w < 0);

const myLongCondition = for_every(close, myEma200, myCrossover, (_c, _e, _co) => _c > _e && _co);
const myShortCondition = for_every(close, myEma200, myCrossunder, (_c, _e, _cu) => _c < _e && _cu);

// Price axis line (forced, since this is a lower indicator)
paint(myEma200, { name: 'EMA200', color: '#FFA726', thickness: 2, forceUsePriceAxis: true });

// Zero Line Momentum oscillator
paint(myWt1, { name: 'WT1', color: '#42A5F5', thickness: 2 });
paint(horizontal_line(0), { name: 'ZeroLine', color: 'gray', thickness: 1, style: 'dotted' });

// Signal markers on the oscillator panel
const myLongMarks = for_every(myWt1, myLongCondition, (_w, _l) => _l ? _w : null);
const myShortMarks = for_every(myWt1, myShortCondition, (_w, _s) => _s ? _w : null);

paint(myLongMarks, { name: 'LongSignal', color: '#26A69A', style: 'labels_below', thickness: 3 });
paint(myShortMarks, { name: 'ShortSignal', color: '#EF5350', style: 'labels_above', thickness: 3 });

// Signals usable in scanners, alerts and strategy tester
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');