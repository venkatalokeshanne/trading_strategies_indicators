/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Closing Pattern
 * Author       : ignatik_zalupatik
 * Source URL   : https://www.tradingview.com/script/8jyrVGDc-Closing-Pattern
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Closing Pattern_TV
 *
 * Deviations from the original: Reviewed AI draft; direction table via paint_overlay (last values); alert-timeframe
 *   signals landed on the first chart bar of each alert bar; triangle icons.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Closing Pattern_TV', 'price');
const myLookback = input.number('Direction lookback', 50, { min: 5, max: 500 });
const myAlertTf = input.select('Alert timeframe', '240', ['1', '5', '15', '30', '60', '240', 'D']);
const myDirInput = input.select('Alert direction', 'Both', ['Below', 'Above', 'Both']);
const myBelowOn = myDirInput === 'Below' || myDirInput === 'Both';
const myAboveOn = myDirInput === 'Above' || myDirInput === 'Both';
const [myD1, my12H, myAlert] = await Promise.all([
	request.history(current.ticker, 'D'),
	request.history(current.ticker, '720'),
	request.history(current.ticker, myAlertTf)
]);
assert(!myD1.error, 'Error fetching D1 data: ' + myD1.error);
assert(!my12H.error, 'Error fetching 12H data: ' + my12H.error);
assert(!myAlert.error, 'Error fetching alert timeframe data: ' + myAlert.error);
// f_scanDirection: look back through completed bars for the first close beyond the high/low of the bar before it
const myDirOf = (_d, _j) => {
	for (let myI = 0; myI < myLookback; myI += 1) {
		const myC = _j - (myI + 1), myH = _j - (myI + 2);
		if (myH < 0) return 0;
		if (_d.close[myC] > _d.high[myH]) return 1;
		if (_d.close[myC] < _d.low[myH]) return -1;
	}
	return 0;
};
const myDirD1 = myDirOf(myD1, myD1.close.length - 1);
const myDir12H = myDirOf(my12H, my12H.close.length - 1);
const myTxt = (_d) => _d === 1 ? 'Long' : (_d === -1 ? 'Short' : 'Neutral');
const myCol = (_d) => _d === 1 ? '#4CAF4F' : (_d === -1 ? '#F44336' : '#cccccc');
paint_overlay('Direction Table', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'D1 Direction', color: 'white', background_color: 'rgba(0,0,0,0.5)' }, { text: myTxt(myDirD1), color: myCol(myDirD1), background_color: 'rgba(0,0,0,0.5)' }] },
		{ cells: [{ text: '12H Direction', color: 'white', background_color: 'rgba(0,0,0,0.5)' }, { text: myTxt(myDir12H), color: myCol(myDir12H), background_color: 'rgba(0,0,0,0.5)' }] }
	]
});
// alert timeframe: on the first chart bar of each alert-timeframe bar, compare close[1] with low[2] / high[2] of that timeframe
const mySameTf = current.resolution === myAlertTf;
const myHtfBelow = myAlert.time.map((_t, _k) => (_k >= 2 && myAlert.close[_k - 1] < myAlert.low[_k - 2]) ? 1 : 0);
const myHtfAbove = myAlert.time.map((_t, _k) => (_k >= 2 && myAlert.close[_k - 1] > myAlert.high[_k - 2]) ? 1 : 0);
const myLandedBelow = land_points_onto_series(myAlert.time, myHtfBelow, time, 'ge');
const myLandedAbove = land_points_onto_series(myAlert.time, myHtfAbove, time, 'ge');
const myBelow = close.map((_c, _i) => mySameTf ? (myBelowOn && _i > 0 && _c < low[_i - 1]) : (myBelowOn && myLandedBelow[_i] === 1));
const myAbove = close.map((_c, _i) => mySameTf ? (myAboveOn && _i > 0 && _c > high[_i - 1]) : (myAboveOn && myLandedAbove[_i] === 1));
paint(myBelow.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Close Below Mark', style: 'labels_below', color: 'red' });
paint(myAbove.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Close Above Mark', style: 'labels_above', color: 'green' });
register_signal(myBelow, 'Close Below Previous Range');
register_signal(myAbove, 'Close Above Previous Range');
