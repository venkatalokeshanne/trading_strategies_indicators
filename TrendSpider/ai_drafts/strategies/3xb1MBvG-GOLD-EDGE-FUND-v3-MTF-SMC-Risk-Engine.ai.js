describe_indicator('Gold Edge Fund v3 (MTF plus SMC Signals)', 'price');

// NOTE: Custom JS indicators cannot run as a strategy (no equity,
// no position tracking, no trade counters, no order execution).
// This script reproduces the Pine Script ENTRY LOGIC, the SMC
// conditions and the ATR based SL and TP levels exactly as
// computed values and registers Long/Short signals that can be
// used in Scanners, Alerts and the Strategy Tester module.
// Break even, trailing stop, daily loss limit and max trades per
// day are strategy level order-management features that have no
// equivalent in an indicator context, so they are not included.

const myLookback = input.number('Liquidity Lookback', 10, { min: 1, max: 200 });
const myRiskATRMult = input.number('ATR Risk Mult', 1.3, { min: 0.1, max: 10 });
const myRiskReward = input.number('Risk Reward', 1.6, { min: 0.1, max: 10 });

// ===================== HTF (15 min) bias =====================
const myHtfData = await request.history(current.ticker, '15');
assert(!myHtfData.error, 'Error fetching HTF data: ' + myHtfData.error);

const myHtfEma50 = ema(myHtfData.close, 50);
const myHtfEma200 = ema(myHtfData.close, 200);

const myHtfBullSparse = for_every(myHtfData.close, myHtfEma50, myHtfEma200, (_c, _e50, _e200) => (_c > _e50 && _e50 > _e200) ? 1 : 0);
const myHtfBearSparse = for_every(myHtfData.close, myHtfEma50, myHtfEma200, (_c, _e50, _e200) => (_c < _e50 && _e50 < _e200) ? 1 : 0);

const myHtfBullLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfBullSparse, time, 'ge'),
	'constant'
);
const myHtfBearLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfBearSparse, time, 'ge'),
	'constant'
);

// ===================== Local trend =====================
const myEma20 = ema(close, 20);
const myEma50 = ema(close, 50);

const myTrendUp = for_every(close, myEma20, myEma50, (_c, _e20, _e50) => _c > _e20 && _e20 > _e50);
const myTrendDown = for_every(close, myEma20, myEma50, (_c, _e20, _e50) => _c < _e20 && _e20 < _e50);

// ===================== FVG (imbalance) =====================
const myHighShift2 = shift(high, 2);
const myLowShift2 = shift(low, 2);

const myBullFVG = for_every(low, myHighShift2, (_l, _h2) => _h2 !== null && _l > _h2);
const myBearFVG = for_every(high, myLowShift2, (_h, _l2) => _l2 !== null && _h < _l2);

// ===================== Order block (refined) =====================
const myHighShift1 = shift(high, 1);
const myLowShift1 = shift(low, 1);
const myOpenShift1 = shift(open, 1);
const myCloseShift1 = shift(close, 1);

const myBullOB = for_every(close, myHighShift1, myOpenShift1, myCloseShift1, (_c, _h1, _o1, _cl1) => _h1 !== null && _c > _h1 && _o1 > _cl1);
const myBearOB = for_every(close, myLowShift1, myOpenShift1, myCloseShift1, (_c, _l1, _o1, _cl1) => _l1 !== null && _c < _l1 && _o1 < _cl1);

// ===================== Liquidity sweep =====================
const myLiqHigh = highest(high, myLookback);
const myLiqLow = lowest(low, myLookback);
const myLiqHighShift1 = shift(myLiqHigh, 1);
const myLiqLowShift1 = shift(myLiqLow, 1);

const mySweepHigh = for_every(high, myLiqHighShift1, close, myLiqHigh, (_h, _lh1, _c, _lh) => _lh1 !== null && _h > _lh1 && _c < _lh);
const mySweepLow = for_every(low, myLiqLowShift1, close, myLiqLow, (_l, _ll1, _c, _ll) => _ll1 !== null && _l < _ll1 && _c > _ll);

// ===================== Momentum filter =====================
const myRsi = rsi(close, 14);
const myMomentumBuy = for_every(myRsi, _r => _r > 55);
const myMomentumSell = for_every(myRsi, _r => _r < 45);

// ===================== Session filter (London + NY killzones, UTC) =====================
// Hours are derived from the raw UTC timestamp directly (not using
// time_of, which returns exchange local time) to match Pine's
// "hour" built-in, which operates on the chart timezone setting.
// We approximate Pine's default (exchange time) behavior using UTC
// hours; if your TradingView chart timezone differs from UTC, the
// session mask may shift versus the original script.
const mySessionOK = for_every(time, _t => {
	const myUtcHour = Math.floor((_t % 86400) / 3600);
	const myLondon = myUtcHour >= 7 && myUtcHour <= 10;
	const myNewYork = myUtcHour >= 13 && myUtcHour <= 16;
	return myLondon || myNewYork;
});

// ===================== Entry logic =====================
const myLongCond = for_every(
	mySessionOK, myHtfBullLanded, myTrendUp, mySweepLow, myBullFVG, myBullOB, myMomentumBuy,
	(_sess, _htfBull, _trendUp, _sweepLow, _bullFVG, _bullOB, _momBuy) =>
		Boolean(_sess && _htfBull && _trendUp && (_sweepLow || _bullFVG || _bullOB) && _momBuy)
);

const myShortCond = for_every(
	mySessionOK, myHtfBearLanded, myTrendDown, mySweepHigh, myBearFVG, myBearOB, myMomentumSell,
	(_sess, _htfBear, _trendDown, _sweepHigh, _bearFVG, _bearOB, _momSell) =>
		Boolean(_sess && _htfBear && _trendDown && (_sweepHigh || _bearFVG || _bearOB) && _momSell)
);

// ===================== Risk engine (levels only) =====================
const myAtr = atr(high, low, close, 14);

const myLongSL = sub(close, mult(myAtr, myRiskATRMult));
const myShortSL = add(close, mult(myAtr, myRiskATRMult));

const myLongTP = add(close, mult(myAtr, myRiskATRMult * myRiskReward));
const myShortTP = sub(close, mult(myAtr, myRiskATRMult * myRiskReward));

const myLongSLOut = for_every(myLongCond, myLongSL, (_cond, _sl) => _cond ? _sl : null);
const myLongTPOut = for_every(myLongCond, myLongTP, (_cond, _tp) => _cond ? _tp : null);
const myShortSLOut = for_every(myShortCond, myShortSL, (_cond, _sl) => _cond ? _sl : null);
const myShortTPOut = for_every(myShortCond, myShortTP, (_cond, _tp) => _cond ? _tp : null);

// ===================== Signals =====================
register_signal(myLongCond, 'Long Entry');
register_signal(myShortCond, 'Short Entry');

// ===================== Visuals =====================
paint(myEma20, { color: '#2962FF', name: 'EMA20', thickness: 2 });
paint(myEma50, { color: '#EF5350', name: 'EMA50', thickness: 2 });

const myLongMarks = for_every(myLongCond, low, (_cond, _l) => _cond ? _l : null);
const myShortMarks = for_every(myShortCond, high, (_cond, _h) => _cond ? _h : null);

paint(myLongMarks, { style: 'labels_below', color: '#26A69A', name: 'Buy Signal' });
paint(myShortMarks, { style: 'labels_above', color: '#EF5350', name: 'Sell Signal' });

paint(myLongSLOut, { style: 'ladder', color: '#FF8A65', name: 'Long Stop Loss' });
paint(myLongTPOut, { style: 'ladder', color: '#26A69A', name: 'Long Take Profit' });
paint(myShortSLOut, { style: 'ladder', color: '#FF8A65', name: 'Short Stop Loss' });
paint(myShortTPOut, { style: 'ladder', color: '#EF5350', name: 'Short Take Profit' });