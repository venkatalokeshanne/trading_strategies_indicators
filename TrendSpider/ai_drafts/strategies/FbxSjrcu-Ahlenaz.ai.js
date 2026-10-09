describe_indicator('XRP Price Action and Volume Strategy', 'price');

// Inputs matching the Pine Script version
const myTab = input.tab('Settings');

const myEmaRow = myTab.row();
const myFastEMALength = myEmaRow.number('Fast EMA', 50, { min: 1, max: 500 });
const mySlowEMALength = myEmaRow.number('Slow EMA', 200, { min: 1, max: 500 });

const myVolRow = myTab.row();
const myVolLength = myVolRow.number('Volume SMA Length', 20, { min: 1, max: 500 });
const myBreakoutLookback = myVolRow.number('Resistance Lookback', 20, { min: 1, max: 500 });

const myRiskATRMult = myTab.number('ATR Stop Multiplier', 1.5, { min: 0.1, max: 10, step: 0.1 });

// Core indicators
const myEmaFast = ema(close, myFastEMALength);
const myEmaSlow = ema(close, mySlowEMALength);
const myVolMA = sma(volume, myVolLength);

// Pine's ta.highest/ta.lowest over "breakoutLookback" bars, then shifted
// by 1 bar (the [1] in Pine) to use the previous bar's resistance/support
const myHighResistance = shift(highest(high, myBreakoutLookback), 1);
const myLowSupport = shift(lowest(low, myBreakoutLookback), 1);

const myAtr = atr(high, low, close, 14);

// Trend filter
const myBullTrend = for_every(myEmaFast, myEmaSlow, (_f, _s) => _f > _s);
const myBearTrend = for_every(myEmaFast, myEmaSlow, (_f, _s) => _f < _s);

// Price action + volume conditions
const myBullBreakout = for_every(close, myHighResistance, open, volume, myVolMA,
	(_c, _hr, _o, _v, _vma) => _hr != null && _c > _hr && _c > _o && _v > _vma * 1.5);

const myBearBreakdown = for_every(close, myLowSupport, open, volume, myVolMA,
	(_c, _ls, _o, _v, _vma) => _ls != null && _c < _ls && _c < _o && _v > _vma * 1.5);

// Entry signals
const myBuySignal = for_every(myBullTrend, myBullBreakout, (_bt, _bb) => _bt && _bb);
const mySellSignal = for_every(myBearTrend, myBearBreakdown, (_bt, _bb) => _bt && _bb);

// Risk management stop levels (informational, exposed as signals/levels,
// since this engine does not run strategy backtests with position management
// the same way Pine strategy.* calls do)
const myLongStop = sub(close, mult(myAtr, myRiskATRMult));
const myShortStop = add(close, mult(myAtr, myRiskATRMult));

// Visuals: EMAs
paint(myEmaFast, { name: 'Fast EMA', color: '#26A69A', thickness: 2 });
paint(myEmaSlow, { name: 'Slow EMA', color: '#EF5350', thickness: 2 });

// Buy / Sell labels, as in plotshape()
const myBuyMarks = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const mySellMarks = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: '#EF5350' });

// Stop lines, forced to price axis in case this is ever viewed as lower
paint(myLongStop, { name: 'Long Stop', color: '#4DA3FF', style: 'dotted', forceUsePriceAxis: true });
paint(myShortStop, { name: 'Short Stop', color: '#FFA726', style: 'dotted', forceUsePriceAxis: true });

// Signals for scanner/alerts/strategy tester
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');