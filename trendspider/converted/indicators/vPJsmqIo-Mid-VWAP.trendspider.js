/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Mid / VWAP
 * Author       : silas7467
 * Source URL   : https://www.tradingview.com/script/vPJsmqIo-Mid-VWAP
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Mid VWAP_TV
 *
 * Deviations from the original: Calendar anchors use exchange time; sub-day buckets use UTC boundaries; session
 *   timezone input and period-start tint dropped
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Mid VWAP_TV', 'price');
const myAnchor = input.select('Anchor period', 'Day', ['Chart', 'Minute', 'Half hour', 'Hour', 'Four hour', 'Eight hour', 'RTH', 'RTH Stretch', 'Euro', 'Day', 'Week', 'Month', 'Quarter', 'Opt Exp', 'Year', 'Bar']);
const myRthStart = input.number('RTH Start HHMM', 930, { min: 0, max: 2359 });
const myRthEnd = input.number('RTH End HHMM', 1600, { min: 0, max: 2359 });
const myEuroHhmm = input.number('Euro Open HHMM', 300, { min: 0, max: 2359 });
const mySrcName = input.select('Source', 'hlc3', ['close', 'hl2', 'hlc3', 'ohlc4', 'open', 'high', 'low']);
const myBreak = input.boolean('Break at boundary', true);
const myShowCloud = input.boolean('Mid VWAP cloud', true);
const myOpac = input.number('Cloud transparency', 82, { min: 0, max: 100 });
const myN = close.length;
const myMin = (_h) => Math.floor(_h / 100) * 60 + (_h % 100);
// session and calendar keys are in exchange time (time_of)
const myT = time.map(_t => time_of(_t));
const myMod = myT.map(_x => _x.hours * 60 + _x.minutes);
const myInRth = myMod.map(_m => _m >= myMin(myRthStart) && _m < myMin(myRthEnd));
const myInEuro = myMod.map(_m => _m === myMin(myEuroHhmm));
// Pine dayofweek (1 = Sunday) from TrendSpider dayOfWeek (1 = Monday ... 7 = Sunday)
const myOpex = (_x) => {
	const myFirstDowTs = (((_x.dayOfWeek - 1 - (_x.dayOfMonth - 1)) % 7) + 7) % 7 + 1;
	const myPineDow = myFirstDowTs % 7 + 1;
	const myFirstFriday = 1 + ((6 - myPineDow + 7) % 7);
	return _x.year * 12 + _x.month + (_x.dayOfMonth > myFirstFriday + 14 ? 1 : 0);
};
const myNew = close.map((_c, _i) => {
	if (_i === 0) return true;
	const myC = myT[_i], myP = myT[_i - 1];
	const myRthOpen = myInRth[_i] && !myInRth[_i - 1], myRthClose = !myInRth[_i] && myInRth[_i - 1], myEuroOpen = myInEuro[_i] && !myInEuro[_i - 1];
	const myBucket = (_s) => Math.floor(time[_i] / _s) !== Math.floor(time[_i - 1] / _s);
	switch (myAnchor) {
		case 'Chart': return false;
		case 'Bar': return true;
		case 'Minute': return myBucket(60);
		case 'Half hour': return myBucket(1800);
		case 'Hour': return myBucket(3600);
		case 'Four hour': return myBucket(14400);
		case 'Eight hour': return myBucket(28800);
		case 'RTH': return myRthOpen || myRthClose;
		case 'RTH Stretch': return myRthOpen;
		case 'Euro': return myRthOpen || myRthClose || myEuroOpen;
		case 'Day': return myC.year !== myP.year || myC.month !== myP.month || myC.dayOfMonth !== myP.dayOfMonth;
		case 'Week': return myC.dayOfWeek < myP.dayOfWeek || (time[_i] - time[_i - 1]) > 6 * 86400;
		case 'Month': return myC.year !== myP.year || myC.month !== myP.month;
		case 'Quarter': return myC.year !== myP.year || Math.floor(myC.month / 3) !== Math.floor(myP.month / 3);
		case 'Opt Exp': return myOpex(myC) !== myOpex(myP);
		case 'Year': return myC.year !== myP.year;
		default: return false;
	}
});
const mySrc = close.map((_c, _i) => {
	if (mySrcName === 'open') return open[_i];
	if (mySrcName === 'high') return high[_i];
	if (mySrcName === 'low') return low[_i];
	if (mySrcName === 'hl2') return (high[_i] + low[_i]) / 2;
	if (mySrcName === 'ohlc4') return (open[_i] + high[_i] + low[_i] + _c) / 4;
	if (mySrcName === 'hlc3') return (high[_i] + low[_i] + _c) / 3;
	return _c;
});
let myVs = null, myVps = 0, myHi = 0, myLo = 0;
const myVwap = [], myMid = [];
for (let myI = 0; myI < myN; myI += 1) {
	if (myNew[myI] || myVs === null) { myVs = volume[myI]; myVps = volume[myI] * mySrc[myI]; myHi = high[myI]; myLo = low[myI]; }
	else { myVs += volume[myI]; myVps += volume[myI] * mySrc[myI]; myHi = Math.max(myHi, high[myI]); myLo = Math.min(myLo, low[myI]); }
	myVwap.push(myVs > 0 ? myVps / myVs : null); myMid.push((myHi + myLo) / 2);
}
const myVp = myVwap.map((_v, _i) => (myBreak && myNew[_i]) ? null : _v), myMp = myMid.map((_v, _i) => (myBreak && myNew[_i]) ? null : _v);
paint(myVp, { name: 'VWAP', color: '#e8c84a', thickness: 2 });
paint(myMp, { name: 'Mid', color: 'gray' });
const myAlpha = (100 - myOpac) / 100;
color_cloud(myShowCloud ? myVp : myVp.map(() => null), myShowCloud ? myMp : myMp.map(() => null), 'rgba(38,166,154,' + myAlpha + ')', 'rgba(239,83,80,' + myAlpha + ')', 'VWAP Above Mid', 'VWAP Below Mid');
register_signal(myVwap.map((_v, _i) => _v !== null && _v > myMid[_i]), 'VWAP Above Mid Sig');
register_signal(myVwap.map((_v, _i) => _v !== null && _v < myMid[_i]), 'VWAP Below Mid Sig');
register_signal(myNew, 'New Anchor Period');
