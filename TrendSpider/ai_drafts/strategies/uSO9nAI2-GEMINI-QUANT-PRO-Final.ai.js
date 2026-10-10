describe_indicator('Gemini Quant Pro', 'price');

// ───────────────────────────────────────────────
// Inputs
// ───────────────────────────────────────────────
const emaTab = input.tab('EMA Settings');
const myEma44Length = emaTab.number('EMA 44 Length', 44, { min: 1, max: 500 });
const myEma200Length = emaTab.number('EMA 200 Length', 200, { min: 1, max: 500 });

const riskTab = input.tab('Risk Management');
const myTp1Mult = riskTab.number('TP1 Profit Ratio (RR)', 1.5, { min: 0.1, max: 20 });
const myTp2Mult = riskTab.number('TP2 Profit Ratio (RR)', 3.0, { min: 0.1, max: 20 });
const myTp3Mult = riskTab.number('TP3 Profit Ratio (RR)', 5.0, { min: 0.1, max: 20 });
const mySlBufferPercent = riskTab.number('SL Buffer (%)', 0.2, { min: 0, max: 10 });
const mySlBuffer = mySlBufferPercent / 100;

// ───────────────────────────────────────────────
// Multi timeframe trend data (Daily, 4H, 1H, 15min)
// ───────────────────────────────────────────────
const [myDailyData, my4hData, my1hData, my15mData] = await Promise.all([
	request.history(current.ticker, 'D'),
	request.history(current.ticker, '240'),
	request.history(current.ticker, '60'),
	request.history(current.ticker, '15')
]);

assert(!myDailyData.error, `Error fetching Daily data: ${myDailyData.error}`);
assert(!my4hData.error, `Error fetching 240 data: ${my4hData.error}`);
assert(!my1hData.error, `Error fetching 60 data: ${my1hData.error}`);
assert(!my15mData.error, `Error fetching 15 data: ${my15mData.error}`);

function myComputeTrend(_data) {
	const myEmaVal = ema(_data.close, myEma200Length);
	return for_every(_data.close, myEmaVal, (_c, _e) => _c > _e ? 1 : -1);
}

const myTrendDailyRaw = myComputeTrend(myDailyData);
const myTrend4hRaw = myComputeTrend(my4hData);
const myTrend1hRaw = myComputeTrend(my1hData);
const myTrend15mRaw = myComputeTrend(my15mData);

// land onto current chart (using 'le' so we only use data that already existed, no future leakage)
const myTrendDaily = interpolate_sparse_series(land_points_onto_series(myDailyData.time, myTrendDailyRaw, time, 'le'), 'constant');
const myTrend4h = interpolate_sparse_series(land_points_onto_series(my4hData.time, myTrend4hRaw, time, 'le'), 'constant');
const myTrend1h = interpolate_sparse_series(land_points_onto_series(my1hData.time, myTrend1hRaw, time, 'le'), 'constant');
const myTrend15m = interpolate_sparse_series(land_points_onto_series(my15mData.time, myTrend15mRaw, time, 'le'), 'constant');

// ───────────────────────────────────────────────
// EMA retest logic (current chart)
// ───────────────────────────────────────────────
const myEma44 = ema(close, myEma44Length);
const myEma200 = ema(close, myEma200Length);
const myVolumeSma = sma(volume, 20);

const myBullRetest = for_every(low, close, myEma44, myEma200, (_l, _c, _e44, _e200) => _l <= _e44 && _c > _e44 && _c > _e200);
const myBearRetest = for_every(high, close, myEma44, myEma200, (_h, _c, _e44, _e200) => _h >= _e44 && _c < _e44 && _c < _e200);
const myVolFilter = for_every(volume, myVolumeSma, (_v, _sv) => _v > _sv);

const myLongCondition = for_every(myBullRetest, myTrendDaily, myTrend4h, myVolFilter, (_bull, _tD, _t4h, _vf) => _bull && _tD == 1 && _t4h == 1 && _vf);
const myShortCondition = for_every(myBearRetest, myTrendDaily, myTrend4h, myVolFilter, (_bear, _tD, _t4h, _vf) => _bear && _tD == -1 && _t4h == -1 && _vf);

// ───────────────────────────────────────────────
// Trade simulation (reproducing strategy.position_size == 0 logic)
// ───────────────────────────────────────────────
const myCandleCount = close.length;
const mySl = series_of(null);
const myTp1 = series_of(null);
const myTp2 = series_of(null);
const myTp3 = series_of(null);

let myPositionSize = 0; // 0 = flat, 1 = long, -1 = short
let myEntryPrice = null;
let myCurrentSl = null;
let myCurrentTp1 = null;
let myCurrentTp2 = null;
let myCurrentTp3 = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	// check exits first (stop/limit on current bar range)
	if (myPositionSize == 1) {
		if (low[myIndex] <= myCurrentSl || high[myIndex] >= myCurrentTp3) {
			myPositionSize = 0;
		}
	}
	else if (myPositionSize == -1) {
		if (high[myIndex] >= myCurrentSl || low[myIndex] <= myCurrentTp3) {
			myPositionSize = 0;
		}
	}

	if (myPositionSize == 0 && myLongCondition[myIndex]) {
		myEntryPrice = close[myIndex];
		myCurrentSl = low[myIndex] * (1 - mySlBuffer);
		const myRisk = myEntryPrice - myCurrentSl;
		myCurrentTp1 = myEntryPrice + myRisk * myTp1Mult;
		myCurrentTp2 = myEntryPrice + myRisk * myTp2Mult;
		myCurrentTp3 = myEntryPrice + myRisk * myTp3Mult;
		myPositionSize = 1;
	}
	else if (myPositionSize == 0 && myShortCondition[myIndex]) {
		myEntryPrice = close[myIndex];
		myCurrentSl = high[myIndex] * (1 + mySlBuffer);
		const myRisk = myCurrentSl - myEntryPrice;
		myCurrentTp1 = myEntryPrice - myRisk * myTp1Mult;
		myCurrentTp2 = myEntryPrice - myRisk * myTp2Mult;
		myCurrentTp3 = myEntryPrice - myRisk * myTp3Mult;
		myPositionSize = -1;
	}

	if (myPositionSize != 0) {
		mySl[myIndex] = myCurrentSl;
		myTp1[myIndex] = myCurrentTp1;
		myTp2[myIndex] = myCurrentTp2;
		myTp3[myIndex] = myCurrentTp3;
	}
}

// ───────────────────────────────────────────────
// Signals for scanner / alerts / strategy tester
// ───────────────────────────────────────────────
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');

// ───────────────────────────────────────────────
// Painting
// ───────────────────────────────────────────────
paint(myEma44, { name: 'EMA44', color: '#FF9800', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: '#2962FF', thickness: 2 });

paint(mySl, { name: 'StopLoss', style: 'ladder', color: '#EF5350', thickness: 2 });
paint(myTp1, { name: 'TP1', style: 'ladder', color: '#26A69A', thickness: 1 });
paint(myTp2, { name: 'TP2', style: 'ladder', color: '#26A69A', thickness: 1 });
paint(myTp3, { name: 'TP3', style: 'ladder', color: '#26A69A', thickness: 2 });

const myBuyMarks = for_every(myLongCondition, low, (_cond, _low) => _cond ? _low : null);
const mySellMarks = for_every(myShortCondition, high, (_cond, _high) => _cond ? _high : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: '#EF5350' });