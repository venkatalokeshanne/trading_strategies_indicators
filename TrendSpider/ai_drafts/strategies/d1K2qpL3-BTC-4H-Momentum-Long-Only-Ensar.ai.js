describe_indicator('BTC 4H Momentum Long Only Ensar', 'price');

// ─── Inputs ──────────────────────────────────────────────────────────
const myTab = input.tab('Settings');
const myRocRow = myTab.row();
const myRocLen = myRocRow.number('ROC Length', 20, { min: 5, max: 500 });
const myRocThr = myRocRow.number('ROC Threshold Percent', 1.0, { min: 0.1, max: 100 });
const myTrendRow = myTab.row();
const myEmaLen = myTrendRow.number('EMA Length Trend', 200, { min: 50, max: 1000 });
const myEmaDirBars = myTrendRow.number('EMA Direction Bars', 10, { min: 3, max: 200 });
const mySwingRow = myTab.row();
const mySwingLb = mySwingRow.number('Swing Lookback', 7, { min: 3, max: 200 });
const myRrTarget = mySwingRow.number('RR Target', 3.0, { min: 1.0, max: 50 });
const myAdxRow = myTab.row();
const myAdxLen = myAdxRow.number('ADX Length', 14, { min: 5, max: 200 });
const myAdxThr = myAdxRow.number('ADX Threshold', 20, { min: 10, max: 100 });

// ─── Core math ───────────────────────────────────────────────────────
const myEma200 = ema(close, myEmaLen);
const myRoc = mult(div(sub(close, shift(close, myRocLen)), shift(close, myRocLen)), 100);
const mySwingLow = lowest(low, mySwingLb);

// Pine's ta.dmi(len, len) is equivalent to our ADX computation with a single length
const myAdxObject = indicators.adx(myAdxLen);
const myEmaRising = for_every(myEma200, shift(myEma200, myEmaDirBars), (_e, _ePrev) => _e > _ePrev);

// long_cond = close > ema200 and ema_rising and roc > roc_thr and adx > adx_thr
const myLongCond = for_every(
	close, myEma200, myEmaRising, myRoc, myAdxObject.adx,
	(_c, _e, _rising, _roc, _adx) => _c > _e && _rising && _roc > myRocThr && _adx > myAdxThr
);

// NOTE: Pine's "no_pos" depends on live strategy.position_size, which this
// scripting engine has no equivalent for (no strategy/position simulation
// is available in Custom JS indicators). We approximate "no_pos" by only
// firing the signal on bars where long_cond just turned true (i.e. it was
// false on the previous bar), which prevents the same signal from firing
// on every consecutive bar while the condition remains true.
const myLongSignal = for_every(myLongCond, shift(myLongCond, 1), (_cur, _prev) => _cur && !_prev);

// Stop/target levels, computed only on signal bars (purely informational,
// no actual strategy entries/exits are simulated)
const mySl = for_every(myLongSignal, mySwingLow, (_sig, _sl) => _sig ? _sl : null);
const myTp = for_every(myLongSignal, close, mySwingLow, (_sig, _c, _sl) => _sig ? _c + (_c - _sl) * myRrTarget : null);

// ─── Painting ────────────────────────────────────────────────────────
paint(myEma200, { name: 'EMA200', color: '#FF9800', thickness: 2 });

const myLongMarks = for_every(myLongSignal, low, (_sig, _low) => _sig ? _low * 0.995 : null);
// Renamed the painted line to a distinct name from the registered
// signal below, since both names clashed and caused a duplicate
// registration error.
paint(myLongMarks, { name: 'LongMark', style: 'labels_below', color: '#3FB950' });
paint(myTp, { name: 'TargetLevel', style: 'line', color: '#2196F3', thickness: 1 });
paint(mySl, { name: 'StopLevel', style: 'line', color: '#EF5350', thickness: 1 });

// ─── Signal for scanners, alerts, strategy tester ───────────────────
register_signal(myLongSignal, 'LongSignal');