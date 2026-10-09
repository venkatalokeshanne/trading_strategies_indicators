/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Alpha Trend Hunter | PropTraderz
 * Author       : MonicaPropTraderz
 * Source URL   : https://www.tradingview.com/script/9HlAQbQE-Alpha-Trend-Hunter-PropTraderz
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Alpha Trend Hunter PropTraderz_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine supertrend and ATR hand-rolled (not TrendSpider supertrend);
 *   Buy/Sell text as icons; EMA seeding differs slightly early on.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Alpha Trend Hunter PropTraderz_TV', 'price');
const myHkPeriod = input.number('HA Period', 14, { min: 1, max: 200 });
const mySmoothLen = input.number('Smooth', 2, { min: 1, max: 100 });
const myAtrLen = input.number('ATR Period', 2, { min: 1, max: 200 });
const myStFactor = input.number('Factor', 2.0, { min: 0.01, max: 20, step: 0.01 });
const myN = close.length;
const myHkOpen = ema(open, myHkPeriod);
const myHkClose = ema(close, myHkPeriod);
const myHkHigh = ema(high, myHkPeriod);
const myHkLow = ema(low, myHkPeriod);
const myTyp = close.map((_c, _i) => (myHkOpen[_i] === null || myHkHigh[_i] === null || myHkLow[_i] === null || myHkClose[_i] === null) ? null : (myHkOpen[_i] + myHkHigh[_i] + myHkLow[_i] + myHkClose[_i]) / 4);
// hkPrev := na(hkPrev[1]) ? (hkOpen + hkClose) / 2 : (hkPrev[1] + hkTypical[1]) / 2
const myPrev = [];
for (let myI = 0; myI < myN; myI += 1) {
	if (myHkOpen[myI] === null || myHkClose[myI] === null) { myPrev.push(null); continue; }
	const myPrior = myI > 0 ? myPrev[myI - 1] : null;
	myPrev.push((myPrior === null || myTyp[myI - 1] === null) ? (myHkOpen[myI] + myHkClose[myI]) / 2 : (myPrior + myTyp[myI - 1]) / 2);
}
const myMid = close.map((_c, _i) => {
	if (myPrev[_i] === null || myTyp[_i] === null) return null;
	const myMax = Math.max(myHkHigh[_i], myPrev[_i], myTyp[_i]);
	const myMin = Math.min(myHkLow[_i], myPrev[_i], myTyp[_i]);
	return myMin + (myMax - myMin) / 2;
});
const myTrendLine = ema(myMid, mySmoothLen);
paint(myTrendLine, { name: 'Trend Line', color: close.map((_c, _i) => (myPrev[_i] !== null && myTyp[_i] !== null && myPrev[_i] > myTyp[_i]) ? '#ff0057' : '#00dbff'), thickness: 3 });
// ta.supertrend(factor, atrLen): Pine reference algorithm (direction -1 = up-trend), hand-rolled
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
let myAcc = null, mySeen = 0, mySeed = 0;
const myAtr = myTr.map(_v => {
	if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === myAtrLen) myAcc = mySeed / myAtrLen; return myAcc; }
	myAcc = (myAcc * (myAtrLen - 1) + _v) / myAtrLen; return myAcc;
});
const myStLine = [];
const myStDir = [];
let myUpper = null, myLower = null, myPrevSt = null;
for (let myI = 0; myI < myN; myI += 1) {
	if (myAtr[myI] === null) { myStLine.push(null); myStDir.push(null); continue; }
	const myHl2 = (high[myI] + low[myI]) / 2;
	let myUp = myHl2 + myStFactor * myAtr[myI];
	let myLo = myHl2 - myStFactor * myAtr[myI];
	const myPUp = myUpper, myPLo = myLower;
	myLo = (myPLo === null || myLo > myPLo || close[myI - 1] < myPLo) ? myLo : myPLo;
	myUp = (myPUp === null || myUp < myPUp || close[myI - 1] > myPUp) ? myUp : myPUp;
	let myDir;
	if (myPrevSt === null) myDir = 1;
	else if (myPrevSt === myPUp) myDir = close[myI] > myUp ? -1 : 1;
	else myDir = close[myI] < myLo ? 1 : -1;
	const mySt = myDir === -1 ? myLo : myUp;
	myUpper = myUp; myLower = myLo; myPrevSt = mySt;
	myStLine.push(mySt); myStDir.push(myDir);
}
const myBullLine = myStLine.map((_v, _i) => myStDir[_i] === -1 ? _v : null);
const myBearLine = myStLine.map((_v, _i) => myStDir[_i] === 1 ? _v : null);
paint(myBullLine, { name: 'Bull Trend', color: 'green', thickness: 1 });
paint(myBearLine, { name: 'Bear Trend', color: 'red', thickness: 1 });
const myCandleMid = close.map((_c, _i) => (open[_i] + _c) / 2);
color_cloud(myCandleMid.map((_v, _i) => myStDir[_i] === -1 ? _v : null), myBullLine, 'rgba(0,219,255,0.1)', 'rgba(0,219,255,0.1)', 'Bull Fill Up', 'Bull Fill Dn');
color_cloud(myCandleMid.map((_v, _i) => myStDir[_i] === 1 ? _v : null), myBearLine, 'rgba(255,0,87,0.1)', 'rgba(255,0,87,0.1)', 'Bear Fill Up', 'Bear Fill Dn');
const myHkBull = close.map((_c, _i) => myPrev[_i] !== null && myTyp[_i] !== null && myPrev[_i] < myTyp[_i]);
const myHkBear = close.map((_c, _i) => myPrev[_i] !== null && myTyp[_i] !== null && myPrev[_i] > myTyp[_i]);
const myGoLong = close.map((_c, _i) => myHkBull[_i] && myStDir[_i] === -1);
const myGoShort = close.map((_c, _i) => myHkBear[_i] && myStDir[_i] === 1);
let mySignal = 0;
const myBuy = [];
const mySell = [];
for (let myI = 0; myI < myN; myI += 1) {
	const myPrior = mySignal;
	if (myGoLong[myI] && !(myI > 0 && myGoLong[myI - 1]) && mySignal !== 1) mySignal = 1;
	if (myGoShort[myI] && !(myI > 0 && myGoShort[myI - 1]) && mySignal !== -1) mySignal = -1;
	myBuy.push(mySignal === 1 && mySignal !== myPrior);
	mySell.push(mySignal === -1 && mySignal !== myPrior);
}
paint(myBuy.map(_b => _b ? constants.icons.triangle_up : null), { name: 'Buy Mark', style: 'labels_below', color: '#00dbff' });
paint(mySell.map(_s => _s ? constants.icons.triangle_down : null), { name: 'Sell Mark', style: 'labels_above', color: '#ff0057' });
register_signal(myBuy, 'ATH Buy Signal');
register_signal(mySell, 'ATH Sell Signal');
