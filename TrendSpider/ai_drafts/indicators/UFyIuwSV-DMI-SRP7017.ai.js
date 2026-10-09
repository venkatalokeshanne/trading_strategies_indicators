describe_indicator('DMI Dynamic', 'lower', { decimals: 4 });

const myAdxLen = input.number('ADX Smoothing', 14, { min: 1, max: 100 });
const myDiLen = input.number('DI Length', 28, { min: 1, max: 100 });

// True Range based smoothed value (Wilder's RMA equivalent to ta.rma(ta.tr, diLen))
const myTrur = atr(high, low, close, myDiLen);

// Directional movement components, replicating ta.change(high) and -ta.change(low)
const myUp = sub(high, shift(high, 1));
const myDown = sub(shift(low, 1), low);

const myPlusDM = for_every(myUp, myDown, (_up, _down) => (_up === null || _down === null) ? null : (_up > _down && _up > 0 ? _up : 0));
const myMinusDM = for_every(myUp, myDown, (_up, _down) => (_up === null || _down === null) ? null : (_down > _up && _down > 0 ? _down : 0));

// Wilder's smoothing (RMA) of the DM series
const myPlusSmoothed = wildma(myPlusDM, myDiLen);
const myMinusSmoothed = wildma(myMinusDM, myDiLen);

// Raw plus/minus DI before fixnan treatment
const myPlusRaw = for_every(myPlusSmoothed, myTrur, (_p, _t) => (_t === null || _t === 0) ? null : (100 * _p / _t));
const myMinusRaw = for_every(myMinusSmoothed, myTrur, (_m, _t) => (_t === null || _t === 0) ? null : (100 * _m / _t));

// fixnan(): carry forward the last valid (non-null) value
const myPlus = for_every(myPlusRaw, (_v, _prev) => (_v === null || isNaN(_v)) ? (_prev === undefined ? null : _prev) : _v);
const myMinus = for_every(myMinusRaw, (_v, _prev) => (_v === null || isNaN(_v)) ? (_prev === undefined ? null : _prev) : _v);

// ADX calculation
const mySum = add(myPlus, myMinus);
const myDxInput = for_every(myPlus, myMinus, mySum, (_p, _m, _s) => Math.abs(_p - _m) / (_s === 0 ? 1 : _s));
const myAdx = mult(wildma(myDxInput, myAdxLen), 100);

// Dynamic colors based on current value vs previous bar
const myPlusShifted = shift(myPlus, 1);
const myMinusShifted = shift(myMinus, 1);
const myAdxShifted = shift(myAdx, 1);

const myColorPlus = for_every(myPlus, myPlusShifted, (_v, _prev) => (_prev !== null && _v > _prev) ? '#00ff00' : '#006400');
const myColorMinus = for_every(myMinus, myMinusShifted, (_v, _prev) => (_prev !== null && _v > _prev) ? '#ff0000' : '#800000');
const myColorAdx = for_every(myAdx, myAdxShifted, (_v, _prev) => (_prev !== null && _v > _prev) ? '#ffff00' : '#ffaa00');

paint(myAdx, { name: 'ADX Dynamic', color: myColorAdx, thickness: 3 });
paint(myPlus, { name: 'Plus DI Dynamic', color: myColorPlus, thickness: 2 });
paint(myMinus, { name: 'Minus DI Dynamic', color: myColorMinus, thickness: 2 });

paint(horizontal_line(10), { name: 'Threshold 10', color: '#00ff2f', style: 'dotted' });
paint(horizontal_line(20), { name: 'Threshold 20', color: '#f2fa00', style: 'dotted' });
paint(horizontal_line(30), { name: 'Threshold 30', color: '#ffffff', style: 'line' });

// Signals for scanners, alerts, strategies
register_signal(for_every(myPlus, myMinus, (_p, _m) => _p > _m), 'Plus DI Above Minus DI');
register_signal(for_every(myPlus, myMinus, (_p, _m) => _m > _p), 'Minus DI Above Plus DI');
register_signal(for_every(myAdx, _a => _a > 20), 'ADX Above 20');
register_signal(for_every(myAdx, _a => _a > 30), 'ADX Above 30');
register_signal(for_every(myAdx, myAdxShifted, (_v, _prev) => _prev !== null && _v > _prev), 'ADX Rising');