/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : The Flash
 * Author       : SlouchyRhino
 * Source URL   : https://www.tradingview.com/script/u8aA5Hae-The-Flash
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : The Flash_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact ta.dmi hand-rolled; bgcolor replaced by a high-low
 *   band; arrows as icons.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('The Flash_TV', 'price');
const myAdxLen = input.number('ADX Length', 14, { min: 1, max: 100 });
const myAdxThr = input.number('ADX Threshold', 13.0, { min: 0, max: 100, step: 0.1 });
const myFlashColor = 'rgba(128,128,128,0.3)';
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null || _v === undefined || isNaN(_v)) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
// pine-parity: ta.dmi(len, len) -> [+DI, -DI, ADX] with SMA-seeded RMA and fixnan
const myTr = high.map((_h, _i) => _i === 0 ? null : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
const myUp = high.map((_h, _i) => _i === 0 ? null : _h - high[_i - 1]);
const myDn = low.map((_l, _i) => _i === 0 ? null : -(_l - low[_i - 1]));
const myPlusDm = myUp.map((_u, _i) => _u === null ? null : (_u > myDn[_i] && _u > 0 ? _u : 0));
const myMinusDm = myUp.map((_u, _i) => _u === null ? null : (myDn[_i] > _u && myDn[_i] > 0 ? myDn[_i] : 0));
const myTrur = myRma(myTr, myAdxLen);
const myFix = (_s) => { let myLast = null; return _s.map(_v => { if (_v !== null) myLast = _v; return myLast; }); };
const myPlusRma = myRma(myPlusDm, myAdxLen), myMinusRma = myRma(myMinusDm, myAdxLen);
const myPlus = myFix(myPlusRma.map((_v, _i) => (_v === null || myTrur[_i] === null) ? null : 100 * _v / myTrur[_i]));
const myMinus = myFix(myMinusRma.map((_v, _i) => (_v === null || myTrur[_i] === null) ? null : 100 * _v / myTrur[_i]));
const myDx = myPlus.map((_p, _i) => { if (_p === null || myMinus[_i] === null) return null; const mySum = _p + myMinus[_i]; return Math.abs(_p - myMinus[_i]) / (mySum === 0 ? 1 : mySum); });
const myAdx = myRma(myDx, myAdxLen).map(_v => _v === null ? null : 100 * _v);
const myActive = close.map(() => false);
const myEnded = close.map(() => false);
const myShow = close.map(() => false);
const myBull = close.map(() => false);
const myActivated = close.map(() => false);
let myFlash = false;
for (let myI = 1; myI < close.length; myI += 1) {
	const myA = myAdx[myI], myPa = myAdx[myI - 1];
	const myNn = (_x) => _x !== null && _x !== undefined;
	const myBelow = myNn(myA) && myNn(myPa) && myPa >= myAdxThr && myA < myAdxThr;
	if (myBelow) myFlash = true;
	myActivated[myI] = myBelow;
	const myCrossP = myFlash && myNn(myA) && myNn(myPa) && myNn(myPlus[myI]) && myNn(myPlus[myI - 1]) && myA > myPlus[myI] && myPa <= myPlus[myI - 1];
	const myCrossM = myFlash && myNn(myA) && myNn(myPa) && myNn(myMinus[myI]) && myNn(myMinus[myI - 1]) && myA > myMinus[myI] && myPa <= myMinus[myI - 1];
	const myEnd = myCrossP || myCrossM;
	if (myEnd) myFlash = false;
	myActive[myI] = myFlash;
	myEnded[myI] = myEnd;
	if (myEnded[myI - 1]) { myShow[myI] = true; myBull[myI] = myNn(myPlus[myI]) && myNn(myMinus[myI]) && myPlus[myI] > myMinus[myI]; }
}
// bgcolor is not available: the flash zone is shaded as a band over every bar's high-low range
color_cloud(high.map((_v, _i) => myActive[_i] ? _v : null), low.map((_v, _i) => myActive[_i] ? _v : null), myFlashColor, myFlashColor, 'Flash Up', 'Flash Dn');
paint(myShow.map((_s, _i) => (_s && myBull[_i]) ? constants.icons.triangle_up : null), { name: 'Bullish Mark', style: 'labels_below', color: 'lime' });
paint(myShow.map((_s, _i) => (_s && !myBull[_i]) ? constants.icons.triangle_down : null), { name: 'Bearish Mark', style: 'labels_above', color: 'red' });
register_signal(myActivated, 'Flash Activated');
register_signal(myShow.map((_s, _i) => _s && myBull[_i]), 'Bullish Signal');
register_signal(myShow.map((_s, _i) => _s && !myBull[_i]), 'Bearish Signal');
