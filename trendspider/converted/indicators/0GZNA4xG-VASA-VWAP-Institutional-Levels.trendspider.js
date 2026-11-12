/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : VASA VWAP + Institutional Levels
 * Author       : VASATrendAI
 * Source URL   : https://www.tradingview.com/script/0GZNA4xG-VASA-VWAP-Institutional-Levels
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : VASA VWAP Institutional Levels_TV
 *
 * Deviations from the original: Reviewed AI draft; anchors by exchange-time day/week/month; colour inputs fixed;
 *   fills as clouds.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('VASA VWAP Institutional Levels_TV', 'price');
const myAnchorTab = input.tab('Anchor and Source');
const myAnchor = myAnchorTab.select('Anchor period', 'Session', ['Session', 'Week', 'Month']);
const mySrcName = myAnchorTab.select('Source', 'hlc3', ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']);
const myBandsTab = input.tab('Bands');
const myShow1 = myBandsTab.boolean('Show 1 sigma band', true);
const myShow2 = myBandsTab.boolean('Show 2 sigma band', true);
const myMult1 = myBandsTab.number('1 sigma mult', 1.0, { min: 0.1, max: 10, step: 0.1 });
const myMult2 = myBandsTab.number('2 sigma mult', 2.0, { min: 0.1, max: 10, step: 0.1 });
const myFillOn = myBandsTab.boolean('Shade bands', true);
const mySrc = close.map((_c, _i) => {
	if (mySrcName === 'open') return open[_i];
	if (mySrcName === 'high') return high[_i];
	if (mySrcName === 'low') return low[_i];
	if (mySrcName === 'hl2') return (high[_i] + low[_i]) / 2;
	if (mySrcName === 'hlc3') return (high[_i] + low[_i] + _c) / 3;
	if (mySrcName === 'ohlc4') return (open[_i] + high[_i] + low[_i] + _c) / 4;
	return _c;
});
// anchor key per bar (exchange time): day, Monday-aligned week, or month
const myKey = time.map(_t => {
	const myX = time_of(_t);
	if (myAnchor === 'Week') return Math.floor((Math.floor(_t / 86400) - 4) / 7);
	if (myAnchor === 'Month') return myX.month;
	return myX.month * 100 + myX.dayOfMonth;
});
const myVwap = series_of(null);
const myDev = series_of(null);
let mySumPV = 0, mySumV = 0, mySumPV2 = 0;
for (let myI = 0; myI < close.length; myI += 1) {
	if (myI === 0 || myKey[myI] !== myKey[myI - 1]) { mySumPV = 0; mySumV = 0; mySumPV2 = 0; }
	mySumPV += mySrc[myI] * volume[myI];
	mySumV += volume[myI];
	mySumPV2 += mySrc[myI] * mySrc[myI] * volume[myI];
	if (mySumV !== 0) {
		const myV = mySumPV / mySumV;
		myVwap[myI] = myV;
		myDev[myI] = Math.sqrt(Math.max(mySumPV2 / mySumV - myV * myV, 0));
	}
}
const myBand = (_m, _sign) => myVwap.map((_v, _i) => _v === null ? null : _v + _sign * _m * myDev[_i]);
const myU1 = myBand(myMult1, 1);
const myL1 = myBand(myMult1, -1);
const myU2 = myBand(myMult2, 1);
const myL2 = myBand(myMult2, -1);
const myGate = (_s, _show) => _s.map(_v => _show ? _v : null);
paint(myVwap, { name: 'VWAP', color: '#2563eb', thickness: 2 });
paint(myGate(myU1, myShow1), { name: 'Upper 1 sigma', color: '#3b82f6' });
paint(myGate(myL1, myShow1), { name: 'Lower 1 sigma', color: '#3b82f6' });
paint(myGate(myU2, myShow2), { name: 'Upper 2 sigma', color: '#93c5fd' });
paint(myGate(myL2, myShow2), { name: 'Lower 2 sigma', color: '#93c5fd' });
const myShade = 'rgba(59,130,246,0.12)';
color_cloud(myGate(myU1, myShow1 && myFillOn), myGate(myL1, myShow1 && myFillOn), myShade, myShade, 'Fill 1 Up', 'Fill 1 Dn');
color_cloud(myGate(myU2, myShow2 && myFillOn), myGate(myU1, myShow2 && myFillOn), myShade, myShade, 'Fill 2U Up', 'Fill 2U Dn');
color_cloud(myGate(myL1, myShow2 && myFillOn), myGate(myL2, myShow2 && myFillOn), myShade, myShade, 'Fill 2L Up', 'Fill 2L Dn');
const myPrevClose = shift(close, 1);
const myPrevVwap = shift(myVwap, 1);
register_signal(for_every(close, myVwap, myPrevClose, myPrevVwap, (_c, _v, _pc, _pv) => _v !== null && _pv !== null && _c > _v && _pc <= _pv), 'Price crossed above VWAP');
register_signal(for_every(close, myVwap, myPrevClose, myPrevVwap, (_c, _v, _pc, _pv) => _v !== null && _pv !== null && _c < _v && _pc >= _pv), 'Price crossed below VWAP');
