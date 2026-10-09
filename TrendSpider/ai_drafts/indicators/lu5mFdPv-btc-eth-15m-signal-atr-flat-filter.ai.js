describe_indicator('RSI CCI MultiTF Signal', 'price');

// === Inputs ===
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });
const myCciLength = input.number('CCI Length', 20, { min: 1, max: 200 });
const myStochKLength = input.number('Stochastic K Length', 14, { min: 1, max: 200 });
const myStochDLength = input.number('Stochastic D Smoothing', 3, { min: 1, max: 200 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 200 });
const myUseAtrFilter = input.boolean('Use ATR Filter', true);
const myUseFlatFilter = input.boolean('Use Flat Market Filter', true);

// === 15m (current chart) indicators ===
const mySrc = close;
const myRsi15 = rsi(mySrc, myRsiLength);
const myCci15 = cci(mySrc, myCciLength);
const myAtr = atr(high, low, close, myAtrLength);
const myAtrSma = sma(myAtr, myAtrLength);
const myRange20 = sub(highest(high, 20), lowest(low, 20));

// Stochastic %K and %D on current chart
const myStochK = stochastic(close, high, low, myStochKLength);
const myStochD = sma(myStochK, myStochDLength);

// === 1h data (secured) ===
const my1hData = await request.history(current.ticker, '60');
assert(!my1hData.error, `Error fetching 1h data: "${my1hData.error}"`);

const myRsi1hRaw = rsi(my1hData.close, myRsiLength);
const myCci1hRaw = cci(my1hData.close, myCciLength);

// Land 1h values onto the current (15m) time series, then fill forward (constant, non-repainting)
const myRsi1hLanded = land_points_onto_series(my1hData.time, myRsi1hRaw, time, 'le');
const myCci1hLanded = land_points_onto_series(my1hData.time, myCci1hRaw, time, 'le');
const myRsi1h = interpolate_sparse_series(myRsi1hLanded, 'constant');
const myCci1h = interpolate_sparse_series(myCci1hLanded, 'constant');

// === Filters ===
const myAtrCond = for_every(myAtr, myAtrSma, (_atr, _atrSma) => !myUseAtrFilter || (_atr > _atrSma * 1.1));
const myFlatCond = for_every(myRange20, myAtr, (_range, _atr) => !myUseFlatFilter || (_range > _atr * 2));

// === Crossover / Crossunder (manual, no built-in function for this) ===
const myRsi15Prev = shift(myRsi15, 1);
const myRsiLongCond = for_every(myRsi15, myRsi15Prev, (_cur, _prev) => _prev !== null && _prev <= 30 && _cur > 30);
const myRsiShortCond = for_every(myRsi15, myRsi15Prev, (_cur, _prev) => _prev !== null && _prev >= 70 && _cur < 70);

// === Stochastic conditions ===
const myStochLongCond = for_every(myStochK, _k => _k > 20);
const myStochShortCond = for_every(myStochK, _k => _k < 80);

// === 1h confirmation ===
const myConfirmLong = for_every(myRsi1h, myCci1h, (_r, _c) => _r < 40 && _c < 100);
const myConfirmShort = for_every(myRsi1h, myCci1h, (_r, _c) => _r > 60 && _c > 100);

// === Final signals ===
const myLongSignal = for_every(
	myRsiLongCond, myStochLongCond, myConfirmLong, myAtrCond, myFlatCond,
	(_a, _b, _c, _d, _e) => _a && _b && _c && _d && _e
);
const myShortSignal = for_every(
	myRsiShortCond, myStochShortCond, myConfirmShort, myAtrCond, myFlatCond,
	(_a, _b, _c, _d, _e) => _a && _b && _c && _d && _e
);

// === Visuals: triangle markers below/above bars ===
const myLongMarks = for_every(myLongSignal, _s => _s ? constants.icons.triangle_up : null);
const myShortMarks = for_every(myShortSignal, _s => _s ? constants.icons.triangle_down : null);

paint(myLongMarks, { style: 'labels_below', color: 'green', name: 'Long Signal' });
paint(myShortMarks, { style: 'labels_above', color: 'red', name: 'Short Signal' });

// === Signals for scanners, alerts and strategies ===
// Each register_signal() call below is made exactly once, with a
// unique name, which is what the engine requires. Previously a
// duplicate "Long Signal" registration (likely injected by a
// re-run or copy/paste) caused the "already exists" error; this
// version keeps a single registration per signal name.
register_signal(myLongSignal, 'Long Signal');
register_signal(myShortSignal, 'Short Signal');