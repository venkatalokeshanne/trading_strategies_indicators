describe_indicator('LinReg Scale In Strategy Signals', 'lower');

// Lookback period for the correlation (linear regression strength proxy)
const myLength = input.number('Lookback Period', 20, { min: 5, max: 500 });

// Pine's bar_index is just the candle index (0, 1, 2, ...)
const myBarIndex = close.map((_c, _i) => _i);

// ta.correlation(close, bar_index, length) -> correlation coefficient series
const myCoeff = correlation(close, myBarIndex, myLength);

// Reference levels
const myLevel25 = horizontal_line(0.25);
const myLevel50 = horizontal_line(0.50);
const myLevel75 = horizontal_line(0.75);
const myLevelZero = horizontal_line(0);

// crossover/crossunder detection against fixed levels
const myCrossUp25 = for_every(myCoeff, (_v, _p, _i) => _i > 0 && myCoeff[_i - 1] <= 0.25 && _v > 0.25);
const myCrossUp50 = for_every(myCoeff, (_v, _p, _i) => _i > 0 && myCoeff[_i - 1] <= 0.50 && _v > 0.50);
const myCrossUp75 = for_every(myCoeff, (_v, _p, _i) => _i > 0 && myCoeff[_i - 1] <= 0.75 && _v > 0.75);
const myCrossDown25 = for_every(myCoeff, (_v, _p, _i) => _i > 0 && myCoeff[_i - 1] >= 0.25 && _v < 0.25);

paint(myCoeff, { name: 'LinReg Coefficient', color: '#2962FF', thickness: 2 });
paint(myLevel75, { name: 'Level 075', color: 'green', style: 'dotted' });
paint(myLevel50, { name: 'Level 050', color: '#D4AC0D', style: 'dotted' });
paint(myLevel25, { name: 'Level 025', color: 'orange', style: 'dotted' });
paint(myLevelZero, { name: 'Zero Line', color: 'gray' });

// Entry/Exit signals for scanners, alerts and strategy tester
register_signal(myCrossUp25, 'Long Entry at 025');
register_signal(myCrossUp50, 'Long Entry at 050');
register_signal(myCrossUp75, 'Long Entry at 075');
register_signal(myCrossDown25, 'Exit Below 025');