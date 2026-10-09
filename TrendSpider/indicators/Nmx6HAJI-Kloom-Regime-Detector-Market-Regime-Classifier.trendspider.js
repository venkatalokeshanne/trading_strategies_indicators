/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Kloom Regime Detector
 * Author       : Kloom
 * Source URL   : https://www.tradingview.com/script/Nmx6HAJI-Kloom-Regime-Detector-Market-Regime-Classifier
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Kloom Regime Detector_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact ADX/ATR; bgcolor replaced by colouring the ADX line by
 *   regime; diamond marker at regime changes; table via paint_overlay.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Kloom Regime Detector_TV', 'lower');
const myAdxLen = input.number('ADX length', 14, { min: 5, max: 50 });
const myAdxTrend = input.number('ADX trend threshold', 22, { min: 10, max: 40 });
const myVolLen = input.number('Volatility lookback', 20, { min: 5, max: 100 });
const myVolMult = input.number('High-vol multiplier', 1.5, { min: 1.0, max: 3.0, step: 0.1 });
const myEmaFast = input.number('Fast trend EMA', 50, { min: 10, max: 200 });
const myEmaSlow = input.number('Slow trend EMA', 200, { min: 50, max: 500 });
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null || _v === undefined || isNaN(_v)) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
// pine-parity: ta.dmi-style ADX and ta.atr with SMA-seeded RMA; ta.tr(true) uses high-low on the first bar
const myTrFirst = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
const myUp = high.map((_h, _i) => _i === 0 ? null : _h - high[_i - 1]);
const myDn = low.map((_l, _i) => _i === 0 ? null : -(_l - low[_i - 1]));
const myPlusDm = myUp.map((_u, _i) => _u === null ? null : (_u > myDn[_i] && _u > 0 ? _u : 0));
const myMinusDm = myUp.map((_u, _i) => _u === null ? null : (myDn[_i] > _u && myDn[_i] > 0 ? myDn[_i] : 0));
const myTrur = myRma(myTrFirst, myAdxLen);
const myPlusRma = myRma(myPlusDm, myAdxLen), myMinusRma = myRma(myMinusDm, myAdxLen);
const myPlusDi = myPlusRma.map((_v, _i) => (_v === null || myTrur[_i] === null) ? null : 100 * _v / myTrur[_i]);
const myMinusDi = myMinusRma.map((_v, _i) => (_v === null || myTrur[_i] === null) ? null : 100 * _v / myTrur[_i]);
const myDx = myPlusDi.map((_p, _i) => { if (_p === null || myMinusDi[_i] === null) return null; const myDen = _p + myMinusDi[_i]; return myDen === 0 ? 0 : 100 * Math.abs(_p - myMinusDi[_i]) / myDen; });
const myAdx = myRma(myDx, myAdxLen);
const myAtr = myRma(myTrFirst, myVolLen);
const myAtrPct = myAtr.map((_a, _i) => _a === null ? null : _a / close[_i] * 100);
const myAtrPctAvg = myAtrPct.map((_v, _i) => {
	const myN = myVolLen * 3;
	if (_i < myN - 1) return null;
	let mySum = 0;
	for (let myK = _i - myN + 1; myK <= _i; myK += 1) { if (myAtrPct[myK] === null) return null; mySum += myAtrPct[myK]; }
	return mySum / myN;
});
const myFast = ema(close, myEmaFast);
const mySlow = ema(close, myEmaSlow);
const myRegime = close.map((_c, _i) => {
	const myHv = myAtrPct[_i] !== null && myAtrPctAvg[_i] !== null && myAtrPct[_i] > myAtrPctAvg[_i] * myVolMult;
	if (myHv) return -1;
	if (myAdx[_i] !== null && myAdx[_i] > myAdxTrend) return (myFast[_i] !== null && mySlow[_i] !== null && myFast[_i] > mySlow[_i]) ? 2 : 1;
	return 0;
});
const myColors = { '2': 'teal', '1': 'red', '0': 'gray', '-1': 'gold' };
const myRegimeColor = myRegime.map(_r => myColors[String(_r)]);
paint(myAdx, { name: 'ADX', color: myRegimeColor, thickness: 2 });
paint(horizontal_line(myAdxTrend), { name: 'Trend Threshold', color: 'rgba(128,128,128,0.5)' });
paint(myRegime.map((_r, _i) => (_i > 0 && _r !== myRegime[_i - 1]) ? myAdx[_i] : null), { name: 'Regime Change Mark', style: 'dotted', marker: 'diamond', color: 'white' });
const myLast = close.length - 1;
const myTxt = myRegime[myLast] === 2 ? 'TREND BULL' : (myRegime[myLast] === 1 ? 'TREND BEAR' : (myRegime[myLast] === 0 ? 'RANGE' : 'HIGH VOL'));
paint_overlay('Regime Table', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'Regime', color: 'white', background_color: 'rgba(0,0,0,0.8)' }, { text: myTxt, color: 'white', background_color: myRegimeColor[myLast] }] },
		{ cells: [{ text: 'ADX', color: 'white', background_color: 'rgba(0,0,0,0.8)' }, { text: myAdx[myLast] === null ? 'n/a' : myAdx[myLast].toFixed(1), color: 'white', background_color: 'rgba(0,0,0,0.6)' }] },
		{ cells: [{ text: 'ATR%', color: 'white', background_color: 'rgba(0,0,0,0.8)' }, { text: myAtrPct[myLast] === null ? 'n/a' : myAtrPct[myLast].toFixed(2) + '%', color: 'white', background_color: 'rgba(0,0,0,0.6)' }] }
	]
});
register_signal(myRegime.map(_r => _r === 2), 'Trend Bull');
register_signal(myRegime.map(_r => _r === 1), 'Trend Bear');
register_signal(myRegime.map(_r => _r === 0), 'Range');
register_signal(myRegime.map(_r => _r === -1), 'High Volatility');
register_signal(myRegime.map((_r, _i) => _i > 0 && _r !== myRegime[_i - 1]), 'Regime Change');
