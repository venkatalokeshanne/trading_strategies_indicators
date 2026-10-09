/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : KPRSI – V1 DivSell Only
 * Author       : MaximusP777
 * Source URL   : https://www.tradingview.com/script/zuv28rUD-kprsi-v1-max-bo
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : KPRSI DivSell DivBuy V1_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact RSI; pivots hand-rolled with price/RSI taken at the
 *   pivot bar (the draft used the confirmation bar); divergence lines and data-window
 *   plots not carried over.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('KPRSI DivSell DivBuy V1_TV', 'price');
const myEmaLen = input.number('EMA Length', 20, { min: 1, max: 500 });
const myRsiLen = input.number('RSI Length', 14, { min: 2, max: 100 });
const myPivLeft = input.number('Pivot Left', 5, { min: 1, max: 50 });
const myPivRight = input.number('Pivot Right', 5, { min: 1, max: 50 });
const mySlopeSens = input.number('EMA Slope Thresh %', 0.05, { min: 0, max: 10, step: 0.01 });
const myTolerance = input.number('Price Equality Tol %', 0.2, { min: 0, max: 10, step: 0.05 });
const myEma20 = ema(close, myEmaLen);
// pine-parity: ta.rsi uses SMA-seeded RMA of gains/losses
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
const myG = myRma(close.map((_c, _i) => _i === 0 ? null : Math.max(_c - close[_i - 1], 0)), myRsiLen);
const myL = myRma(close.map((_c, _i) => _i === 0 ? null : Math.max(close[_i - 1] - _c, 0)), myRsiLen);
const myRsi = myG.map((_g, _i) => (_g === null || myL[_i] === null) ? null : (myL[_i] === 0 ? 100 : 100 - 100 / (1 + _g / myL[_i])));
const myPivotAt = (_src, _i, _isHigh) => {
	const myP = _i - myPivRight;
	if (myP - myPivLeft < 0) return false;
	for (let myK = myP - myPivLeft; myK <= _i; myK += 1) {
		if (myK === myP) continue;
		if (_isHigh ? (myK < myP ? !(_src[myP] > _src[myK]) : !(_src[myP] >= _src[myK])) : (myK < myP ? !(_src[myP] < _src[myK]) : !(_src[myP] <= _src[myK]))) return false;
	}
	return true;
};
const mySell = close.map(() => false);
const myBuy = close.map(() => false);
const myBearDivS = close.map(() => false);
const myBullDivS = close.map(() => false);
let myPH = null, myLH = null, myPL = null, myLL = null;
let myLastSellBar = null, myLastBuyBar = null;
for (let myI = 0; myI < close.length; myI += 1) {
	const myP = myI - myPivRight;
	if (myPivotAt(high, myI, true)) { myPH = myLH; myLH = { price: high[myP], rsi: myRsi[myP], bar: myP }; }
	if (myPivotAt(low, myI, false)) { myPL = myLL; myLL = { price: low[myP], rsi: myRsi[myP], bar: myP }; }
	const myEmaSlope = (myI > 0 && myEma20[myI] !== null && myEma20[myI - 1]) ? (myEma20[myI] - myEma20[myI - 1]) / myEma20[myI - 1] * 100 : 0;
	const myEmaUp = myEmaSlope > mySlopeSens, myEmaDown = myEmaSlope < -mySlopeSens;
	const myBull = myLL !== null && myPL !== null && myLL.rsi !== null && myPL.rsi !== null && ((myLL.price < myPL.price) || Math.abs((myLL.price - myPL.price) / myPL.price) * 100 <= myTolerance) && myLL.rsi > myPL.rsi;
	const myBear = myLH !== null && myPH !== null && myLH.rsi !== null && myPH.rsi !== null && ((myLH.price > myPH.price) || Math.abs((myLH.price - myPH.price) / myPH.price) * 100 <= myTolerance) && myLH.rsi < myPH.rsi;
	myBearDivS[myI] = myBear; myBullDivS[myI] = myBull;
	const myDivSell = myBear && myEmaDown && myEma20[myI] !== null && close[myI] < myEma20[myI];
	const myDivBuy = myBull && myEmaUp && myEma20[myI] !== null && close[myI] > myEma20[myI];
	const myNewSell = myDivSell && (myLastSellBar === null || myLastSellBar !== myLH.bar);
	const myNewBuy = myDivBuy && (myLastBuyBar === null || myLastBuyBar !== myLL.bar);
	if (myNewSell) myLastSellBar = myLH.bar;
	if (myNewBuy) myLastBuyBar = myLL.bar;
	const myStrength = (myPH !== null && myLH !== null && myPH.rsi !== null && myLH.rsi !== null) ? myPH.rsi - myLH.rsi : 0;
	const myBody = open[myI] !== 0 ? Math.abs(close[myI] - open[myI]) / open[myI] * 100 : 0;
	mySell[myI] = myNewSell && myStrength >= 1.5 && myBody <= 2.0;
	myBuy[myI] = myNewBuy;
}
paint(myEma20, { name: 'EMA 20', color: 'orange', thickness: 2 });
paint(mySell.map(_f => _f ? constants.icons.triangle_down : null), { name: 'DivSell Mark', style: 'labels_above', color: 'red' });
paint(myBuy.map(_f => _f ? constants.icons.triangle_up : null), { name: 'DivBuy Mark', style: 'labels_below', color: 'teal' });
register_signal(mySell, 'Filtered Sell');
register_signal(myBuy, 'New Buy');
register_signal(myBearDivS, 'Bearish Divergence');
register_signal(myBullDivS, 'Bullish Divergence');
