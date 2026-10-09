/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : ROC & RSI Toleranslı Al-Sat İndikatörü © S_SANLI
 * Author       : S_SANLI
 * Source URL   : https://www.tradingview.com/script/oSx9IHxI
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : ROC RSI Tolerance Signal_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact RSI and ROC; AL/SAT text as triangle icons.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('ROC RSI Tolerance Signal_TV', 'price');
const myRocLength = input.number('ROC Length', 9, { min: 1, max: 500 });
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 500 });
const myRsiMaLength = input.number('RSI MA Length', 14, { min: 1, max: 500 });
const myTolerance = input.number('Tolerance Bars', 2, { min: 0, max: 500 });
// pine-parity: ta.rsi uses SMA-seeded RMA; ta.roc = 100 * (x - x[n]) / x[n]
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
const myG = myRma(close.map((_c, _i) => _i === 0 ? null : Math.max(_c - close[_i - 1], 0)), myRsiLength);
const myL = myRma(close.map((_c, _i) => _i === 0 ? null : Math.max(close[_i - 1] - _c, 0)), myRsiLength);
const myRsi = myG.map((_g, _i) => (_g === null || myL[_i] === null) ? null : (myL[_i] === 0 ? 100 : 100 - 100 / (1 + _g / myL[_i])));
const myRsiMa = myRsi.map((_v, _i) => {
	if (_i < myRsiMaLength - 1) return null;
	let mySum = 0;
	for (let myK = _i - myRsiMaLength + 1; myK <= _i; myK += 1) { if (myRsi[myK] === null) return null; mySum += myRsi[myK]; }
	return mySum / myRsiMaLength;
});
const myRoc = close.map((_c, _i) => _i < myRocLength ? null : 100 * (_c - close[_i - myRocLength]) / close[_i - myRocLength]);
const myNn = (_a) => _a !== null && _a !== undefined;
const myRocUp = myRoc.map((_v, _i) => _i > 0 && myNn(_v) && myNn(myRoc[_i - 1]) && myRoc[_i - 1] <= 0 && _v > 0);
const myRocDn = myRoc.map((_v, _i) => _i > 0 && myNn(_v) && myNn(myRoc[_i - 1]) && myRoc[_i - 1] >= 0 && _v < 0);
const myRsiUp = myRsi.map((_v, _i) => _i > 0 && myNn(_v) && myNn(myRsiMa[_i]) && myNn(myRsi[_i - 1]) && myNn(myRsiMa[_i - 1]) && myRsi[_i - 1] <= myRsiMa[_i - 1] && _v > myRsiMa[_i]);
const myRsiDn = myRsi.map((_v, _i) => _i > 0 && myNn(_v) && myNn(myRsiMa[_i]) && myNn(myRsi[_i - 1]) && myNn(myRsiMa[_i - 1]) && myRsi[_i - 1] >= myRsiMa[_i - 1] && _v < myRsiMa[_i]);
// ta.barssince: 0 on the bar where the condition is true
const mySince = (_flags) => { let myLast = null; return _flags.map((_f, _i) => { if (_f) myLast = _i; return myLast === null ? myTolerance + 1 : _i - myLast; }); };
const mySRocUp = mySince(myRocUp), mySRocDn = mySince(myRocDn), mySRsiUp = mySince(myRsiUp), mySRsiDn = mySince(myRsiDn);
const myBuy = close.map((_c, _i) => (myRocUp[_i] && mySRsiUp[_i] <= myTolerance) || (myRsiUp[_i] && mySRocUp[_i] <= myTolerance));
const mySell = close.map((_c, _i) => (myRocDn[_i] && mySRsiDn[_i] <= myTolerance) || (myRsiDn[_i] && mySRocDn[_i] <= myTolerance));
paint(myBuy.map(_b => _b ? constants.icons.triangle_up : null), { name: 'Buy Mark', style: 'labels_below', color: 'green' });
paint(mySell.map(_s => _s ? constants.icons.triangle_down : null), { name: 'Sell Mark', style: 'labels_above', color: 'red' });
register_signal(myBuy, 'Buy Signal Series');
register_signal(mySell, 'Sell Signal Series');
