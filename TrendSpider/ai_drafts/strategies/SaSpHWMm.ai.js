describe_indicator('Swing Trading Playbook v1 - BTC/ETH/SOL', 'price');

// ==================== Inputs ====================
const myTab = input.tab('Settings');
const myEmaGroup = myTab.group('Moving Averages');
const myEmaRow = myEmaGroup.row();
const myLenEMA20 = myEmaRow.number('20 EMA', 20, { min: 1, max: 500 });
const myLenEMA50 = myEmaRow.number('50 EMA', 50, { min: 1, max: 500 });

const myOscGroup = myTab.group('Oscillators');
const myOscRow1 = myOscGroup.row();
const myLenRSI = myOscRow1.number('RSI Length', 14, { min: 1, max: 200 });
const myLenMACDFast = myOscRow1.number('MACD Fast', 12, { min: 1, max: 200 });
const myLenMACDSignal = myOscGroup.row().number('MACD Slow', 26, { min: 1, max: 200 });

const myBBGroup = myTab.group('Bollinger Bands');
const myBBRow = myBBGroup.row();
const myLenBB = myBBRow.number('BB Length', 20, { min: 1, max: 500 });
const myMultBB = myBBRow.number('BB Multiplier', 2.0, { min: 0.1, max: 10, step: 0.1 });

const myRiskGroup = myTab.group('Risk Management');
const myRiskRow = myRiskGroup.row();
const myAtrLen = myRiskRow.number('ATR Length', 14, { min: 1, max: 200 });
const myRRRatio = myRiskRow.number('Risk/Reward Ratio', 2.0, { min: 1.5, max: 10, step: 0.1 });
const myRiskPercent = myRiskRow.number('Risk Per Trade %', 1.0, { min: 0.5, max: 2.0, step: 0.1 });

// ==================== Current timeframe indicators ====================
const myEma20 = ema(close, myLenEMA20);
const myEma50 = ema(close, myLenEMA50);
const myRsi = rsi(close, myLenRSI);

// MACD(fast=12, slow=26, signal=9) : macdLine = EMA(fast) - EMA(slow); signalLine = EMA(macdLine, 9)
const myMacdFastEma = ema(close, myLenMACDFast);
const myMacdSlowEma = ema(close, myLenMACDSignal);
const myMacdLine = sub(myMacdFastEma, myMacdSlowEma);
const myMacdSignalLine = ema(myMacdLine, 9);
const myMacdHist = sub(myMacdLine, myMacdSignalLine);

// Bollinger middle band = SMA(close, lenBB)
const myBBMiddle = sma(close, myLenBB);
const myAtr = atr(high, low, close, myAtrLen);

const myVolSma20 = sma(volume, 20);

// ==================== Daily trend filter (via request.history) ====================
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching daily data: "${myDailyData.error}"`);

const myDailyEma20Raw = ema(myDailyData.close, myLenEMA20);
const myDailyEma50Raw = ema(myDailyData.close, myLenEMA50);
const myDailyMacdFastRaw = ema(myDailyData.close, myLenMACDFast);
const myDailyMacdSlowRaw = ema(myDailyData.close, myLenMACDSignal);
const myDailyMacdLineRaw = sub(myDailyMacdFastRaw, myDailyMacdSlowRaw);
const myDailyMacdSignalRaw = ema(myDailyMacdLineRaw, 9);
const myDailyMacdHistRaw = sub(myDailyMacdLineRaw, myDailyMacdSignalRaw);

const myDailyBullishRaw = for_every(
	myDailyData.close, myDailyEma20Raw, myDailyEma50Raw, myDailyMacdHistRaw,
	(_c, _e20, _e50, _h) => (_c > _e20 && _c > _e50 && _h > 0)
);

// Land daily values onto the current chart (use 'le' so we only use data
// known as of each intraday candle's time, avoiding lookahead bias)
const myDailyBullishLanded = land_points_onto_series(myDailyData.time, myDailyBullishRaw, time, 'le');
const myDailyBullish = interpolate_sparse_series(myDailyBullishLanded, 'constant');

// ==================== Entry conditions ====================
const myPullbackToSupport = for_every(close, myEma20, myBBMiddle, (_c, _e20, _bbm) => (_c <= _e20 || _c <= _bbm));
const myRsiCondition = for_every(myRsi, _r => _r > 45);
const myMacdBullish = for_every(myMacdHist, myMacdLine, myMacdSignalLine, (_h, _ml, _sl) => (_h > 0 || _ml > _sl));
const myVolumeConfirm = for_every(volume, myVolSma20, (_v, _vsma) => _v > _vsma * 0.8);

const myLongCondition = for_every(
	myDailyBullish, myPullbackToSupport, myRsiCondition, myMacdBullish,
	(_db, _pb, _rc, _mb) => Boolean(_db && _pb && _rc && _mb)
);

// ==================== Stop loss / take profit ====================
const myLongStop = sub(close, mult(myAtr, 1.5));
const myLongTP = add(close, mult(sub(close, myLongStop), myRRRatio));

// ==================== Signals (for scanners/alerts/strategy tester) ====================
register_signal(myLongCondition, 'Long Entry Signal');
register_signal(myDailyBullish, 'Daily Bullish Trend');

// ==================== Plotting ====================
paint(myEma20, { name: 'EMA20', color: '#FF9800', thickness: 2 });
paint(myEma50, { name: 'EMA50', color: '#2196F3', thickness: 2 });
paint(myBBMiddle, { name: 'BB Middle', color: 'gray', thickness: 1 });

const myLongSignalMarks = for_every(myLongCondition, low, (_lc, _lo) => _lc ? _lo : null);
paint(myLongSignalMarks, { name: 'Long Signal', style: 'labels_below', color: 'green' });

// ==================== Info panel overlay ====================
const myLastRsi = myRsi[myRsi.length - 1];
const myLastDailyBullish = myDailyBullish[myDailyBullish.length - 1];

paint_overlay('StrategyInfoPanel', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'Strategy Name', color: 'white' }, { text: 'Swing Trading Playbook v1', color: 'lime' }] },
		{ cells: [{ text: 'Current Trend', color: 'white' }, { text: myLastDailyBullish ? 'Bullish' : 'Bearish/Watch', color: myLastDailyBullish ? 'lime' : 'red' }] },
		{ cells: [{ text: 'RSI', color: 'white' }, { text: (myLastRsi != null ? myLastRsi.toFixed(2) : 'NA'), color: (myLastRsi > 50 ? 'lime' : 'red') }] },
		{ cells: [{ text: 'Risk Reward', color: 'white' }, { text: String(myRRRatio.toFixed(1)), color: 'white' }] }
	]
});