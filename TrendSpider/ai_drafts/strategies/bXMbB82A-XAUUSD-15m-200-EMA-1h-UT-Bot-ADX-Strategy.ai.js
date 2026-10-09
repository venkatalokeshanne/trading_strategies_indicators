describe_indicator('XAUUSD UT Bot plus ADX plus HTF EMA', 'price');

// This indicator reproduces the Pine Script logic (UT Bot trailing stop,
// ADX/DMI filter and HTF 200 EMA trend filter) using TrendSpider's
// Custom JS API. Strategy money-management (take profit / stop loss,
// position sizing) is not something an indicator can execute; instead
// we expose the entry condition as a scan/alert-ready signal.

const utTab = input.tab('UT Bot');
const myKeyValue = utTab.number('UT Bot Key Value', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myAtrPeriod = utTab.number('UT Bot ATR Period', 1, { min: 1, max: 50 });

const adxTab = input.tab('ADX');
const myAdxLen = adxTab.number('ADX Smoothing', 14, { min: 1, max: 100 });
const myDiLen = adxTab.number('DI Length', 14, { min: 1, max: 100 });
const myAdxThresh = adxTab.number('ADX Minimum Level', 25, { min: 1, max: 100 });

const htfTab = input.tab('HTF EMA');
const myEmaPeriod = htfTab.number('HTF EMA Period', 200, { min: 1, max: 500 });
const myHtfTimeframe = htfTab.select('HTF Timeframe', '60', constants.time_frames);

// --- HTF 200 EMA, computed on the higher timeframe then landed onto this chart ---
const myHtfData = await request.history(current.ticker, myHtfTimeframe);
assert(!myHtfData.error, 'Error fetching HTF data: ' + myHtfData.error);

const myHtfEmaRaw = ema(myHtfData.close, myEmaPeriod);
const myHtfEmaLanded = land_points_onto_series(myHtfData.time, myHtfEmaRaw, time, 'ge');
const myHtfEma = interpolate_sparse_series(myHtfEmaLanded, 'constant');

// --- ADX / DMI ---
// NOTE: Pine's ta.dmi(diLen, adxLen) allows independent DI length and ADX
// smoothing length. The built-in indicators.adx() only exposes a single
// period parameter used for both. We use diLen for that parameter, which
// is an approximation; values may differ slightly from Pine when
// diLen != adxLen.
const myAdxObject = indicators.adx(myDiLen);
const myAdxValue = myAdxObject.adx;

// --- UT Bot trailing stop (requires sequential state, built with a loop) ---
const myAtrSeries = atr(high, low, close, myAtrPeriod);
const myNLoss = mult(myAtrSeries, myKeyValue);

const myTrailingStop = series_of(null);
const myPos = series_of(0);
const myUtBotBuy = series_of(false);
const myUtBotSell = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myIndex === 0 || myTrailingStop[myIndex - 1] === null) {
		myTrailingStop[myIndex] = Math.max(close[myIndex] - myNLoss[myIndex], 0.0);
		myPos[myIndex] = 0;
		continue;
	}

	const myPrevStop = myTrailingStop[myIndex - 1];
	const myPrevClose = close[myIndex - 1];
	const myCurrentClose = close[myIndex];
	const myCurrentNLoss = myNLoss[myIndex];

	let myNewStop;
	if (myPrevClose > myPrevStop && myCurrentClose > myPrevStop) {
		myNewStop = Math.max(myPrevStop, myCurrentClose - myCurrentNLoss);
	}
	else if (myPrevClose < myPrevStop && myCurrentClose < myPrevStop) {
		myNewStop = Math.min(myPrevStop, myCurrentClose + myCurrentNLoss);
	}
	else {
		myNewStop = myCurrentClose > myPrevStop ? myCurrentClose - myCurrentNLoss : myCurrentClose + myCurrentNLoss;
	}

	myTrailingStop[myIndex] = myNewStop;

	let myNewPos = myPos[myIndex - 1];
	if (myCurrentClose > myPrevStop && myPrevClose <= myPrevStop) {
		myNewPos = 1;
	}
	else if (myCurrentClose < myPrevStop && myPrevClose >= myPrevStop) {
		myNewPos = -1;
	}
	myPos[myIndex] = myNewPos;

	myUtBotBuy[myIndex] = (myNewPos === 1 && myPos[myIndex - 1] === -1);
	myUtBotSell[myIndex] = (myNewPos === -1 && myPos[myIndex - 1] === 1);
}

// --- Strategy conditions ---
const myHtfTrendBullish = for_every(close, myHtfEma, (_close, _ema) => _close > _ema);

const myBuyCondition = series_of(false);
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	myBuyCondition[myIndex] = myUtBotBuy[myIndex] && myHtfTrendBullish[myIndex] && myAdxValue[myIndex] > myAdxThresh;
}

// --- Painting ---
paint(myHtfEma, { name: 'HTF EMA', color: 'orange', thickness: 2 });

const myBuyMarks = for_every(myBuyCondition, _buy => _buy ? 1 : null);
paint(myBuyMarks, { name: 'Buy Entry', style: 'labels_below', color: 'green' });

// --- Signals for scanners, alerts and strategy testing ---
register_signal(myBuyCondition, 'Valid Strategy Entry');
register_signal(myUtBotBuy, 'UT Bot Buy');
register_signal(myUtBotSell, 'UT Bot Sell');
register_signal(myHtfTrendBullish, 'HTF Trend Bullish');
register_signal(for_every(myAdxValue, _adx => _adx > myAdxThresh), 'ADX Above Threshold');

// --- Status overlay (approximation of the Pine info table) ---
const myLastHtfBullish = myHtfTrendBullish[myHtfTrendBullish.length - 1];
const myLastAdx = myAdxValue[myAdxValue.length - 1];

paint_overlay('StatusTable', { position: 'top_right' }, {
	rows: [{
		cells: [
			{ text: '1H Trend', color: 'white' },
			{ text: myLastHtfBullish ? 'BULLISH' : 'BEARISH', background_color: myLastHtfBullish ? 'green' : 'red', color: 'white' }
		]
	}, {
		cells: [
			{ text: 'Current ADX', color: 'white' },
			{ text: myLastAdx != null ? myLastAdx.toFixed(2) : 'N/A', background_color: (myLastAdx || 0) > myAdxThresh ? 'green' : 'navy', color: 'white' }
		]
	}]
});