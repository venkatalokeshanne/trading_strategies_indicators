/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : O.Insidebox Mapper
 * Author       : AmmattinaTreidaus
 * Source URL   : https://www.tradingview.com/script/aq6QGBPp-O-Insidebox-Mapper
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : O.Insidebox Mapper_TV
 *
 * Deviations from the original: Reviewed AI draft; Asian session fixed to a UTC hour window; box drawn as a cloud
 *   over the session's final range; X marker as triangle icon; wick line not drawn.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('O.Insidebox Mapper_TV', 'price');
const myShowBox = input.boolean('Show Session Range', true);
const myInsideColor = input.color('Inside Bar Color', '#FFFF00');
const myShowMarker = input.boolean('Show Marker', true);
const myStartHour = input.number('Asian Start Hour UTC', 0, { min: 0, max: 23 });
const myEndHour = input.number('Asian End Hour UTC', 8, { min: 0, max: 24 });
// time is epoch seconds (UTC): session 00:00-08:00 UTC by default
const myInSession = time.map(_t => { const myH = Math.floor((_t % 86400) / 3600); return myH >= myStartHour && myH < myEndHour; });
const myInside = close.map((_c, _i) => _i > 0 && high[_i] <= high[_i - 1] && low[_i] >= low[_i - 1]);
const myTarget = myInside.map((_b, _i) => _b && myInSession[_i]);
color_candles(myTarget.map(_t => _t ? myInsideColor : null));
paint(myTarget.map(_t => (myShowMarker && _t) ? constants.icons.triangle_up : null), { name: 'Inside Bar Marker', style: 'labels_below', color: myInsideColor });
// session range: final high/low of each session shown across that session's bars
const myBoxHigh = series_of(null);
const myBoxLow = series_of(null);
let myStart = null;
for (let myI = 0; myI <= close.length; myI += 1) {
	const myIn = myI < close.length && myInSession[myI];
	if (myIn && myStart === null) myStart = myI;
	if (!myIn && myStart !== null) {
		let myHi = -Infinity, myLo = Infinity;
		for (let myK = myStart; myK < myI; myK += 1) { myHi = Math.max(myHi, high[myK]); myLo = Math.min(myLo, low[myK]); }
		for (let myK = myStart; myK < myI; myK += 1) { myBoxHigh[myK] = myShowBox ? myHi : null; myBoxLow[myK] = myShowBox ? myLo : null; }
		myStart = null;
	}
}
color_cloud(myBoxHigh, myBoxLow, 'rgba(41,98,255,0.25)', 'rgba(41,98,255,0.25)', 'Asian Up', 'Asian Dn');
register_signal(myTarget, 'Inside Bar In Asian Session');
register_signal(myInSession.map((_s, _i) => _s && !(_i > 0 && myInSession[_i - 1])), 'New Asian Session Started');
