/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Cambist Swing High / Low
 * Author       : Mansoor_A56
 * Source URL   : https://www.tradingview.com/script/PUT7aIKF-Cambist-Swing-High-Low
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Cambist Swing High Low_TV
 *
 * Deviations from the original: Reviewed AI draft; pivots hand-rolled; lines start on the pivot bar and end at the
 *   breaking bar or when replaced, as in Pine; style options dropped; labels on the last
 *   30 pivots.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Cambist Swing High Low_TV', 'price');
const myLen = input.number('Swing Lookback', 5, { min: 1, max: 200 });
const myShowLabels = input.boolean('Show Swing Labels', true);
const myN = close.length;
// ta.pivothigh/pivotlow(len, len): confirmed `len` bars after the pivot bar
const myPivotAt = (_src, _i, _isHigh) => {
	const myP = _i - myLen;
	if (myP - myLen < 0) return false;
	for (let myK = myP - myLen; myK <= _i; myK += 1) {
		if (myK === myP) continue;
		if (_isHigh ? (myK < myP ? !(_src[myP] > _src[myK]) : !(_src[myP] >= _src[myK])) : (myK < myP ? !(_src[myP] < _src[myK]) : !(_src[myP] <= _src[myK]))) return false;
	}
	return true;
};
const myHighLine = close.map(() => null);
const myLowLine = close.map(() => null);
const myNewHigh = close.map(() => false);
const myNewLow = close.map(() => false);
const myHighBroken = close.map(() => false);
const myLowBroken = close.map(() => false);
const myHighPivots = [];
const myLowPivots = [];
// a line starts on the pivot bar and ends at the bar that breaks it, or at the confirmation bar once a newer pivot replaces it
const myTrack = (_isHigh, _lineSeries, _newSeries, _brokenSeries, _list) => {
	let myActive = null;
	for (let myI = 0; myI < myN; myI += 1) {
		if (myPivotAt(_isHigh ? high : low, myI, _isHigh)) {
			if (myActive !== null) { for (let myK = myActive.start; myK <= myActive.conf; myK += 1) _lineSeries[myK] = myActive.price; }
			myActive = { start: myI - myLen, conf: myI, price: (_isHigh ? high : low)[myI - myLen] };
			_newSeries[myI] = true;
			_list.push(myActive.start);
		}
		if (myActive !== null && (_isHigh ? close[myI] > myActive.price : close[myI] < myActive.price)) {
			for (let myK = myActive.start; myK <= myI; myK += 1) _lineSeries[myK] = myActive.price;
			_brokenSeries[myI] = true;
			myActive = null;
		}
	}
	if (myActive !== null) { for (let myK = myActive.start; myK < myN; myK += 1) _lineSeries[myK] = myActive.price; }
};
myTrack(true, myHighLine, myNewHigh, myHighBroken, myHighPivots);
myTrack(false, myLowLine, myNewLow, myLowBroken, myLowPivots);
const myHighPainted = paint(myHighLine, { name: 'Swing High', color: '#1E88FF', thickness: 3 });
const myLowPainted = paint(myLowLine, { name: 'Swing Low', color: '#FF1744', thickness: 3 });
if (myShowLabels) {
	myHighPivots.slice(-30).forEach(_i => paint_label_at_line(myHighPainted, _i, String(high[_i]), { color: '#1E88FF' }));
	myLowPivots.slice(-30).forEach(_i => paint_label_at_line(myLowPainted, _i, String(low[_i]), { color: '#FF1744' }));
}
register_signal(myNewHigh, 'New Swing High');
register_signal(myNewLow, 'New Swing Low');
register_signal(myHighBroken, 'Swing High Broken');
register_signal(myLowBroken, 'Swing Low Broken');
