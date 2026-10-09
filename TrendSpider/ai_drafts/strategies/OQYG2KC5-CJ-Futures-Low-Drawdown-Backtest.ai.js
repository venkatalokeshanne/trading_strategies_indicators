describe_indicator('CJ Futures Low-Drawdown Setup', 'price');

// ──────────────────────────────────────────────────────────────
// Inputs, grouped to keep the panel tidy
// ──────────────────────────────────────────────────────────────
const myGeneralTab = input.tab('General');
const myEmaLength = myGeneralTab.number('EMA Length', 50, { min: 1, max: 500 });
const myTrendTf = myGeneralTab.select('Trend Timeframe', '240', constants.time_frames);
const mySetupTf = myGeneralTab.select('Setup Timeframe', '60', constants.time_frames);
const myRR = myGeneralTab.number('Risk Reward', 2.0, { min: 0.1, max: 20, step: 0.1 });

const mySwingTab = input.tab('Swing / Volume');
const mySwingLookback = mySwingTab.number('Swing Lookback', 5, { min: 1, max: 200 });
const myUseVolumeFilter = mySwingTab.boolean('Use Volume Filter', true);
const myVolumeLength = mySwingTab.number('Volume SMA Length', 20, { min: 1, max: 500 });

const mySessionTab = input.tab('Session');
const mySessionInput = mySessionTab.text('Main Session (HHMM-HHMM)', '0830-1130');

// ──────────────────────────────────────────────────────────────
// Current timeframe EMA
// ──────────────────────────────────────────────────────────────
const myEma = ema(close, myEmaLength);
paint(myEma, { name: 'EMA50', color: 'orange', thickness: 2 });

// ──────────────────────────────────────────────────────────────
// Higher timeframe filters (trend & setup timeframes)
// ──────────────────────────────────────────────────────────────
const myTrendHistoryPromise = request.history(current.ticker, myTrendTf);
const mySetupHistoryPromise = request.history(current.ticker, mySetupTf);
const [myTrendHistory, mySetupHistory] = await Promise.all([myTrendHistoryPromise, mySetupHistoryPromise]);

assert(!myTrendHistory.error, `Error fetching trend timeframe data: "${myTrendHistory.error}"`);
assert(!mySetupHistory.error, `Error fetching setup timeframe data: "${mySetupHistory.error}"`);

const myTrendEma = ema(myTrendHistory.close, myEmaLength);
const mySetupEma = ema(mySetupHistory.close, myEmaLength);

// Land higher timeframe close/ema onto the current chart's candles.
// 'ge' mimics Pine's request.security repainting-free lookahead=off behavior
// reasonably well: a current candle only "sees" the most recently closed
// higher timeframe bar.
const myTrendCloseLanded = interpolate_sparse_series(
	land_points_onto_series(myTrendHistory.time, myTrendHistory.close, time, 'le'),
	'constant'
);
const myTrendEmaLanded = interpolate_sparse_series(
	land_points_onto_series(myTrendHistory.time, myTrendEma, time, 'le'),
	'constant'
);
const mySetupCloseLanded = interpolate_sparse_series(
	land_points_onto_series(mySetupHistory.time, mySetupHistory.close, time, 'le'),
	'constant'
);
const mySetupEmaLanded = interpolate_sparse_series(
	land_points_onto_series(mySetupHistory.time, mySetupEma, time, 'le'),
	'constant'
);

const myBullTrend = for_every(myTrendCloseLanded, myTrendEmaLanded, mySetupCloseLanded, mySetupEmaLanded,
	(_tc, _te, _sc, _se) => _tc > _te && _sc > _se);
const myBearTrend = for_every(myTrendCloseLanded, myTrendEmaLanded, mySetupCloseLanded, mySetupEmaLanded,
	(_tc, _te, _sc, _se) => _tc < _te && _sc < _se);

// ──────────────────────────────────────────────────────────────
// Session filter: parse "HHMM-HHMM" and compare using exchange local time
// ──────────────────────────────────────────────────────────────
const mySessionParts = mySessionInput.split('-');
const mySessionFromMinutes = parseInt(mySessionParts[0].slice(0, 2), 10) * 60 + parseInt(mySessionParts[0].slice(2, 4), 10);
const mySessionToMinutes = parseInt(mySessionParts[1].slice(0, 2), 10) * 60 + parseInt(mySessionParts[1].slice(2, 4), 10);

const myInSession = time.map(_t => {
	const myTimeInfo = time_of(_t);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	return myMinutesOfDay >= mySessionFromMinutes && myMinutesOfDay <= mySessionToMinutes;
});

// ──────────────────────────────────────────────────────────────
// Volume filter
// ──────────────────────────────────────────────────────────────
const myVolSma = sma(volume, myVolumeLength);
const myGoodVolume = myUseVolumeFilter
	? for_every(volume, myVolSma, (_v, _vs) => _v > _vs)
	: series_of(true);

// ──────────────────────────────────────────────────────────────
// Pullback + trigger confirmation
// ──────────────────────────────────────────────────────────────
const myPullbackBuy = for_every(low, myEma, myBullTrend, (_l, _e, _bull) => _l <= _e && _bull);
const myPullbackSell = for_every(high, myEma, myBearTrend, (_h, _e, _bear) => _h >= _e && _bear);

const myPrevHigh = shift(high, 1);
const myPrevLow = shift(low, 1);

const myBullConfirm = for_every(close, open, myPrevHigh, (_c, _o, _ph) => _c > _o && _c > _ph);
const myBearConfirm = for_every(close, open, myPrevLow, (_c, _o, _pl) => _c < _o && _c < _pl);

const myBuySignal = for_every(myInSession, myGoodVolume, myPullbackBuy, myBullConfirm,
	(_s, _v, _pb, _bc) => _s && _v && _pb && _bc);
const mySellSignal = for_every(myInSession, myGoodVolume, myPullbackSell, myBearConfirm,
	(_s, _v, _ps, _sc) => _s && _v && _ps && _sc);

// ──────────────────────────────────────────────────────────────
// Stops and targets
// ──────────────────────────────────────────────────────────────
const myBuySL = lowest(low, mySwingLookback);
const mySellSL = highest(high, mySwingLookback);

const myBuyRisk = sub(close, myBuySL);
const mySellRisk = sub(mySellSL, close);

const myBuyTP = add(close, mult(myBuyRisk, myRR));
const mySellTP = sub(close, mult(mySellRisk, myRR));

const myFinalBuySignal = for_every(myBuySignal, myBuyRisk, (_b, _r) => _b && _r > 0);
const myFinalSellSignal = for_every(mySellSignal, mySellRisk, (_s, _r) => _s && _r > 0);

// ──────────────────────────────────────────────────────────────
// Visual signals
// ──────────────────────────────────────────────────────────────
const myBuyLabels = for_every(myFinalBuySignal, _b => _b ? constants.icons.triangle_up : null);
const mySellLabels = for_every(myFinalSellSignal, _s => _s ? constants.icons.triangle_down : null);

paint(myBuyLabels, { style: 'labels_below', color: 'green', name: 'BuySignal' });
paint(mySellLabels, { style: 'labels_above', color: 'red', name: 'SellSignal' });

// Optional reference lines for stop and target on the signal bar
paint(for_every(myFinalBuySignal, myBuySL, (_b, _v) => _b ? _v : null), { style: 'ladder', color: 'silver', name: 'BuyStopLevel' });
paint(for_every(myFinalBuySignal, myBuyTP, (_b, _v) => _b ? _v : null), { style: 'ladder', color: 'teal', name: 'BuyTargetLevel' });
paint(for_every(myFinalSellSignal, mySellSL, (_s, _v) => _s ? _v : null), { style: 'ladder', color: 'silver', name: 'SellStopLevel' });
paint(for_every(myFinalSellSignal, mySellTP, (_s, _v) => _s ? _v : null), { style: 'ladder', color: 'maroon', name: 'SellTargetLevel' });

// ──────────────────────────────────────────────────────────────
// Signals for scanners, alerts and strategy tester
// ──────────────────────────────────────────────────────────────
register_signal(myFinalBuySignal, 'Buy Signal');
register_signal(myFinalSellSignal, 'Sell Signal');