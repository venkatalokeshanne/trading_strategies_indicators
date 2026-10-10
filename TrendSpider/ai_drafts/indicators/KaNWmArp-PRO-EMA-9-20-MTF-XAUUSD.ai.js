describe_indicator('PRO EMA 9 20 MTF XAUUSD', 'price');

// ===== Inputs =====
const emaTab = input.tab('EMA And MTF');
const emaRow = emaTab.row();
const myFastLen = emaRow.number('Fast EMA', 9, { min: 1, max: 200 });
const mySlowLen = emaRow.number('Slow EMA', 20, { min: 1, max: 200 });

const htfRow = emaTab.row();
const myHtf1 = htfRow.select('Confirmation TF 1', '5', constants.time_frames);
const myHtf2 = htfRow.select('Confirmation TF 2', '15', constants.time_frames);

const rsiTab = input.tab('RSI And ADX');
const rsiRow = rsiTab.row();
const myRsiLen = rsiRow.number('RSI Length', 14, { min: 1, max: 100 });
const myRsiBuy = rsiRow.number('Minimum RSI For Buy', 52, { min: 0, max: 100 });
const myRsiSell = rsiRow.number('Maximum RSI For Sell', 48, { min: 0, max: 100 });

const adxRow = rsiTab.row();
const myAdxLen = adxRow.number('ADX Length', 14, { min: 1, max: 100 });
const myAdxMin = adxRow.number('Minimum ADX', 18, { min: 0, max: 100 });

const atrTab = input.tab('ATR Risk');
const atrRow = atrTab.row();
const myAtrLen = atrRow.number('ATR Length', 14, { min: 1, max: 100 });
const myAtrSL = atrRow.number('SL ATR Multiplier', 1.5, { min: 0.1, max: 20, step: 0.1 });
const myRR = atrRow.number('Risk Reward', 1.8, { min: 0.1, max: 20, step: 0.1 });

// ===== Current timeframe EMAs =====
const myEma9 = ema(close, myFastLen);
const myEma20 = ema(close, mySlowLen);

paint(myEma9, { name: 'Ema9', color: '#00E5FF', thickness: 2 });
paint(myEma20, { name: 'Ema20', color: '#FFA726', thickness: 2 });

// ===== Higher timeframe data =====
const [myHtf1Data, myHtf2Data] = await Promise.all([
	request.history(current.ticker, myHtf1),
	request.history(current.ticker, myHtf2)
]);
assert(!myHtf1Data.error, `Error fetching HTF1 data: ${myHtf1Data.error}`);
assert(!myHtf2Data.error, `Error fetching HTF2 data: ${myHtf2Data.error}`);

const myHtf1Ema9Raw = ema(myHtf1Data.close, myFastLen);
const myHtf1Ema20Raw = ema(myHtf1Data.close, mySlowLen);
const myHtf2Ema9Raw = ema(myHtf2Data.close, myFastLen);
const myHtf2Ema20Raw = ema(myHtf2Data.close, mySlowLen);

// Land onto the current series without look-ahead (use last closed HTF candle)
const myHtf1Ema9 = interpolate_sparse_series(
	land_points_onto_series(myHtf1Data.time, myHtf1Ema9Raw, time, 'le'),
	'constant'
);
const myHtf1Ema20 = interpolate_sparse_series(
	land_points_onto_series(myHtf1Data.time, myHtf1Ema20Raw, time, 'le'),
	'constant'
);
const myHtf2Ema9 = interpolate_sparse_series(
	land_points_onto_series(myHtf2Data.time, myHtf2Ema9Raw, time, 'le'),
	'constant'
);
const myHtf2Ema20 = interpolate_sparse_series(
	land_points_onto_series(myHtf2Data.time, myHtf2Ema20Raw, time, 'le'),
	'constant'
);

// ===== MTF Trend =====
const myBullHTF = for_every(myHtf1Ema9, myHtf1Ema20, myHtf2Ema9, myHtf2Ema20,
	(_h1f, _h1s, _h2f, _h2s) => (_h1f != null && _h1s != null && _h2f != null && _h2s != null) &&
		_h1f > _h1s && _h2f > _h2s
);
const myBearHTF = for_every(myHtf1Ema9, myHtf1Ema20, myHtf2Ema9, myHtf2Ema20,
	(_h1f, _h1s, _h2f, _h2s) => (_h1f != null && _h1s != null && _h2f != null && _h2s != null) &&
		_h1f < _h1s && _h2f < _h2s
);

// ===== RSI =====
const myRsi = rsi(close, myRsiLen);
const myRsiBull = for_every(myRsi, _r => _r >= myRsiBuy);
const myRsiBear = for_every(myRsi, _r => _r <= myRsiSell);

// ===== ADX / DMI =====
const myAdxObject = indicators.adx(myAdxLen);
const myStrongTrend = for_every(myAdxObject.adx, _a => _a >= myAdxMin);
const myAdxBull = for_every(myAdxObject.dmiPlus, myAdxObject.dmiMinus, (_p, _m) => _p > _m);
const myAdxBear = for_every(myAdxObject.dmiPlus, myAdxObject.dmiMinus, (_p, _m) => _m > _p);

// ===== EMA Cross =====
const myEma9Prev = shift(myEma9, 1);
const myEma20Prev = shift(myEma20, 1);
const myEmaBullCross = for_every(myEma9, myEma20, myEma9Prev, myEma20Prev,
	(_f, _s, _fp, _sp) => _f > _s && _fp <= _sp
);
const myEmaBearCross = for_every(myEma9, myEma20, myEma9Prev, myEma20Prev,
	(_f, _s, _fp, _sp) => _f < _s && _fp >= _sp
);

// ===== Price confirmation =====
const myPriceBull = for_every(close, myEma9, (_c, _e) => _c > _e);
const myPriceBear = for_every(close, myEma9, (_c, _e) => _c < _e);

// ===== Final buy / sell conditions =====
// Note: Pine's barstate.isconfirmed is approximated as "always true" since
// TrendSpider custom scripts always evaluate on closed historical candles.
const myBuySignal = for_every(
	myEmaBullCross, myBullHTF, myRsiBull, myStrongTrend, myAdxBull, myPriceBull,
	(_c1, _c2, _c3, _c4, _c5, _c6) => _c1 && _c2 && _c3 && _c4 && _c5 && _c6
);
const mySellSignal = for_every(
	myEmaBearCross, myBearHTF, myRsiBear, myStrongTrend, myAdxBear, myPriceBear,
	(_c1, _c2, _c3, _c4, _c5, _c6) => _c1 && _c2 && _c3 && _c4 && _c5 && _c6
);

// ===== ATR SL / TP =====
const myAtr = atr(high, low, close, myAtrLen);

const myEntryPrice = series_of(null);
const myStopPrice = series_of(null);
const myTargetPrice = series_of(null);

let myLastEntry = null;
let myLastStop = null;
let myLastTarget = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myBuySignal[myIndex]) {
		myLastEntry = close[myIndex];
		myLastStop = close[myIndex] - myAtr[myIndex] * myAtrSL;
		myLastTarget = close[myIndex] + (myAtr[myIndex] * myAtrSL * myRR);
	}
	else if (mySellSignal[myIndex]) {
		myLastEntry = close[myIndex];
		myLastStop = close[myIndex] + myAtr[myIndex] * myAtrSL;
		myLastTarget = close[myIndex] - (myAtr[myIndex] * myAtrSL * myRR);
	}

	if (myBuySignal[myIndex] || mySellSignal[myIndex]) {
		myEntryPrice[myIndex] = myLastEntry;
		myStopPrice[myIndex] = myLastStop;
		myTargetPrice[myIndex] = myLastTarget;
	}
}

// ===== Labels =====
const myBuyMarks = for_every(myBuySignal, low, (_s, _l) => _s ? _l : null);
const mySellMarks = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: '#00E676' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: '#FF5252' });

// ===== Entry / SL / TP lines =====
paint(myEntryPrice, { name: 'Entry', style: 'ladder', color: 'yellow', thickness: 2 });
paint(myStopPrice, { name: 'StopLoss', style: 'ladder', color: 'red', thickness: 2 });
paint(myTargetPrice, { name: 'TakeProfit', style: 'ladder', color: '#00E676', thickness: 2 });

// ===== Signals for scanner / strategy / alerts =====
register_signal(myBuySignal, 'Pro Buy Signal');
register_signal(mySellSignal, 'Pro Sell Signal');
register_signal(myBullHTF, 'Bullish MTF Trend');
register_signal(myBearHTF, 'Bearish MTF Trend');