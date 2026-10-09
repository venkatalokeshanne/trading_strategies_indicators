describe_indicator('Full Session Trading System', 'price');

// ===== INPUTS =====
const trendTab = input.tab('Trend');
const myEmaFast = trendTab.number('EMA Fast', 50, { min: 1, max: 500 });
const myEmaSlow = trendTab.number('EMA Slow', 200, { min: 1, max: 500 });
const myRsiLen = trendTab.number('RSI Length', 14, { min: 1, max: 100 });
const myMinConditions = trendTab.number('Trend Min Conditions', 3, { min: 1, max: 5 });

const stopsTab = input.tab('Stops');
const myUseATR = stopsTab.boolean('Use ATR Stop Loss', true);
const myAtrMult = stopsTab.number('ATR Multiplier', 1.2, { min: 0.1, max: 10 });
const myRR = stopsTab.number('Risk Reward', 1.8, { min: 0.1, max: 10 });

const htfTab = input.tab('HTF');
const myUseHTF = htfTab.boolean('Use HTF Filter', true);
const myHtfTF = htfTab.select('HTF Timeframe', '15', constants.time_frames);
const myUseCandle = htfTab.boolean('Use Candle Confirmation', true);

const asiaTab = input.tab('Asia');
const myAsiaRSIHigh = asiaTab.number('Asia RSI Sell Level', 65, { min: 1, max: 99 });
const myAsiaRSILow = asiaTab.number('Asia RSI Buy Level', 35, { min: 1, max: 99 });

// ===== SESSION (UTC hours derived from unix timestamp) =====
// Note: time_of() uses exchange timezone, but Pine's hour(time, "UTC")
// is explicitly UTC, so we derive UTC hour directly from the timestamp.
const myHourUTC = time.map(_t => Math.floor((_t % 86400) / 3600));

const myIsAsia = myHourUTC.map(_h => _h >= 0 && _h < 6);
const myIsLondon = myHourUTC.map(_h => _h >= 7 && _h < 10);
const myIsNewYork = myHourUTC.map(_h => _h >= 13 && _h < 16);
const myIsTrendSession = myIsLondon.map((_v, _i) => _v || myIsNewYork[_i]);
const myIsAsiaSession = myIsAsia;

// ===== INDICATORS =====
const myEma50 = ema(close, myEmaFast);
const myEma200 = ema(close, myEmaSlow);
const myRsiVal = rsi(close, myRsiLen);
const myAtrVal = atr(high, low, close, 14);

// ===== HTF FILTER =====
const myHtfData = await request.history(current.ticker, myHtfTF);
assert(!myHtfData.error, "Error fetching HTF data: " + myHtfData.error);

const myEma50HtfRaw = ema(myHtfData.close, myEmaFast);
const myEma200HtfRaw = ema(myHtfData.close, myEmaSlow);

// Land HTF values onto current series without look-ahead ('le' = last known closed HTF bar)
const myEma50HtfLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myEma50HtfRaw, time, 'le'),
	'constant'
);
const myEma200HtfLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myEma200HtfRaw, time, 'le'),
	'constant'
);

// ===== TREND LOGIC =====
const myUpTrend = for_every(myEma50, myEma200, (_f, _s) => _f > _s);
const myDownTrend = for_every(myEma50, myEma200, (_f, _s) => _f < _s);

const myHtfUp = for_every(myEma50HtfLanded, myEma200HtfLanded, (_f, _s) => _f > _s);
const myHtfDown = for_every(myEma50HtfLanded, myEma200HtfLanded, (_f, _s) => _f < _s);

const myFinalUp = for_every(myUpTrend, myHtfUp, (_u, _h) => myUseHTF ? (_u && _h) : _u);
const myFinalDown = for_every(myDownTrend, myHtfDown, (_d, _h) => myUseHTF ? (_d && _h) : _d);

// ===== TREND ENTRY =====
const myPrevLow = shift(lowest(low, 10), 1);
const myPrevHigh = shift(highest(high, 10), 1);

const mySweepLow = for_every(low, myPrevLow, (_l, _p) => _p !== null && _l < _p);
const mySweepHigh = for_every(high, myPrevHigh, (_h, _p) => _p !== null && _h > _p);

const myPullbackBuy = for_every(close, myEma50, (_c, _e) => _c < _e);
const myPullbackSell = for_every(close, myEma50, (_c, _e) => _c > _e);

const myRsiBuy = for_every(myRsiVal, _r => _r > 50);
const myRsiSell = for_every(myRsiVal, _r => _r < 50);

const myBull = for_every(close, open, (_c, _o) => _c > _o);
const myBear = for_every(close, open, (_c, _o) => _c < _o);

const myCandleBuy = myUseCandle ? myBull : close.map(() => true);
const myCandleSell = myUseCandle ? myBear : close.map(() => true);

const myBuyCount = for_every(
	myFinalUp, mySweepLow, myRsiBuy, myPullbackBuy, myCandleBuy,
	(_a, _b, _c, _d, _e) => (_a ? 1 : 0) + (_b ? 1 : 0) + (_c ? 1 : 0) + (_d ? 1 : 0) + (_e ? 1 : 0)
);
const mySellCount = for_every(
	myFinalDown, mySweepHigh, myRsiSell, myPullbackSell, myCandleSell,
	(_a, _b, _c, _d, _e) => (_a ? 1 : 0) + (_b ? 1 : 0) + (_c ? 1 : 0) + (_d ? 1 : 0) + (_e ? 1 : 0)
);

const myTrendBuy = myBuyCount.map(_v => _v >= myMinConditions);
const myTrendSell = mySellCount.map(_v => _v >= myMinConditions);

// ===== FIXED ASIA RANGE (stateful, computed via explicit loop) =====
const myAsiaHigh = series_of(null);
const myAsiaLow = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevIsAsia = myIndex > 0 ? myIsAsiaSession[myIndex - 1] : false;
	const myNewAsiaSession = myIsAsiaSession[myIndex] && !myPrevIsAsia;

	if (myNewAsiaSession) {
		myAsiaHigh[myIndex] = high[myIndex];
		myAsiaLow[myIndex] = low[myIndex];
	}
	else if (myIsAsiaSession[myIndex]) {
		const myPrevHighVal = myIndex > 0 ? myAsiaHigh[myIndex - 1] : null;
		const myPrevLowVal = myIndex > 0 ? myAsiaLow[myIndex - 1] : null;
		myAsiaHigh[myIndex] = myPrevHighVal === null ? high[myIndex] : Math.max(myPrevHighVal, high[myIndex]);
		myAsiaLow[myIndex] = myPrevLowVal === null ? low[myIndex] : Math.min(myPrevLowVal, low[myIndex]);
	}
	else {
		myAsiaHigh[myIndex] = myIndex > 0 ? myAsiaHigh[myIndex - 1] : null;
		myAsiaLow[myIndex] = myIndex > 0 ? myAsiaLow[myIndex - 1] : null;
	}
}

// ===== RANGE REACTIONS =====
const myNearLow = for_every(close, myAsiaLow, myAtrVal, (_c, _l, _a) => _l !== null && _c <= _l + _a * 0.2);
const myNearHigh = for_every(close, myAsiaHigh, myAtrVal, (_c, _h, _a) => _h !== null && _c >= _h - _a * 0.2);

const myAsiaBuy = for_every(myNearLow, myRsiVal, (_n, _r) => _n && _r < myAsiaRSILow);
const myAsiaSell = for_every(myNearHigh, myRsiVal, (_n, _r) => _n && _r > myAsiaRSIHigh);

// ===== CLEAN SIGNAL SYSTEM =====
const myBuySignal = for_every(
	myIsTrendSession, myTrendBuy, myIsAsiaSession, myAsiaBuy,
	(_t, _tb, _a, _ab) => (_t && _tb) || (_a && _ab)
);
const mySellSignal = for_every(
	myIsTrendSession, myTrendSell, myIsAsiaSession, myAsiaSell,
	(_t, _ts, _a, _as) => (_t && _ts) || (_a && _as)
);

// ===== VISUALS =====
paint(myEma50, { name: 'EMA50', color: '#2962FF', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: '#EF5350', thickness: 2 });
paint(myAsiaHigh, { name: 'AsiaHigh', color: '#FF9800', style: 'ladder' });
paint(myAsiaLow, { name: 'AsiaLow', color: '#FF9800', style: 'ladder' });

const myBuyMarks = myBuySignal.map(_v => _v ? true : null);
const mySellMarks = mySellSignal.map(_v => _v ? true : null);

paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: '#EF5350' });

// ===== SIGNALS FOR SCANNER / ALERTS / STRATEGY =====
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');