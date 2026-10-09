// Scalping indicator with EMA crossover, RSI filter, ATR volatility
// filter, and informational TP/SL/Trailing levels based on ATR.
describe_indicator('XAUUSD Scalping V2 Agresiv', 'price');

// Inputs organized into groups
const maGroup = input.group('Moving Averages');
const myEmaFastLen = maGroup.number('EMA Rapid', 5, { min: 1, max: 200 });
const myEmaSlowLen = maGroup.number('EMA Lent', 13, { min: 1, max: 200 });

const oscGroup = input.group('Oscillator Volatility');
const myRsiLen = oscGroup.number('RSI Rapid', 7, { min: 1, max: 200 });
const myAtrLen = oscGroup.number('ATR Length', 14, { min: 1, max: 200 });
// Shortened name to fix "input(): name is too lengthy" error
const myMinVolatility = oscGroup.number('Filtru ATR minim', 0.5, { min: 0, max: 100, step: 0.1 });

const riskGroup = input.group('Risk Management');
const myTpATR = riskGroup.number('Take Profit ATR', 1.2, { min: 0, max: 20, step: 0.1 });
const mySlATR = riskGroup.number('Stop Loss ATR', 0.8, { min: 0, max: 20, step: 0.1 });
const myTrailATR = riskGroup.number('Trailing Stop ATR', 0.5, { min: 0, max: 20, step: 0.1 });

// === Core calculations, matching Pine ta.ema, ta.rsi, ta.atr ===
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);
const myRsi = rsi(close, myRsiLen);
const myAtr = atr(high, low, close, myAtrLen);

// === Volatility filter ===
const myVolatilityOK = for_every(myAtr, _a => _a > myMinVolatility);

// === Crossover / crossunder detection (replicates ta.crossover / ta.crossunder) ===
const myEmaFastPrev = shift(myEmaFast, 1);
const myEmaSlowPrev = shift(myEmaSlow, 1);

const myLongCondition = for_every(
	myEmaFast, myEmaSlow, myEmaFastPrev, myEmaSlowPrev, myRsi, myVolatilityOK,
	(_fast, _slow, _fastPrev, _slowPrev, _r, _volOK) => {
		const myCrossOver = _fastPrev <= _slowPrev && _fast > _slow;
		return myCrossOver && _r > 55 && _volOK;
	});

const myShortCondition = for_every(
	myEmaFast, myEmaSlow, myEmaFastPrev, myEmaSlowPrev, myRsi, myVolatilityOK,
	(_fast, _slow, _fastPrev, _slowPrev, _r, _volOK) => {
		const myCrossUnder = _fastPrev >= _slowPrev && _fast < _slow;
		return myCrossUnder && _r < 45 && _volOK;
	});

// === Informational TP/SL/Trail levels (not an actual executed strategy, just for reference) ===
const myLongTakeProfit = for_every(close, myAtr, myLongCondition, (_c, _a, _l) => _l ? _c + _a * myTpATR : null);
const myLongStopLoss = for_every(close, myAtr, myLongCondition, (_c, _a, _l) => _l ? _c - _a * mySlATR : null);
const myShortTakeProfit = for_every(close, myAtr, myShortCondition, (_c, _a, _s) => _s ? _c - _a * myTpATR : null);
const myShortStopLoss = for_every(close, myAtr, myShortCondition, (_c, _a, _s) => _s ? _c + _a * mySlATR : null);

// === Plotting EMAs ===
paint(myEmaFast, { name: 'EMA Rapid', color: '#26A69A', thickness: 2 });
paint(myEmaSlow, { name: 'EMA Lent', color: '#EF5350', thickness: 2 });

// === Buy / Sell markers ===
const myBuyMarks = for_every(myLongCondition, low, (_l, _lo) => _l ? _lo : null);
const mySellMarks = for_every(myShortCondition, high, (_s, _hi) => _s ? _hi : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'lime' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

// === Signals for scanners, alerts and strategy tester ===
register_signal(myLongCondition, 'Buy Signal');
register_signal(myShortCondition, 'Sell Signal');