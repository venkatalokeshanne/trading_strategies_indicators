describe_indicator('Hemant Gold Strategy Signals', 'price');

// Inputs
const myEmaLen = input.number('EMA Length', 200, { min: 1, max: 1000 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMult = input.number('SL ATR Multiplier', 1.5, { min: 0.1, max: 10, step: 0.1 });

// Core indicators
const myEma200 = ema(close, myEmaLen);
const myAtr = atr(high, low, close, myAtrLen);

// Structure: highest high / lowest low over last 10 candles, shifted by 1
// (Pine's hh[1] / ll[1] means "value from the previous candle")
const myHh = shift(highest(high, 10), 1);
const myLl = shift(lowest(low, 10), 1);

// Buy / Sell conditions, computed per candle
const myBuySignal = for_every(low, close, myLl, myEma200, (_low, _close, _ll, _ema) =>
	_low < _ll && _close > _ll && _close > _ema
);

const mySellSignal = for_every(high, close, myHh, myEma200, (_high, _close, _hh, _ema) =>
	_high > _hh && _close < _hh && _close < _ema
);

// Plot EMA
paint(myEma200, { name: 'EMA200', color: '#2962FF', thickness: 2 });

// Plot buy/sell markers (below/above bar)
const myBuyMarks = for_every(myBuySignal, low, (_b, _low) => _b ? _low : null);
const mySellMarks = for_every(mySellSignal, high, (_s, _high) => _s ? _high : null);

paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: '#EF5350', thickness: 3 });

// Register signals so they can be used in Scanners, Alerts, Strategy Tester
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');

// Reference lines for SL/TP distances (informational only, based on last close)
// Not a real position tracker - see notes below.
paint(myAtr, { name: 'ATR', color: '#9E9E9E', thickness: 1, style: 'line', forceUsePriceAxis: false, hidden: true });