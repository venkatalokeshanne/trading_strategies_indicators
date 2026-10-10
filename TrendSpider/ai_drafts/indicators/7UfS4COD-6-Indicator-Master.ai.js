describe_indicator('6 Indicator Master', 'price');

// ================= 1. CM MACD =================
const myMacdFast = ema(close, 12);
const myMacdSlow = ema(close, 26);
const myMacdLine = sub(myMacdFast, myMacdSlow);
const myMacdSignal = sma(myMacdLine, 9);
const myMacdHist = sub(myMacdLine, myMacdSignal);

const myMacdBear = for_every(myMacdLine, myMacdSignal, myMacdHist, (_l, _s, _h) => _l < _s && _h <= 0);
const myMacdBull = for_every(myMacdLine, myMacdSignal, myMacdHist, (_l, _s, _h) => _l > _s && _h >= 0);

// ================= 2. SQUEEZE MOMENTUM =================
const mySqLen = 20;
const mySqHigh = highest(high, mySqLen);
const mySqLow = lowest(low, mySqLen);
const mySqAverage = sma(close, mySqLen);

const mySqSource = for_every(close, mySqHigh, mySqLow, mySqAverage, (_c, _h, _l, _a) => _c - ((_h + _l) / 2 + _a) / 2);
const mySqValue = linreg(mySqSource, mySqLen);

const mySqBear = for_every(mySqValue, (_v, _prev, _i) => _v < 0 && _v < (_i > 0 ? mySqValue[_i - 1] : _v));
const mySqBull = for_every(mySqValue, (_v, _prev, _i) => _v > 0 && _v > (_i > 0 ? mySqValue[_i - 1] : _v));

// ================= 3. WAVETREND =================
const myWtN1 = 10;
const myWtN2 = 21;

const myWtAP = hlc3;
const myWtESA = ema(myWtAP, myWtN1);
const myWtAbsDiff = for_every(myWtAP, myWtESA, (_a, _e) => Math.abs(_a - _e));
const myWtD = ema(myWtAbsDiff, myWtN1);

const myWtCI = for_every(myWtAP, myWtESA, myWtD, (_a, _e, _d) => _d !== 0 ? (_a - _e) / (0.015 * _d) : 0);

const myWt1 = ema(myWtCI, myWtN2);
const myWt2 = sma(myWt1, 4);

const myWtBear = for_every(myWt1, myWt2, (_w1, _w2) => _w1 < _w2);
const myWtBull = for_every(myWt1, myWt2, (_w1, _w2) => _w1 > _w2);

// ================= 4. BULL BEAR POWER TREND =================
const myBbLowest50 = lowest(low, 50);
const myBbHighest50 = highest(high, 50);
const myBbAtr5 = atr(high, low, close, 5);

const myBullTrend = for_every(close, myBbLowest50, myBbAtr5, (_c, _lo, _a) => _a !== 0 ? (_c - _lo) / _a : 0);
const myBearTrend = for_every(myBbHighest50, close, myBbAtr5, (_hi, _c, _a) => _a !== 0 ? (_hi - _c) / _a : 0);
const myBbTrend = sub(myBullTrend, myBearTrend);

const myBbBear = for_every(myBbTrend, _t => _t < 0);
const myBbBull = for_every(myBbTrend, _t => _t > 0);

// ================= 5. SUPERTREND =================
// NOTE: the built-in supertrend() function only exposes the trend line itself,
// not a separate "direction" output like Pine's ta.supertrend(). As an
// approximation, direction is derived by comparing close to the supertrend
// line: close above the line => bullish (line acts as support below price).
const mySupertrendLine = supertrend(10, 3.0, false);
const myStBear = for_every(close, mySupertrendLine, (_c, _st) => _c < _st);
const myStBull = for_every(close, mySupertrendLine, (_c, _st) => _c > _st);

// ================= 6. TRADE PRO REJECTION ZONE =================
const myFastMA = ema(close, 20);
const mySlowMA = ema(close, 50);

const myRzBear = for_every(myFastMA, mySlowMA, (_f, _s) => _f < _s);
const myRzBull = for_every(myFastMA, mySlowMA, (_f, _s) => _f > _s);

// ================= COUNT =================
const myBearCount = for_every(myMacdBear, mySqBear, myWtBear, myBbBear, myStBear, myRzBear,
	(_m, _sq, _wt, _bb, _st, _rz) => (_m ? 1 : 0) + (_sq ? 1 : 0) + (_wt ? 1 : 0) + (_bb ? 1 : 0) + (_st ? 1 : 0) + (_rz ? 1 : 0)
);

const myBullCount = for_every(myMacdBull, mySqBull, myWtBull, myBbBull, myStBull, myRzBull,
	(_m, _sq, _wt, _bb, _st, _rz) => (_m ? 1 : 0) + (_sq ? 1 : 0) + (_wt ? 1 : 0) + (_bb ? 1 : 0) + (_st ? 1 : 0) + (_rz ? 1 : 0)
);

const myAllBear = for_every(myBearCount, _c => _c === 6);
const myAllBull = for_every(myBullCount, _c => _c === 6);

const myBearTrigger = for_every(myAllBear, (_v, _prev, _i) => _v && !(_i > 0 && myAllBear[_i - 1]));
const myBullTrigger = for_every(myAllBull, (_v, _prev, _i) => _v && !(_i > 0 && myAllBull[_i - 1]));

// ================= CHART SIGNALS =================
const myBearShape = for_every(myBearTrigger, _t => _t ? constants.icons.triangle_down : null);
const myBullShape = for_every(myBullTrigger, _t => _t ? constants.icons.triangle_up : null);

paint(myBearShape, { style: 'labels_above', color: 'red', name: 'SixSixBearish' });
paint(myBullShape, { style: 'labels_below', color: 'green', name: 'SixSixBullish' });

// ================= SCANNER / ALERT SIGNALS =================
register_signal(myBearTrigger, '6/6 Bearish');
register_signal(myBullTrigger, '6/6 Bullish');
register_signal(myMacdBear, 'MACD Bearish');
register_signal(myMacdBull, 'MACD Bullish');
register_signal(mySqBear, 'Squeeze Bearish');
register_signal(mySqBull, 'Squeeze Bullish');
register_signal(myWtBear, 'WaveTrend Bearish');
register_signal(myWtBull, 'WaveTrend Bullish');
register_signal(myBbBear, 'BBPT Bearish');
register_signal(myBbBull, 'BBPT Bullish');
register_signal(myStBear, 'Supertrend Bearish');
register_signal(myStBull, 'Supertrend Bullish');
register_signal(myRzBear, 'Rejection Zone Bearish');
register_signal(myRzBull, 'Rejection Zone Bullish');

// ================= DASHBOARD =================
const myLastIndex = close.length - 1;

const myStatusOf = (_bear, _bull) => _bear[myLastIndex] ? 'BEAR' : _bull[myLastIndex] ? 'BULL' : 'NEUTRAL';
const myColorOf = (_bear, _bull) => _bear[myLastIndex] ? '#d9342b' : (_bull[myLastIndex] ? '#1fa855' : '#808080');

const myMasterStatus = myAllBear[myLastIndex] ? 'BEARISH' : (myAllBull[myLastIndex] ? 'BULLISH' : 'WAIT');
const myMasterColor = myAllBear[myLastIndex] ? '#d9342b' : (myAllBull[myLastIndex] ? '#1fa855' : '#808080');
const myBearCountColor = myAllBear[myLastIndex] ? '#d9342b' : '#808080';

paint_overlay('SixIndicatorDashboard', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: '#', background_color: '#000000', color: '#ffffff' }, { text: 'INDICATOR', background_color: '#000000', color: '#ffffff' }, { text: 'STATUS', background_color: '#000000', color: '#ffffff' }] },
		{ cells: [{ text: '1' }, { text: 'MACD' }, { text: myStatusOf(myMacdBear, myMacdBull), background_color: myColorOf(myMacdBear, myMacdBull), color: '#ffffff' }] },
		{ cells: [{ text: '2' }, { text: 'SQUEEZE' }, { text: myStatusOf(mySqBear, mySqBull), background_color: myColorOf(mySqBear, mySqBull), color: '#ffffff' }] },
		{ cells: [{ text: '3' }, { text: 'WAVETREND' }, { text: myStatusOf(myWtBear, myWtBull), background_color: myColorOf(myWtBear, myWtBull), color: '#ffffff' }] },
		{ cells: [{ text: '4' }, { text: 'BBPT' }, { text: myStatusOf(myBbBear, myBbBull), background_color: myColorOf(myBbBear, myBbBull), color: '#ffffff' }] },
		{ cells: [{ text: '5' }, { text: 'SUPERTREND' }, { text: myStatusOf(myStBear, myStBull), background_color: myColorOf(myStBear, myStBull), color: '#ffffff' }] },
		{ cells: [{ text: '6' }, { text: 'REJECTION' }, { text: myStatusOf(myRzBear, myRzBull), background_color: myColorOf(myRzBear, myRzBull), color: '#ffffff' }] },
		{ cells: [{ text: '' }, { text: 'BEAR COUNT' }, { text: `${myBearCount[myLastIndex]} / 6`, background_color: myBearCountColor, color: '#ffffff' }] },
		{ cells: [{ text: '' }, { text: 'MASTER' }, { text: myMasterStatus, background_color: myMasterColor, color: '#ffffff' }] }
	]
});