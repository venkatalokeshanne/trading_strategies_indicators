/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Penroute Trend Score
 * Author       : jordanventures
 * Source URL   : https://www.tradingview.com/script/VBQ1702o-Penroute-Trend-Score
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Penroute Trend Score_TV
 *
 * Deviations from the original: Panel is a static image of the last bar; ADX/ATR/EMA hand-rolled Pine-style; text
 *   colours simplified
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Penroute Trend Score_TV', 'price');
const myAdxLen = input.number('ADX length', 14, { min: 1, max: 200 });
const myAdxTh = input.number('ADX above', 25, { min: 0, max: 100 });
const myErLen = input.number('Efficiency lookback', 20, { min: 1, max: 500 });
const myErTh = input.number('Efficiency above', 0.55, { min: 0, max: 1, step: 0.01 });
const myEmaLen = input.number('EMA length', 50, { min: 1, max: 1000 });
const myEmaLook = input.number('EMA closes lookback', 10, { min: 1, max: 500 });
const myEmaNeed = input.number('Closes needed', 8, { min: 1, max: 500 });
const mySweepLook = input.number('Sweep lookback', 20, { min: 1, max: 500 });
const mySweepTh = input.number('Reversion below', 0.40, { min: 0, max: 1, step: 0.01 });
const myAtrFast = input.number('ATR fast', 5, { min: 1, max: 500 });
const myAtrSlow = input.number('ATR slow', 20, { min: 1, max: 500 });
const myAtrTh = input.number('ATR ratio above', 1.30, { min: 0, max: 10, step: 0.05 });
const myN = close.length;
const myRma = (_s, _n) => { let myAcc = null, myCnt = 0, mySum = 0; return _s.map(_v => { if (_v === null) return null; if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; } myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc; }); };
const myWinSum = (_s, _n) => _s.map((_v, _i) => { if (_i < _n - 1) return null; let myS = 0; for (let myK = _i - _n + 1; myK <= _i; myK += 1) { if (_s[myK] === null) return null; myS += _s[myK]; } return myS; });
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
// ta.dmi(len, len): ADX
const myUp = high.map((_h, _i) => _i === 0 ? null : _h - high[_i - 1]);
const myDn = low.map((_l, _i) => _i === 0 ? null : low[_i - 1] - _l);
const myPdm = myUp.map((_u, _i) => _u === null ? null : (_u > myDn[_i] && _u > 0 ? _u : 0));
const myMdm = myDn.map((_d, _i) => _d === null ? null : (_d > myUp[_i] && _d > 0 ? _d : 0));
const myTrr = myRma(myTr, myAdxLen), myPr = myRma(myPdm, myAdxLen), myMr = myRma(myMdm, myAdxLen);
const myPlus = myTrr.map((_t, _i) => (_t === null || _t === 0 || myPr[_i] === null) ? null : 100 * myPr[_i] / _t);
const myMinus = myTrr.map((_t, _i) => (_t === null || _t === 0 || myMr[_i] === null) ? null : 100 * myMr[_i] / _t);
const myDx = myPlus.map((_p, _i) => (_p === null || myMinus[_i] === null) ? null : Math.abs(_p - myMinus[_i]) / ((_p + myMinus[_i]) === 0 ? 1 : (_p + myMinus[_i])));
const myAdx = myRma(myDx, myAdxLen).map(_v => _v === null ? null : 100 * _v);
const myC1 = myAdx.map(_a => _a !== null && _a > myAdxTh);
// efficiency ratio
const myNet = close.map((_c, _i) => _i < myErLen ? null : Math.abs(_c - close[_i - myErLen]));
const myAbsCh = close.map((_c, _i) => _i === 0 ? null : Math.abs(_c - close[_i - 1]));
const myPath = myWinSum(myAbsCh, myErLen);
const myEff = myNet.map((_n, _i) => (_n === null || myPath[_i] === null) ? null : (myPath[_i] > 0 ? _n / myPath[_i] : 0));
const myC2 = myEff.map(_e => _e !== null && _e > myErTh);
// EMA side (Pine ta.ema, SMA-seeded)
let myEa = null, myEc = 0, myEs = 0;
const myK = 2 / (myEmaLen + 1);
const myEma = close.map(_c => { if (myEa === null) { myEs += _c; myEc += 1; if (myEc === myEmaLen) myEa = myEs / myEmaLen; return myEa; } myEa = myK * _c + (1 - myK) * myEa; return myEa; });
const myAbove = myWinSum(close.map((_c, _i) => (myEma[_i] !== null && _c > myEma[_i]) ? 1 : 0), myEmaLook);
const mySame = myAbove.map(_a => _a === null ? null : Math.max(_a, myEmaLook - _a));
const myC3 = mySame.map(_s => _s !== null && _s >= myEmaNeed);
// sweep reversion
const myBH = high.map((_h, _i) => _i > 0 && _h > high[_i - 1]), myBL = low.map((_l, _i) => _i > 0 && _l < low[_i - 1]);
const myRev = close.map((_c, _i) => { if (_i === 0) return false; if (myBH[_i] && myBL[_i]) return _c <= high[_i - 1] && _c >= low[_i - 1]; if (myBH[_i]) return _c <= high[_i - 1]; if (myBL[_i]) return _c >= low[_i - 1]; return false; });
const myBreaks = myWinSum(close.map((_c, _i) => (myBH[_i] || myBL[_i]) ? 1 : 0), mySweepLook);
const myReverts = myWinSum(myRev.map(_r => _r ? 1 : 0), mySweepLook);
const myRevRate = myBreaks.map((_b, _i) => (_b !== null && _b > 0) ? myReverts[_i] / _b : null);
const myC4 = myRevRate.map((_r, _i) => _r !== null && myBreaks[_i] >= 5 && _r < mySweepTh);
// ATR ratio
const myAf = myRma(myTr, myAtrFast), myAs = myRma(myTr, myAtrSlow);
const myAtrRatio = myAs.map((_s, _i) => _s === null ? null : (_s > 0 && myAf[_i] !== null ? myAf[_i] / _s : 0));
const myC5 = myAtrRatio.map(_r => _r !== null && _r > myAtrTh);
const myScore = close.map((_c, _i) => (myC1[_i] ? 1 : 0) + (myC2[_i] ? 1 : 0) + (myC3[_i] ? 1 : 0) + (myC4[_i] ? 1 : 0) + (myC5[_i] ? 1 : 0));
paint(myEma, { name: 'EMA', color: 'gray' });
const myL = myN - 1, myS = myScore[myL];
const myVerdict = myS >= 3 ? 'TREND' : (myS <= 1 ? 'RANGE' : 'MIXED');
const myMethod = myS >= 3 ? 'Sweep and continuation' : (myS <= 1 ? 'Reversal, original' : 'No clear read');
const myVc = myS >= 3 ? '#96660D' : (myS <= 1 ? '#2F6F62' : '#98A2AC');
const myFmt = (_v, _d) => _v === null ? 'n/a' : _v.toFixed(_d);
const myRow = (_a, _b, _c) => ({ cells: [{ text: _a, color: 'gray', background_color: '#333333' }, { text: _b, color: 'white', background_color: '#333333' }, { text: _c ? 'YES' : 'no', color: _c ? '#E0A030' : 'gray', background_color: '#333333' }] });
paint_overlay('Trend Score Panel', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: current.ticker + '  ' + myVerdict, color: 'white', background_color: myVc }, { text: myS + '/5', color: 'white', background_color: myVc }, { text: ' ', background_color: myVc }] },
		myRow('ADX', myFmt(myAdx[myL], 1), myC1[myL]),
		myRow('Efficiency', myFmt(myEff[myL], 2), myC2[myL]),
		myRow('Closes vs EMA', (mySame[myL] === null ? 'n/a' : mySame[myL]) + '/' + myEmaLook, myC3[myL]),
		myRow('Sweep reversion', myRevRate[myL] === null ? 'n/a' : Math.round(myRevRate[myL] * 100) + '% (' + myBreaks[myL] + ')', myC4[myL]),
		myRow('ATR ratio', myFmt(myAtrRatio[myL], 2), myC5[myL]),
		{ cells: [{ text: 'Method', color: 'gray', background_color: '#333333' }, { text: myMethod, color: 'white', background_color: myVc }, { text: ' ', background_color: '#333333' }] }
	]
});
register_signal(myC1, 'ADX above threshold');
register_signal(myC2, 'Efficiency above threshold');
register_signal(myC3, 'Closes same side of EMA');
register_signal(myC4, 'Sweep reversion below threshold');
register_signal(myC5, 'ATR ratio above threshold');
register_signal(myScore.map(_s => _s >= 3), 'Trend verdict');
register_signal(myScore.map(_s => _s <= 1), 'Range verdict');
register_signal(myScore.map(_s => _s === 2), 'Mixed verdict');
