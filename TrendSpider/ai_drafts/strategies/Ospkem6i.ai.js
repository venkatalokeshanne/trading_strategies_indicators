describe_indicator('EMA MACD RSI Confluence Strategy', 'lower');

// Inputs for the various lengths used in the original Pine script
const myEmaFastLength = input.number('EMA Fast Length', 9, { min: 1, max: 200 });
const myEmaSlowLength = input.number('EMA Slow Length', 20, { min: 1, max: 200 });
const myMacdFastLength = input.number('MACD Fast Length', 12, { min: 1, max: 200 });
const myMacdSlowLength = input.number('MACD Slow Length', 26, { min: 1, max: 200 });
const myMacdSignalLength = input.number('MACD Signal Length', 9, { min: 1, max: 200 });
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });

// Stop/Limit percentages, taken from the Pine strategy.exit() calls
const myLongStopPercent = input.number('Long Stop %', 1.8, { min: 0, max: 100 });
const myLongLimitPercent = input.number('Long Limit %', 6, { min: 0, max: 100 });
const myShortStopPercent = input.number('Short Stop %', 1.8, { min: 0, max: 100 });
const myShortLimitPercent = input.number('Short Limit %', 6, { min: 0, max: 100 });

// EMA 9 / EMA 20
const myEmaFast = ema(close, myEmaFastLength);
const myEmaSlow = ema(close, myEmaSlowLength);

// MACD: computed manually using EMA(12), EMA(26) and the signal EMA(9) of the MACD line,
// since this reproduces ta.macd() exactly.
const myMacdFastEma = ema(close, myMacdFastLength);
const myMacdSlowEma = ema(close, myMacdSlowLength);
const myMacdLine = sub(myMacdFastEma, myMacdSlowEma);
const myMacdSignalLine = ema(myMacdLine, myMacdSignalLength);
const myMacdHist = sub(myMacdLine, myMacdSignalLine);

// RSI(14)
const myRsi = rsi(close, myRsiLength);

// Long/Short entry conditions, exactly mirroring the Pine logic
const myLongCondition = for_every(
	close, myEmaFast, myEmaSlow, myRsi, myMacdHist,
	(_c, _ef, _es, _r, _h) => (_c > _ef && _c > _es && _r > 50 && _h > 0)
);

const myShortCondition = for_every(
	close, myEmaFast, myEmaSlow, myRsi, myMacdHist,
	(_c, _ef, _es, _r, _h) => (_c < _ef && _c < _es && _r < 50 && _h < 0)
);

// Exit levels, computed off the current candle's close (as per Pine's "close * factor")
const myLongStopLevel = mult(close, 1 - myLongStopPercent / 100);
const myLongLimitLevel = mult(close, 1 + myLongLimitPercent / 100);
const myShortStopLevel = mult(close, 1 + myShortStopPercent / 100);
const myShortLimitLevel = mult(close, 1 - myShortLimitPercent / 100);

// Register signals for scanning, alerts and strategy testing
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');

// Paint the core indicator lines (lower panel), with EMAs forced onto price axis
paint(myEmaFast, { name: 'EMA Fast', color: '#26A69A', thickness: 1, forceUsePriceAxis: true });
paint(myEmaSlow, { name: 'EMA Slow', color: '#EF5350', thickness: 1, forceUsePriceAxis: true });
paint(myMacdHist, { name: 'MACD Histogram', color: '#789DFF', style: 'column' });
paint(myRsi, { name: 'RSI', color: '#B967FF' });
paint(horizontal_line(50), { name: 'RSI Mid', color: 'gray', style: 'dotted' });

// Paint markers for long/short entries (labels on candles)
const myLongMarker = for_every(myLongCondition, _l => _l ? 1 : null);
const myShortMarker = for_every(myShortCondition, _s => _s ? 1 : null);
paint(myLongMarker, { name: 'Long Signal', style: 'labels_below', color: '#26A69A' });
paint(myShortMarker, { name: 'Short Signal', style: 'labels_above', color: '#EF5350' });

// Exit levels painted on the price axis for reference
paint(myLongStopLevel, { name: 'Long Stop Level', color: '#EF5350', style: 'dotted', forceUsePriceAxis: true });
paint(myLongLimitLevel, { name: 'Long Limit Level', color: '#26A69A', style: 'dotted', forceUsePriceAxis: true });
paint(myShortStopLevel, { name: 'Short Stop Level', color: '#EF5350', style: 'dotted', forceUsePriceAxis: true });
paint(myShortLimitLevel, { name: 'Short Limit Level', color: '#26A69A', style: 'dotted', forceUsePriceAxis: true });