describe_indicator('OminousLine EMAs 13 21 55 200', 'price');

// ─────────────────────────────────────
// EMA 13
// ─────────────────────────────────────
const ema13Group = input.group('EMA 13');
const myEma13Length = ema13Group.number('Length', 13, { min: 1, max: 1000 });
const myShow13 = ema13Group.boolean('Show EMA 13', true);

// ─────────────────────────────────────
// EMA 21
// ─────────────────────────────────────
const ema21Group = input.group('EMA 21');
const myEma21Length = ema21Group.number('Length', 21, { min: 1, max: 1000 });
const myShow21 = ema21Group.boolean('Show EMA 21', true);

// ─────────────────────────────────────
// EMA 55
// ─────────────────────────────────────
const ema55Group = input.group('EMA 55');
const myEma55Length = ema55Group.number('Length', 55, { min: 1, max: 1000 });
const myShow55 = ema55Group.boolean('Show EMA 55', true);

// ─────────────────────────────────────
// EMA 200
// ─────────────────────────────────────
const ema200Group = input.group('EMA 200');
const myEma200Length = ema200Group.number('Length', 200, { min: 1, max: 1000 });
const myShow200 = ema200Group.boolean('Show EMA 200', true);

// ─────────────────────────────────────
// Calculations
// ─────────────────────────────────────
const myEma13 = ema(close, myEma13Length);
const myEma21 = ema(close, myEma21Length);
const myEma55 = ema(close, myEma55Length);
const myEma200 = ema(close, myEma200Length);

// ─────────────────────────────────────
// Plots
// colors/widths are defaults only; the platform
// auto-generates color/thickness/visibility controls
// ─────────────────────────────────────
paint(myShow13 ? myEma13 : constants.empty_series, { name: 'EMA13', color: '#FF6D00', thickness: 2 });
paint(myShow21 ? myEma21 : constants.empty_series, { name: 'EMA21', color: '#00E5FF', thickness: 2 });
paint(myShow55 ? myEma55 : constants.empty_series, { name: 'EMA55', color: '#FFD740', thickness: 2 });
paint(myShow200 ? myEma200 : constants.empty_series, { name: 'EMA200', color: '#B388FF', thickness: 3 });

// ─────────────────────────────────────
// Signals for scanners, alerts and strategy tester
// Common crossover signals derived from the EMAs
// ─────────────────────────────────────
const myEma13CrossAboveEma21 = for_every(myEma13, myEma21, (_a, _b, _prev, _i) => _i > 0 && myEma13[_i - 1] <= myEma21[_i - 1] && _a > _b);
const myEma13CrossBelowEma21 = for_every(myEma13, myEma21, (_a, _b, _prev, _i) => _i > 0 && myEma13[_i - 1] >= myEma21[_i - 1] && _a < _b);
const myCloseAboveEma200 = for_every(close, myEma200, (_c, _e) => _c > _e);
const myCloseBelowEma200 = for_every(close, myEma200, (_c, _e) => _c < _e);

register_signal(myEma13CrossAboveEma21, 'EMA13 Cross Above EMA21');
register_signal(myEma13CrossBelowEma21, 'EMA13 Cross Below EMA21');
register_signal(myCloseAboveEma200, 'Close Above EMA200');
register_signal(myCloseBelowEma200, 'Close Below EMA200');