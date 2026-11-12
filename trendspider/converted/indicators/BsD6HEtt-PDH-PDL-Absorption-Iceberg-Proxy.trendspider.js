/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : PDH/PDL + Absorption (Iceberg Proxy)
 * Author       : MaHaRaJa81
 * Source URL   : https://www.tradingview.com/script/BsD6HEtt-PDH-PDL-Absorption-Iceberg-Proxy
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : PDH PDL Absorption Proxy_TV
 *
 * Deviations from the original: Reviewed AI draft; prior day H/L from the previous completed daily bar; premarket
 *   04:00-09:30 New York via moment-timezone; ABS labels as icons.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('PDH PDL Absorption Proxy_TV', 'price');
const myMoment = library('moment-timezone');
const myShowPdhl = input.boolean('Show Prior Day H/L', true);
const myShowPm = input.boolean('Show Premarket H/L', false);
const myTolPts = input.number('Level Tolerance Pts', 2.0, { min: 0 });
const myVolLen = input.number('Volume Lookback', 20, { min: 5 });
const myRangeLen = input.number('Range Lookback', 20, { min: 5 });
const myVolMult = input.number('Volume Threshold x', 1.8, { min: 1, step: 0.1 });
const myRangeMult = input.number('Range Threshold x', 0.6, { min: 0.1, step: 0.1 });
const myOnlyAtLevel = input.boolean('Only Near PDH/PDL', true);
const myDaily = await request.history(current.ticker, 'D');
assert(!myDaily.error, 'Error fetching daily data: ' + myDaily.error);
// request.security(D, [high[1], low[1]]): the previous completed day, valid for every chart bar of the next day
const myLand = (_vals) => interpolate_sparse_series(land_points_onto_series(myDaily.time, shift(_vals, 1), time, 'le'), 'constant');
const myPdh = myLand(myDaily.high);
const myPdl = myLand(myDaily.low);
paint(myPdh.map(_v => myShowPdhl ? _v : null), { name: 'PDH', color: 'red', thickness: 1 });
paint(myPdl.map(_v => myShowPdhl ? _v : null), { name: 'PDL', color: 'green', thickness: 1 });
// premarket 04:00-09:30 New York, kept until the next day starts (as the Pine vars)
const myNy = time.map(_t => myMoment.tz(_t * 1000, 'America/New_York'));
const myPmHigh = [];
const myPmLow = [];
let myH = null, myL = null, myDay = null;
for (let myI = 0; myI < close.length; myI += 1) {
	const myKey = myNy[myI].format('YYYYMMDD');
	if (myKey !== myDay) { myH = null; myL = null; myDay = myKey; }
	const myM = myNy[myI].hours() * 60 + myNy[myI].minutes();
	if (myM >= 240 && myM < 570) { myH = myH === null ? high[myI] : Math.max(myH, high[myI]); myL = myL === null ? low[myI] : Math.min(myL, low[myI]); }
	myPmHigh.push(myH);
	myPmLow.push(myL);
}
paint(myPmHigh.map(_v => myShowPm ? _v : null), { name: 'PM High', color: 'orange', style: 'dotted', marker: 'circle' });
paint(myPmLow.map(_v => myShowPm ? _v : null), { name: 'PM Low', color: 'blue', style: 'dotted', marker: 'circle' });
const myAvgVol = sma(volume, myVolLen);
const myRangeS = close.map((_c, _i) => high[_i] - low[_i]);
const myAvgRange = sma(myRangeS, myRangeLen);
const mySignal = close.map((_c, _i) => {
	if (myAvgVol[_i] === null || myAvgRange[_i] === null) return false;
	const myRaw = volume[_i] > myAvgVol[_i] * myVolMult && myRangeS[_i] < myAvgRange[_i] * myRangeMult;
	const myNear = (myPdh[_i] !== null && Math.abs(_c - myPdh[_i]) <= myTolPts) || (myPdl[_i] !== null && Math.abs(_c - myPdl[_i]) <= myTolPts);
	return myOnlyAtLevel ? (myRaw && myNear) : myRaw;
});
paint(mySignal.map(_s => _s ? constants.icons.triangle_down : null), { name: 'Absorption Mark', style: 'labels_above', color: 'fuchsia' });
register_signal(mySignal, 'Absorption Iceberg Detected');
