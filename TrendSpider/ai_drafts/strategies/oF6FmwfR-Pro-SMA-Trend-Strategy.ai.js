describe_indicator('Pro SMA Trend Strategy', 'price');

// ==========================================
// SETTINGS
// ==========================================
const tradeDirectionTab = input.tab('Strategy Settings');
const myTradeDirection = tradeDirectionTab.select('Trade Direction', 'Both', ['Both', 'Long Only', 'Short Only']);
const myLongLeverage = tradeDirectionTab.number('Long Leverage', 2.0, { min: 0.1, max: 100, step: 0.1 });
const myShortLeverage = tradeDirectionTab.number('Short Leverage', 1.0, { min: 0.1, max: 100, step: 0.1 });

const indicatorTab = input.tab('Indicator Settings');
const mySmaLength = indicatorTab.number('SMA Length', 44, { min: 1, max: 500 });

// ==========================================
// LOGIC
// Note: leverage/qty sizing and strategy.entry/strategy.close
// (equity, position management) are concepts from Pine Script's
// backtesting engine and have no equivalent in TrendSpider's
// Custom JS API. This script reproduces the SMA, the crossover/
// crossunder signal logic, and the visuals, and exposes long/short
// entry and exit conditions as scannable/alertable signals instead
// of actually managing simulated positions or quantities.
// ==========================================

const mySmaValue = sma(close, mySmaLength);

// crossover: close crosses above sma
const myLongCondition = for_every(close, mySmaValue, (_close, _sma, _prev, _index) => {
	if (_index === 0) return false;
	return _close > _sma && close[_index - 1] <= mySmaValue[_index - 1];
});

// crossunder: close crosses below sma
const myShortCondition = for_every(close, mySmaValue, (_close, _sma, _prev, _index) => {
	if (_index === 0) return false;
	return _close < _sma && close[_index - 1] >= mySmaValue[_index - 1];
});

// Entry/exit signals based on trade direction setting
const myLongEntrySignal = for_every(myLongCondition, _long => {
	return _long && (myTradeDirection === 'Both' || myTradeDirection === 'Long Only');
});

const myShortCloseSignal = for_every(myLongCondition, _long => {
	return _long && myTradeDirection === 'Short Only';
});

const myShortEntrySignal = for_every(myShortCondition, _short => {
	return _short && (myTradeDirection === 'Both' || myTradeDirection === 'Short Only');
});

const myLongCloseSignal = for_every(myShortCondition, _short => {
	return _short && myTradeDirection === 'Long Only';
});

// ==========================================
// VISUALS
// ==========================================

// 1. Colored SMA line (green above price, red below)
const mySmaColor = for_every(close, mySmaValue, (_close, _sma) => _close > _sma ? '#26A69A' : '#EF5350');
paint(mySmaValue, { name: 'Trend SMA', color: mySmaColor, thickness: 3 });

// 2. Buy/Short labels on candles
const myBuyLabels = for_every(myLongCondition, _long => _long ? 'BUY' : null);
const myShortLabels = for_every(myShortCondition, _short => _short ? 'SHORT' : null);

paint(myBuyLabels, { name: 'Buy Signal', style: 'labels_below', color: '#26A69A' });
paint(myShortLabels, { name: 'Short Signal', style: 'labels_above', color: '#EF5350' });

// 3. Candle coloring to approximate the trend background shading
const myTrendColors = for_every(close, mySmaValue, (_close, _sma) => _close > _sma ? '#26A69A' : '#EF5350');
color_candles(myTrendColors);

// ==========================================
// SIGNALS FOR SCANNER / ALERTS / STRATEGY TESTER
// ==========================================
register_signal(myLongCondition, 'Long Crossover');
register_signal(myShortCondition, 'Short Crossunder');
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongCloseSignal, 'Close Long');
register_signal(myShortCloseSignal, 'Close Short');