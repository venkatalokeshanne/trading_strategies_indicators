// ─────────────────────────────────────────────────────────────────────────
// This indicator reproduces the Pine Script "InvestAI - Backtest Long Short
// v3" strategy logic as closely as the TrendSpider Custom JS API allows.
// Note: TrendSpider custom indicators cannot place strategy orders
// (strategy.entry/exit, SL/TP, equity sizing). Instead we expose Long/Short
// signals (via register_signal, usable in Scanner/Alerts/Strategy Tester)
// and plot SL/TP reference levels (close -/+ ATR*mult) for the bar the
// signal fires on, so the risk management logic is still visible.
// ─────────────────────────────────────────────────────────────────────────
describe_indicator('InvestAI Long Short v3', 'price');

const myEmaTab = input.tab('EMA / RSI');
const myEmaGroup = myEmaTab.group('EMA');
const myEmaFastLen = myEmaGroup.number('EMA Fast', 9, { min: 1, max: 500 });
const myEmaSlowLen = myEmaGroup.number('EMA Slow', 21, { min: 1, max: 500 });

const myRsiGroup = myEmaTab.group('RSI');
const myRsiLen = myRsiGroup.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiOverboughtRow = myRsiGroup.row();
const myRsiOverbought = myRsiOverboughtRow.number('RSI Overbought', 70, { min: 1, max: 99 });
const myRsiOversold = myRsiOverboughtRow.number('RSI Oversold', 30, { min: 1, max: 99 });

const myRiskTab = input.tab('Risk');
const myAtrLen = myRiskTab.number('ATR Length', 14, { min: 1, max: 200 });
const myRiskRow = myRiskTab.row();
const mySlMult = myRiskRow.number('SL Multiplier (ATR)', 1.0, { min: 0.5, max: 5.0, step: 0.5 });
const myTpMult = myRiskRow.number('TP Multiplier (ATR)', 4.0, { min: 0.5, max: 10.0, step: 0.5 });

const myFiltersTab = input.tab('Filters');
const myVolRow = myFiltersTab.row();
const myUseVolFilter = myVolRow.boolean('Volume Filter', false);
const myVolMult = myVolRow.number('Volume Min vs Avg', 1.2, { min: 1.0, max: 3.0, step: 0.1 });
const myUseMacroFilter = myFiltersTab.boolean('EMA 200 Filter', false);
const myUseConfirm = myFiltersTab.boolean('Confirm On Candle Close', true);

// ── indicators ─────────────────────────────────────────────────────────
const myEFast = ema(close, myEmaFastLen);
const myESlow = ema(close, myEmaSlowLen);
const myEMacro = ema(close, 200);
const myRsi = rsi(close, myRsiLen);
const myAtr = atr(high, low, close, myAtrLen);
const myVol20 = sma(volume, 20);

// MACD(12,26,9) built manually, since there's no built-in macd() function
const myMacdLine = sub(ema(close, 12), ema(close, 26));
const mySignalLine = ema(myMacdLine, 9);
const myMacdBull = for_every(myMacdLine, mySignalLine, (_m, _s) => _m > _s);

// ── crossover / crossunder of EMAs ────────────────────────────────────
const myEFastPrev = shift(myEFast, 1);
const myESlowPrev = shift(myESlow, 1);

const myBullCross = for_every(myEFast, myESlow, myEFastPrev, myESlowPrev,
	(_f, _s, _fp, _sp) => _fp !== null && _sp !== null && _fp <= _sp && _f > _s);

const myBearCross = for_every(myEFast, myESlow, myEFastPrev, myESlowPrev,
	(_f, _s, _fp, _sp) => _fp !== null && _sp !== null && _fp >= _sp && _f < _s);

// ── filters ────────────────────────────────────────────────────────────
const myVolOk = myUseVolFilter
	? for_every(volume, myVol20, (_v, _va) => _v > _va * myVolMult)
	: for_every(close, _c => true);

const myMacroLong = myUseMacroFilter
	? for_every(close, myEMacro, (_c, _e) => _c > _e)
	: for_every(close, _c => true);

const myMacroShort = myUseMacroFilter
	? for_every(close, myEMacro, (_c, _e) => _c < _e)
	: for_every(close, _c => true);

// ── raw signals ────────────────────────────────────────────────────────
const myLongRaw = for_every(
	myBullCross, myRsi, myMacdBull, myVolOk, myMacroLong,
	(_bc, _r, _mb, _vo, _ml) => _bc && _r > myRsiOversold && _r < myRsiOverbought && _mb && _vo && _ml
);

const myShortRaw = for_every(
	myBearCross, myRsi, myMacdBull, myVolOk, myMacroShort,
	(_bec, _r, _mb, _vo, _ms) => _bec && _r < myRsiOverbought && _r > myRsiOversold && !_mb && _vo && _ms
);

// ── confirmed signals (optionally delayed by 1 bar, like `[1]` in Pine) ─
const myLongSig = myUseConfirm ? shift(myLongRaw, 1) : myLongRaw;
const myShortSig = myUseConfirm ? shift(myShortRaw, 1) : myShortRaw;

// ── reference SL/TP levels for a signal bar (informational only) ───────
const myLongStop = for_every(close, myAtr, myLongSig, (_c, _a, _s) => _s ? _c - _a * mySlMult : null);
const myLongLimit = for_every(close, myAtr, myLongSig, (_c, _a, _s) => _s ? _c + _a * myTpMult : null);
const myShortStop = for_every(close, myAtr, myShortSig, (_c, _a, _s) => _s ? _c + _a * mySlMult : null);
const myShortLimit = for_every(close, myAtr, myShortSig, (_c, _a, _s) => _s ? _c - _a * myTpMult : null);

// ── painting ───────────────────────────────────────────────────────────
const myFastLinePainted = paint(myEFast, { name: 'EMA Fast', color: '#0066ff', thickness: 1 });
const mySlowLinePainted = paint(myESlow, { name: 'EMA Slow', color: '#6d4aff', thickness: 2 });

color_cloud(myEFast, myESlow, '#00a86b', '#e63946', 'Bullish Gap', 'Bearish Gap', 0.1);

paint(myUseMacroFilter ? myEMacro : constants.empty_series, { name: 'EMA 200', color: '#f5a623', thickness: 2 });

const myLongMarks = for_every(myLongSig, low, (_s, _l) => _s ? _l : null);
const myShortMarks = for_every(myShortSig, high, (_s, _h) => _s ? _h : null);

paint(myLongMarks, { name: 'Long Signal', style: 'labels_below', color: '#00a86b' });
paint(myShortMarks, { name: 'Short Signal', style: 'labels_above', color: '#e63946' });

paint(myLongStop, { name: 'Long Stop', color: '#e63946', style: 'dotted', forceUsePriceAxis: true });
paint(myLongLimit, { name: 'Long Target', color: '#00a86b', style: 'dotted', forceUsePriceAxis: true });
paint(myShortStop, { name: 'Short Stop', color: '#e63946', style: 'dotted', forceUsePriceAxis: true });
paint(myShortLimit, { name: 'Short Target', color: '#00a86b', style: 'dotted', forceUsePriceAxis: true });

// ── signals for Scanner / Alerts / Strategy Tester ──────────────────────
register_signal(myLongSig, 'Long Entry');
register_signal(myShortSig, 'Short Entry');

// ── HUD overlay (static snapshot of the last bar) ───────────────────────
const myLastRsi = Math.round((myRsi[myRsi.length - 1] || 0) * 10) / 10;
const myLastAtr = Math.round((myAtr[myAtr.length - 1] || 0) * 100) / 100;
const myLastMacdBull = myMacdBull[myMacdBull.length - 1];
const myLastTrendUp = myEFast[myEFast.length - 1] > myESlow[myESlow.length - 1];
const myLastLong = myLongSig[myLongSig.length - 1];
const myLastShort = myShortSig[myShortSig.length - 1];

const myRsiColor = myLastRsi > myRsiOverbought ? '#e63946' : (myLastRsi < myRsiOversold ? '#00a86b' : '#ffffff');
const mySignalText = myLastLong ? 'LONG' : (myLastShort ? 'SHORT' : 'WAIT');
const mySignalColor = myLastLong ? '#00a86b' : (myLastShort ? '#e63946' : '#7a8499');

paint_overlay('InvestAIHud', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'RSI', color: '#7a8499' }, { text: String(myLastRsi), color: myRsiColor }] },
		{ cells: [{ text: 'MACD', color: '#7a8499' }, { text: myLastMacdBull ? 'BULL' : 'BEAR', color: myLastMacdBull ? '#00a86b' : '#e63946' }] },
		{ cells: [{ text: 'Trend', color: '#7a8499' }, { text: myLastTrendUp ? 'UP' : 'DOWN', color: myLastTrendUp ? '#00a86b' : '#e63946' }] },
		{ cells: [{ text: 'ATR', color: '#7a8499' }, { text: String(myLastAtr), color: '#d4870a' }] },
		{ cells: [{ text: 'Signal', color: '#7a8499' }, { text: mySignalText, color: mySignalColor }] }
	]
});