describe_indicator('Kloom Regime Detector', 'lower');

// ── Inputs, grouped like the original Pine script ──────────────────────────
const myRegimeGroup = input.group('Regime');
const myAdxLenRow = myRegimeGroup.row();
const myAdxLen = myAdxLenRow.number('ADX length', 14, { min: 5, max: 50 });
const myAdxTrend = myAdxLenRow.number('ADX trend threshold', 22, { min: 10, max: 40 });
const myVolRow = myRegimeGroup.row();
const myVolLen = myVolRow.number('Volatility lookback (ATR%)', 20, { min: 5, max: 100 });
const myVolMult = myVolRow.number('High volatility multiplier', 1.5, { min: 1.0, max: 3.0, step: 0.1 });
const myEmaRow = myRegimeGroup.row();
const myEmaFast = myEmaRow.number('Fast trend EMA', 50, { min: 10, max: 200 });
const myEmaSlow = myEmaRow.number('Slow trend EMA', 200, { min: 50, max: 500 });

// ── ADX ──────────────────────────────────────────────────────────────────
// Using the built-in indicators.adx() which implements Wilder's RMA based
// DMI/ADX, equivalent to the manual Pine computation in the source script.
const myAdxObject = indicators.adx(myAdxLen);
const myAdx = myAdxObject.adx;

// ── Volatility state ─────────────────────────────────────────────────────
const myAtrPct = mult(div(atr(high, low, close, myVolLen), close), 100);
const myAtrPctAvg = sma(myAtrPct, myVolLen * 3);
const myHighVol = for_every(myAtrPct, myAtrPctAvg, (_atrPct, _avg) => _atrPct > _avg * myVolMult);

// ── Trend direction ──────────────────────────────────────────────────────
const myFast = ema(close, myEmaFast);
const mySlow = ema(close, myEmaSlow);
const myBullish = for_every(myFast, mySlow, (_f, _s) => _f > _s);

// ── Regime classification ────────────────────────────────────────────────
// 2 = trending bull, 1 = trending bear, 0 = range, -1 = high volatility
const myRegime = for_every(myHighVol, myAdx, myBullish, (_hv, _adx, _bull) => {
	if (_hv) return -1;
	if (_adx > myAdxTrend) return _bull ? 2 : 1;
	return 0;
});

const myRegimeColorMap = { '2': 'teal', '1': 'red', '0': 'gray', '-1': 'gold' };
const myRegimeColor = for_every(myRegime, _r => myRegimeColorMap[String(_r)]);

// ── Regime change markers ────────────────────────────────────────────────
const myRegimeChange = for_every(myRegime, (_r, _prev, _index) => {
	if (_index === 0) return null;
	return _r !== myRegime[_index - 1] ? high[_index] : null;
});

// ── Plots ────────────────────────────────────────────────────────────────
paint(myAdx, { name: 'ADX', color: 'aqua', thickness: 2 });
paint(horizontal_line(myAdxTrend), { name: 'ADX Trend Threshold', color: 'gray', style: 'dotted' });
// Renamed this painted line's name away from "Regime Change" since that
// exact name is also used below for register_signal(); the platform
// treats paint() and register_signal() output names as sharing the same
// namespace, so using the same string for both caused a
// "signal already exists" collision at script registration time.
paint(myRegimeChange, { name: 'Regime Change Marker', style: 'labels_above', color: myRegimeColor });

// Candle background/coloring equivalent approximation of bgcolor()
color_candles(myRegimeColor);

// ── Signals for scanning / alerts / strategies ──────────────────────────
register_signal(for_every(myRegime, _r => _r === 2), 'Trend Bull');
register_signal(for_every(myRegime, _r => _r === 1), 'Trend Bear');
register_signal(for_every(myRegime, _r => _r === 0), 'Range');
register_signal(for_every(myRegime, _r => _r === -1), 'High Volatility');
register_signal(for_every(myRegimeChange, _v => _v !== null), 'Regime Change');