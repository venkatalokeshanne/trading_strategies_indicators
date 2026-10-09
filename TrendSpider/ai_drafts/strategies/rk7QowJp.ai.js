describe_indicator('Scalping Strategy Improved v2', 'price');

// ===== INPUTS =====
const emaTab = input.tab('EMA');
const myEmaFast = emaTab.number('EMA Fast', 50, { min: 1, max: 500 });
const myEmaSlow = emaTab.number('EMA Slow', 200, { min: 1, max: 500 });

const rsiTab = input.tab('RSI');
const myRsiLen = rsiTab.number('RSI Length', 3, { min: 1, max: 100 });
const myRsiOB = rsiTab.number('RSI Overbought', 80, { min: 1, max: 100 });
const myRsiOS = rsiTab.number('RSI Oversold', 20, { min: 1, max: 100 });

const adxTab = input.tab('ADX');
const myAdxLen = adxTab.number('ADX Length', 5, { min: 1, max: 100 });
const myAdxLevel = adxTab.number('ADX Level', 20, { min: 1, max: 100 });

const atrTab = input.tab('ATR');
const myAtrLen = atrTab.number('ATR Length', 14, { min: 1, max: 100 });
const myAtrMult = atrTab.number('ATR Multiplier', 1.2, { min: 0.1, max: 10, step: 0.1 });

// ===== INDICATORS =====
const myEma50 = ema(close, myEmaFast);
const myEma200 = ema(close, myEmaSlow);
const myRsi = rsi(close, myRsiLen);
const myAdxObject = indicators.adx(myAdxLen);
const myAdx = myAdxObject.adx;
const myAtr = atr(high, low, close, myAtrLen);

// candle body / range strength
const myBody = for_every(close, open, (_c, _o) => Math.abs(_c - _o));
const myRange = sub(high, low);
const myStrongBull = for_every(close, open, myBody, myRange, (_c, _o, _b, _r) => _c > _o && _b > _r * 0.5);
const myStrongBear = for_every(close, open, myBody, myRange, (_c, _o, _b, _r) => _c < _o && _b > _r * 0.5);

// ===== TREND =====
const myTrendLong = for_every(close, myEma50, myEma200, (_c, _e50, _e200) => _c > _e50 && _e50 > _e200);
const myTrendShort = for_every(close, myEma50, myEma200, (_c, _e50, _e200) => _c < _e50 && _e50 < _e200);

// ===== MOMENTUM: crossover / crossunder of RSI =====
const myRsiPrev = shift(myRsi, 1);
const myRsiLong = for_every(myRsi, myRsiPrev, (_r, _rp) => _r > myRsiOS && _rp <= myRsiOS);
const myRsiShort = for_every(myRsi, myRsiPrev, (_r, _rp) => _r < myRsiOB && _rp >= myRsiOB);

// ===== STRENGTH =====
const myTrendStrength = for_every(myAdx, _a => _a > myAdxLevel);

// ===== CONDITIONS =====
const myLongCondition = for_every(myTrendLong, myRsiLong, myTrendStrength, myStrongBull, (_a, _b, _c, _d) => _a && _b && _c && _d);
const myShortCondition = for_every(myTrendShort, myRsiShort, myTrendStrength, myStrongBear, (_a, _b, _c, _d) => _a && _b && _c && _d);

// ===== STOP / TP (for reference, computed per candle) =====
const myLongStop = for_every(close, myAtr, (_c, _a) => _c - _a * myAtrMult);
const myShortStop = for_every(close, myAtr, (_c, _a) => _c + _a * myAtrMult);
const myLongTP = for_every(close, myLongStop, (_c, _s) => _c + (_c - _s) * 2);
const myShortTP = for_every(close, myShortStop, (_c, _s) => _c - (_s - _c) * 2);

// ===== PLOTS =====
paint(myEma50, { name: 'EMA Fast', color: '#FF9800', thickness: 2 });
paint(myEma200, { name: 'EMA Slow', color: '#2196F3', thickness: 2 });

// Buy/Sell markers on candles
const myBuyMarks = for_every(myLongCondition, _l => _l ? constants.icons.triangle_up : null);
const mySellMarks = for_every(myShortCondition, _s => _s ? constants.icons.triangle_down : null);
paint(myBuyMarks, { style: 'labels_below', color: '#26A69A', name: 'Buy Signal' });
paint(mySellMarks, { style: 'labels_above', color: '#EF5350', name: 'Sell Signal' });

// ===== SCANNER / STRATEGY SIGNALS =====
register_signal(myLongCondition, 'Buy Entry');
register_signal(myShortCondition, 'Sell Entry');