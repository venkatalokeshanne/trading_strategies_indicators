/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Directional Movement Index Improved
 * Author       : SRP7017
 * Source URL   : https://www.tradingview.com/script/3KeGCOZy-Directional-Movement-Index-SRP7017
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Directional Movement Index Improved_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact RMA and TR; dashed hline styles not available.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Directional Movement Index Improved_TV', 'lower', { decimals: 4 });
const myAdxLen = input.number('ADX Smoothing', 14, { min: 1 });
const myDiLen = input.number('DI Length', 28, { min: 1 });
// pine-parity: ta.rma is SMA-seeded (reference/02), so wildma() is not used
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null || _v === undefined || isNaN(_v)) return myAcc;
		if (myAcc === null) {
			mySeed += _v; mySeen += 1;
			if (mySeen === _n) myAcc = mySeed / _n;
			return myAcc;
		}
		myAcc = (myAcc * (_n - 1) + _v) / _n;
		return myAcc;
	});
};
const myTr = high.map((_h, _i) => _i === 0 ? null : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
const myUp = sub(high, shift(high, 1));
const myDown = sub(shift(low, 1), low);
const myPlusDM = for_every(myUp, myDown, (_u, _d) => (_u === null || _d === null) ? null : ((_u > _d && _u > 0) ? _u : 0));
const myMinusDM = for_every(myUp, myDown, (_u, _d) => (_u === null || _d === null) ? null : ((_d > _u && _d > 0) ? _d : 0));
const myTrur = myRma(myTr, myDiLen);
const myPlusRma = myRma(myPlusDM, myDiLen);
const myMinusRma = myRma(myMinusDM, myDiLen);
// fixnan: carry the last valid value forward
const myFixNan = (_s) => { let myLast = null; return _s.map(_v => { if (_v !== null && !isNaN(_v)) myLast = _v; return myLast; }); };
const myPlus = myFixNan(myPlusRma.map((_v, _i) => (_v === null || myTrur[_i] === null) ? null : 100 * _v / myTrur[_i]));
const myMinus = myFixNan(myMinusRma.map((_v, _i) => (_v === null || myTrur[_i] === null) ? null : 100 * _v / myTrur[_i]));
const myDx = myPlus.map((_p, _i) => {
	if (_p === null || myMinus[_i] === null) return null;
	const mySum = _p + myMinus[_i];
	return Math.abs(_p - myMinus[_i]) / (mySum === 0 ? 1 : mySum);
});
const myAdx = myRma(myDx, myAdxLen).map(_v => _v === null ? null : 100 * _v);
const myRising = (_s) => _s.map((_v, _i) => _i > 0 && _v !== null && _s[_i - 1] !== null && _v > _s[_i - 1]);
const myColorAdx = myRising(myAdx).map(_r => _r ? '#ffff00' : 'rgba(255,170,0,0.5)');
const myColorPlus = myRising(myPlus).map(_r => _r ? '#00ff00' : '#006400');
const myColorMinus = myRising(myMinus).map(_r => _r ? '#ff0000' : '#800000');
paint(myAdx, { name: 'ADX Dynamic', color: myColorAdx, thickness: 3 });
paint(myPlus, { name: 'Plus DI Dynamic', color: myColorPlus, thickness: 2 });
paint(myMinus, { name: 'Minus DI Dynamic', color: myColorMinus, thickness: 2 });
paint(horizontal_line(10), { name: 'Threshold 10', color: '#00ff2f' });
paint(horizontal_line(20), { name: 'Threshold 20', color: '#f2fa00' });
paint(horizontal_line(30), { name: 'Threshold 30', color: '#ffffff' });
const myCrossUp = myPlus.map((_p, _i) => _i > 0 && _p !== null && myMinus[_i] !== null && myPlus[_i - 1] !== null && myMinus[_i - 1] !== null && _p > myMinus[_i] && myPlus[_i - 1] <= myMinus[_i - 1]);
const myCrossDown = myPlus.map((_p, _i) => _i > 0 && _p !== null && myMinus[_i] !== null && myPlus[_i - 1] !== null && myMinus[_i - 1] !== null && _p < myMinus[_i] && myPlus[_i - 1] >= myMinus[_i - 1]);
register_signal(myCrossUp, 'DMI Bullish Cross');
register_signal(myCrossDown, 'DMI Bearish Cross');
register_signal(myRising(myAdx), 'ADX Rising');
