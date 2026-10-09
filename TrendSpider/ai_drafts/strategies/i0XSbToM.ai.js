describe_indicator('DMT Estrategia Universal Editable', 'price');

// Strategy entry/webhook payloads and strategy.entry() orders from the
// original Pine script have no equivalent in Custom JS API; this is
// a signal-only reproduction of the entry logic (long/short conditions),
// exposed via register_signal() for scanners/alerts/backtests.

const myTab = input.tab('Strategy');

const myUseEMA = myTab.boolean('Usar Cruce de EMAs', true);
const myEmaFastRow = myTab.row();
const myEmaFastLen = myEmaFastRow.number('EMA Rapida', 9, { min: 1, max: 500 });
const myEmaSlowLen = myEmaFastRow.number('EMA Lenta', 21, { min: 1, max: 500 });

const myUseRSI = myTab.boolean('Filtrar por RSI', false);
const myRsiRow = myTab.row();
const myRsiLen = myRsiRow.number('RSI Longitud', 14, { min: 1, max: 200 });
const myRsiOverB = myRsiRow.number('Sobrecompra', 70, { min: 1, max: 100 });
const myRsiOverS = myRsiRow.number('Sobreventa', 30, { min: 0, max: 99 });

const myUseTrend = myTab.boolean('Filtro de Tendencia EMA 200', true);

// Technical calculations
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);
const myEmaTrend = ema(close, 200);
const myRsi = rsi(close, myRsiLen);

// Crossover / Crossunder of fast/slow EMA, replicating ta.crossover/crossunder
const myCrossoverEMA = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _idx) => {
	if (_idx === 0) return false;
	return myEmaFast[_idx - 1] <= myEmaSlow[_idx - 1] && _fast > _slow;
});

const myCrossunderEMA = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _idx) => {
	if (_idx === 0) return false;
	return myEmaFast[_idx - 1] >= myEmaSlow[_idx - 1] && _fast < _slow;
});

// Logical conditions
const myLongEMA = myUseEMA ? myCrossoverEMA : series_of(true);
const myShortEMA = myUseEMA ? myCrossunderEMA : series_of(true);

const myLongRSI = myUseRSI ? for_every(myRsi, _r => _r < myRsiOverS) : series_of(true);
const myShortRSI = myUseRSI ? for_every(myRsi, _r => _r > myRsiOverB) : series_of(true);

const myLongTrend = myUseTrend ? for_every(close, myEmaTrend, (_c, _t) => _c > _t) : series_of(true);
const myShortTrend = myUseTrend ? for_every(close, myEmaTrend, (_c, _t) => _c < _t) : series_of(true);

// Final entry signals
const myLongSignal = for_every(myLongEMA, myLongRSI, myLongTrend, (_e, _r, _t) => _e && _r && _t);
const myShortSignal = for_every(myShortEMA, myShortRSI, myShortTrend, (_e, _r, _t) => _e && _r && _t);

// Expose signals for scanners, alerts and strategy backtests
register_signal(myLongSignal, 'Long Signal');
register_signal(myShortSignal, 'Short Signal');

// Visualization
paint(myEmaFast, { name: 'EMA Fast', color: '#2962FF', thickness: 1 });
paint(myEmaSlow, { name: 'EMA Slow', color: '#FF9800', thickness: 1 });
paint(myUseTrend ? myEmaTrend : series_of(null), { name: 'EMA Trend', color: '#9E9E9E', thickness: 2 });

const myLongMarks = for_every(myLongSignal, low, (_sig, _low) => _sig ? _low : null);
const myShortMarks = for_every(myShortSignal, high, (_sig, _high) => _sig ? _high : null);

paint(myLongMarks, { name: 'Long Entry', style: 'labels_below', color: '#26A69A' });
paint(myShortMarks, { name: 'Short Entry', style: 'labels_above', color: '#EF5350' });