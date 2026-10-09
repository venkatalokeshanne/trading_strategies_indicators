describe_indicator('Quant Scoring System Long Only', 'lower');

// NOTE: This is a conversion of a Pine Script STRATEGY into an INDICATOR.
// The Custom JS API has no portfolio/position/equity simulation (no
// strategy.entry/exit/close, no strategy.position_avg_price, no runner
// mode state tied to real fills). So all position sizing, ATR/hard
// stops, take-profit, runner-mode trailing stop and the backtest P&L
// logic from the Pine script cannot be reproduced here. What IS
// reproduced exactly (same math, same bars) is: the composite Score,
// the Regime filter, the Long entry condition, the Base exit condition
// and the HTF "bearish" condition, all exposed as paintable lines and
// as register_signal() outputs usable in Scanners/Alerts.
// Also, Pine's ta.linreg(src, length, offset) evaluates the SAME fitted
// regression line at different offsets inside its window. The JS API's
// linreg() only gives the endpoint value (offset 0) per bar, so the
// "slope" term is approximated as linreg(close,lenFast) minus that same
// series shifted by 1 bar (i.e., comparing endpoints of two
// consecutively-fitted lines rather than two points on one line). This
// is a reasonable proxy, but not bit-identical to Pine's slope term.

const myLenFast = input.number('Fast Length', 20, { min: 1, max: 500 });
const myLenSlow = input.number('Slow Length', 100, { min: 1, max: 1000 });
const myLenMom = input.number('Momentum Length', 1, { min: 1, max: 500 });
const myLenVol = input.number('Volatility Length', 10, { min: 1, max: 500 });
const myLenZ = input.number('ZScore Length', 20, { min: 1, max: 500 });
const myLongTh = input.number('Long Score Threshold', 2.0, { min: -10, max: 10, step: 0.1 });
const myExitTh = input.number('Exit Score Threshold', 0.0, { min: -10, max: 10, step: 0.1 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 500 });

const myHtfTab = input.tab('Runner HTF');
const myHtfTf = myHtfTab.select('Runner Higher Timeframe', '240', constants.time_frames);
const myHtfEmaLen = myHtfTab.number('Runner HTF EMA Length', 50, { min: 1, max: 1000 });

// === Features ===
const myEmaFast = ema(close, myLenFast);
const myEmaSlow = ema(close, myLenSlow);
const myAtr = atr(high, low, close, myAtrLen);

const myTrend = for_every(myEmaFast, myEmaSlow, myAtr, (_ef, _es, _a) => {
	if (_a === 0) return 0;
	return Math.max(-3, Math.min(3, (_ef - _es) / _a)) / 3;
});

const myMomRaw = roc(close, myLenMom);

function myZscore(_src, _len) {
	const myMean = sma(_src, _len);
	const myStd = stdev(_src, _len);
	return for_every(_src, myMean, myStd, (_v, _m, _s) => (_s === 0 ? 0 : (_v - _m) / _s));
}

function myNorm(_src, _len) {
	const myZ = myZscore(_src, _len);
	return for_every(myZ, _z => Math.max(-3, Math.min(3, _z)) / 3);
}

const myMom = myNorm(myMomRaw, myLenZ);

const myBasis = vwma(close, myLenFast);
const myStretch = for_every(close, myBasis, myAtr, (_c, _b, _a) => (_a === 0 ? 0 : (_c - _b) / _a));
const myMr = for_every(myStretch, _s => Math.max(-3, Math.min(3, -_s)) / 3);

const myCloseShift1 = shift(close, 1);
const myLogRet = for_every(close, myCloseShift1, (_c, _p) => (_p ? Math.log(_c / _p) : 0));
const myVolRaw = stdev(myLogRet, myLenVol);
const myVolReg = myNorm(myVolRaw, myLenZ);
const myVolConf = myNorm(volume, myLenZ);

// Approximated slope term, see note above about linreg offsets
const myLinreg = linreg(close, myLenFast);
const myLinregShift1 = shift(myLinreg, 1);
const mySlope = sub(myLinreg, myLinregShift1);
const mySlopeN = myNorm(mySlope, myLenZ);

const mySignTrend = for_every(myTrend, _t => Math.sign(_t));
const mySignMom = for_every(myMom, _m => Math.sign(_m));

const myScore = for_every(
	myTrend, myMom, myMr, myVolReg, mySignTrend, myVolConf, mySignMom, mySlopeN,
	(_trend, _mom, _mr, _volReg, _signTrend, _volConf, _signMom, _slopeN) => {
		return 0.20 * _trend + 0.20 * _mom + 0.10 * _mr
			+ 0.0 * _volReg * _signTrend
			+ 0.10 * _volConf * _signMom
			+ 0.10 * _slopeN;
	}
);

const myScoreScaled = mult(myScore, 7.0);

// === Regime filter ===
const myRegimeLong = for_every(myEmaFast, myEmaSlow, close, (_ef, _es, _c) => _ef > _es && _c > _es);

// === Entry / Exit conditions ===
const myLongSignal = for_every(myScoreScaled, myRegimeLong, (_s, _r) => _s > myLongTh && _r);
const myBaseExitSignal = for_every(myScoreScaled, myEmaFast, close, (_s, _ef, _c) => _s < myExitTh || _c < _ef);

// === Higher timeframe runner logic (bearish filter) ===
const myHtfData = await request.history(current.ticker, myHtfTf);
assert(!myHtfData.error, 'Error fetching HTF data: ' + myHtfData.error);

const myHtfEma = ema(myHtfData.close, myHtfEmaLen);
const myHtfEmaShift1 = shift(myHtfEma, 1);
const myHtfBearishRaw = for_every(myHtfData.close, myHtfEma, myHtfEmaShift1, (_c, _e, _ePrev) => _c < _e && _e < _ePrev);

const myHtfCloseLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfData.close, time, 'le'),
	'constant'
);
const myHtfEmaLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfEma, time, 'le'),
	'constant'
);
const myHtfBearishLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfBearishRaw, time, 'le'),
	'constant'
);
const myHtfBearish = for_every(myHtfBearishLanded, _v => !!_v);

// === Visualization ===
const myBarColors = for_every(myLongSignal, _l => (_l ? 'lime' : 'gray'));
color_candles(myBarColors);

paint(myScoreScaled, { name: 'Score', color: 'white', thickness: 2 });
paint(horizontal_line(myLongTh), { name: 'Long Threshold', color: 'lime', style: 'dotted' });
paint(horizontal_line(myExitTh), { name: 'Exit Threshold', color: 'orange', style: 'dotted' });
paint(myEmaFast, { name: 'EMA Fast', color: 'teal', forceUsePriceAxis: true });
paint(myEmaSlow, { name: 'EMA Slow', color: 'orange', forceUsePriceAxis: true });

register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myBaseExitSignal, 'Base Exit Signal');
register_signal(myHtfBearish, 'Runner HTF Bearish');