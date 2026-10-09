/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Custom Multi-Indicator Suite (Vindi Clone) V6
 * Author       : vinceokafor6
 * Source URL   : https://www.tradingview.com/script/Rq6wZ96P-Custom-Multi-Indicator-Suite-Vindi-Clone-V6
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Vindi Clone Multi Indicator Suite V6_TV
 *
 * Deviations from the original: Reviewed AI draft; the original EARLY BUY/SELL logic can never fire (its position
 *   test compares src with the same stop value on both sides) - reproduced faithfully,
 *   so no buy/sell marks appear; S/R shows only the latest pivot line as in Pine.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Vindi Clone Multi Indicator Suite V6_TV', 'price');
const myFastLen = input.number('Fast Ribbon Length', 20, { min: 1, max: 500 });
const mySlowLen = input.number('Slow Ribbon Length', 50, { min: 1, max: 500 });
const mySrcName = input.select('Signal Source', 'close', ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']);
const myKeyValue = input.number('Key Value', 2.0, { min: 0.1, max: 20, step: 0.5 });
const myAtrPeriod = input.number('ATR Period', 10, { min: 1, max: 100 });
const myPivotLen = input.number('Pivot Strength', 15, { min: 1, max: 200 });
const myMaFast = ema(close, myFastLen);
const myMaSlow = ema(close, mySlowLen);
const myBull = close.map((_c, _i) => myMaFast[_i] !== null && myMaSlow[_i] !== null && myMaFast[_i] > myMaSlow[_i]);
paint(myMaFast, { name: 'Fast Ribbon Line', color: myBull.map(_b => _b ? 'green' : 'red'), thickness: 2 });
paint(myMaSlow, { name: 'Slow Ribbon Line', color: myBull.map(_b => _b ? 'lime' : 'maroon'), thickness: 1 });
color_cloud(myMaFast, myMaSlow, 'rgba(0,200,0,0.2)', 'rgba(220,0,0,0.2)', 'Ribbon Bull', 'Ribbon Bear');
const mySrc = close.map((_c, _i) => {
	if (mySrcName === 'open') return open[_i];
	if (mySrcName === 'high') return high[_i];
	if (mySrcName === 'low') return low[_i];
	if (mySrcName === 'hl2') return (high[_i] + low[_i]) / 2;
	if (mySrcName === 'hlc3') return (high[_i] + low[_i] + _c) / 3;
	if (mySrcName === 'ohlc4') return (open[_i] + high[_i] + low[_i] + _c) / 4;
	return _c;
});
// pine-parity: ta.atr = SMA-seeded RMA of true range
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
let myAcc = null, mySeen = 0, mySeed = 0;
const myAtr = myTr.map(_v => {
	if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === myAtrPeriod) myAcc = mySeed / myAtrPeriod; return myAcc; }
	myAcc = (myAcc * (myAtrPeriod - 1) + _v) / myAtrPeriod; return myAcc;
});
// UT-Bot trailing stop as written in the Pine script. Its position test compares the source with the SAME stop value
// on both sides ("src > stop and src <= stop"), which can never be true, so pos stays 0 and the EARLY BUY/SELL signals never fire.
const myStop = [];
let myPrev = 0;
mySrc.forEach((_s, _i) => {
	if (myAtr[_i] === null) { myStop.push(null); return; }
	const myNLoss = myKeyValue * myAtr[_i];
	let myNew;
	if (_s > myPrev && _s > myPrev) myNew = Math.max(myPrev, _s - myNLoss);
	else if (_s < myPrev && _s < myPrev) myNew = Math.min(myPrev, _s + myNLoss);
	else if (_s > myPrev) myNew = _s - myNLoss;
	else myNew = _s + myNLoss;
	myPrev = myNew;
	myStop.push(myNew);
});
const myPos = mySrc.map((_s, _i) => (myStop[_i] !== null && _s > myStop[_i] && _s <= myStop[_i]) ? 1 : ((myStop[_i] !== null && _s < myStop[_i] && _s >= myStop[_i]) ? -1 : 0));
const myEmaSig = ema(mySrc, 1);
const myBuy = close.map((_c, _i) => _i > 0 && myStop[_i] !== null && myStop[_i - 1] !== null && myEmaSig[_i] > myStop[_i] && myEmaSig[_i - 1] <= myStop[_i - 1] && myPos[_i] === 1);
const mySell = close.map((_c, _i) => _i > 0 && myStop[_i] !== null && myStop[_i - 1] !== null && myEmaSig[_i] < myStop[_i] && myEmaSig[_i - 1] >= myStop[_i - 1] && myPos[_i] === -1);
paint(myBuy.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Early Buy Mark', style: 'labels_below', color: 'green' });
paint(mySell.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Early Sell Mark', style: 'labels_above', color: 'red' });
register_signal(myBuy, 'Early Buy Signal');
register_signal(mySell, 'Early Sell Signal');
// support / resistance: only the latest pivot line exists in Pine (older ones are deleted), drawn from its pivot bar
const myPivotAt = (_src, _i, _isHigh) => {
	const myP = _i - myPivotLen;
	if (myP - myPivotLen < 0) return false;
	for (let myK = myP - myPivotLen; myK <= _i; myK += 1) {
		if (myK === myP) continue;
		if (_isHigh ? (myK < myP ? !(_src[myP] > _src[myK]) : !(_src[myP] >= _src[myK])) : (myK < myP ? !(_src[myP] < _src[myK]) : !(_src[myP] <= _src[myK]))) return false;
	}
	return true;
};
let myResI = null, myResV = null, mySupI = null, mySupV = null;
for (let myI = 0; myI < close.length; myI += 1) {
	if (myPivotAt(high, myI, true)) { myResI = myI - myPivotLen; myResV = high[myResI]; }
	if (myPivotAt(low, myI, false)) { mySupI = myI - myPivotLen; mySupV = low[mySupI]; }
}
paint(close.map((_c, _i) => (myResI !== null && _i >= myResI) ? myResV : null), { name: 'Resistance Level', color: 'red', thickness: 1 });
paint(close.map((_c, _i) => (mySupI !== null && _i >= mySupI) ? mySupV : null), { name: 'Support Level', color: 'blue', thickness: 1 });
