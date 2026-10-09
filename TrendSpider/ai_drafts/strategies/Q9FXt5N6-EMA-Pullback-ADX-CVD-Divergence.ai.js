describe_indicator('EMA Pullback ADX CVD Divergence', 'price');

// ===== INPUTS =====
const tab = input.tab('Settings');
const myAdxLen = tab.number('ADX Length', 14, { min: 1, max: 100 });
const myAdxThreshold = tab.number('ADX Threshold', 25, { min: 1, max: 100 });
const myRR = tab.number('RR', 3.0, { min: 0.1, max: 20 });
const myLookback = tab.number('Divergence Lookback', 10, { min: 1, max: 200 });

// ===== EMA =====
const myEma9 = ema(close, 9);
const myEma20 = ema(close, 20);

// ===== ADX / DMI =====
const myAdxObject = indicators.adx(myAdxLen);
const myAdx = myAdxObject.adx;

// ===== CVD (Proxy, built from candle direction * volume) =====
const myDelta = for_every(close, open, volume, (_c, _o, _v) => {
	if (_c > _o) return _v;
	if (_c < _o) return -_v;
	return 0;
});
const myCvd = for_every(myDelta, (_d, _prev) => (_prev || 0) + _d);

// ===== DIVERGENCE =====
// Bullish: price makes a Lower Low while CVD makes a Higher Low
const myPriceLL = for_every(low, lowest(shift(low, 1), myLookback), (_l, _ll) => _ll !== null && _l < _ll);
const myCvdHL = for_every(myCvd, lowest(shift(myCvd, 1), myLookback), (_c, _cl) => _cl !== null && _c > _cl);
const myBullDiv = for_every(myPriceLL, myCvdHL, (_a, _b) => _a && _b);

// Bearish: price makes a Higher High while CVD makes a Lower High
const myPriceHH = for_every(high, highest(shift(high, 1), myLookback), (_h, _hh) => _hh !== null && _h > _hh);
const myCvdLH = for_every(myCvd, highest(shift(myCvd, 1), myLookback), (_c, _ch) => _ch !== null && _c < _ch);
const myBearDiv = for_every(myPriceHH, myCvdLH, (_a, _b) => _a && _b);

// ===== TREND CROSS DETECTION =====
const myEma9Prev = shift(myEma9, 1);
const myEma20Prev = shift(myEma20, 1);
const myBullCross = for_every(myEma9, myEma20, myEma9Prev, myEma20Prev, (_f, _s, _fp, _sp) => _f > _s && _fp <= _sp);
const myBearCross = for_every(myEma9, myEma20, myEma9Prev, myEma20Prev, (_f, _s, _fp, _sp) => _f < _s && _fp >= _sp);

// ===== STRONG TREND =====
const myStrongTrend = for_every(myAdx, _a => _a > myAdxThreshold);

// ===== SWING SL / TP LEVELS =====
const mySwingLow = lowest(low, 5);
const mySwingHigh = highest(high, 5);

// ===== SEQUENTIAL STATE MACHINE (mirrors Pine's "var bool" + per-bar logic) =====
// Note: replaced "new Array(...)" with "Array(...)" since the "new" keyword
// is not allowed by the scripting engine. Array() without "new" behaves
// identically for this purpose.
const myCandleCount = close.length;
const myBuySignalArray = Array(myCandleCount).fill(false);
const mySellSignalArray = Array(myCandleCount).fill(false);
const myBuySLArray = Array(myCandleCount).fill(null);
const mySellSLArray = Array(myCandleCount).fill(null);
const myBuyTPArray = Array(myCandleCount).fill(null);
const mySellTPArray = Array(myCandleCount).fill(null);

let myWaitBuy = false;
let myWaitSell = false;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myBullCross[myIndex]) {
		myWaitBuy = true;
		myWaitSell = false;
	}
	if (myBearCross[myIndex]) {
		myWaitSell = true;
		myWaitBuy = false;
	}

	const myPullbackBuy = myWaitBuy && (low[myIndex] <= myEma9[myIndex] || low[myIndex] <= myEma20[myIndex]);
	const myPullbackSell = myWaitSell && (high[myIndex] >= myEma9[myIndex] || high[myIndex] >= myEma20[myIndex]);

	const myBuySignal = myPullbackBuy && myStrongTrend[myIndex] && myBullDiv[myIndex] && close[myIndex] > open[myIndex];
	const mySellSignal = myPullbackSell && myStrongTrend[myIndex] && myBearDiv[myIndex] && close[myIndex] < open[myIndex];

	myBuySignalArray[myIndex] = myBuySignal;
	mySellSignalArray[myIndex] = mySellSignal;

	if (myBuySignal) {
		const myBuySL = mySwingLow[myIndex];
		const myBuyRisk = close[myIndex] - myBuySL;
		myBuySLArray[myIndex] = myBuySL;
		myBuyTPArray[myIndex] = close[myIndex] + myBuyRisk * myRR;
		myWaitBuy = false;
	}

	if (mySellSignal) {
		const mySellSL = mySwingHigh[myIndex];
		const mySellRisk = mySellSL - close[myIndex];
		mySellSLArray[myIndex] = mySellSL;
		mySellTPArray[myIndex] = close[myIndex] - mySellRisk * myRR;
		myWaitSell = false;
	}
}

// ===== PLOTS =====
paint(myEma9, { name: 'EMA9', color: '#26A69A', thickness: 2 });
paint(myEma20, { name: 'EMA20', color: '#EF5350', thickness: 2 });

const myBuyMarkerSeries = for_every(myBuySignalArray.map((_v, _i) => (_v ? low[_i] : null)), _v => _v);
const mySellMarkerSeries = for_every(mySellSignalArray.map((_v, _i) => (_v ? high[_i] : null)), _v => _v);

paint(myBuyMarkerSeries, { name: 'BuyMarker', style: 'labels_below', color: '#26A69A' });
paint(mySellMarkerSeries, { name: 'SellMarker', style: 'labels_above', color: '#EF5350' });

// ===== STOP LOSS / TAKE PROFIT LEVELS (sparse, land on signal candles) =====
paint(myBuySLArray, { name: 'BuyStopLoss', style: 'dotted', color: '#B71C1C', forceUsePriceAxis: true });
paint(myBuyTPArray, { name: 'BuyTakeProfit', style: 'dotted', color: '#1B5E20', forceUsePriceAxis: true });
paint(mySellSLArray, { name: 'SellStopLoss', style: 'dotted', color: '#B71C1C', forceUsePriceAxis: true });
paint(mySellTPArray, { name: 'SellTakeProfit', style: 'dotted', color: '#1B5E20', forceUsePriceAxis: true });

// ===== SIGNALS FOR SCANNER / ALERTS / STRATEGY TESTER =====
register_signal(myBuySignalArray, 'Buy Signal');
register_signal(mySellSignalArray, 'Sell Signal');