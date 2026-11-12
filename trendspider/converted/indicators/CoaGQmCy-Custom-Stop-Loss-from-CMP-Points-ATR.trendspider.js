/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Stop Loss from CMP
 * Author       : avdhesh_alstom
 * Source URL   : https://www.tradingview.com/script/CoaGQmCy-Custom-Stop-Loss-from-CMP-Points-ATR
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Stop Loss from CMP_TV
 *
 * The Pine original, in words: a dashed stop-loss line over the last 22 bars at close -/+ (percent, points or ATR x
 *   multiplier), with a label.
 *
 * Deviations from the original: dotted line; label without a filled background.
 * Not carried over: alertconditions — use the SL Hit signals.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Stop Loss from CMP_TV', 'price');
const myTab = input.tab('Stop Loss Settings');
const mySlType = myTab.select('Stop Loss Type', 'Percentage', ['Percentage', 'Points', 'ATR']);
const mySlPctGroup = myTab.row();
const mySlPct = mySlPctGroup.number('Stop Loss Percent', 5.0, { min: 0.01, max: 100, step: 0.1 });
const mySlPoints = mySlPctGroup.number('Stop Loss Points', 10.0, { min: 0.01, max: 100000, step: 0.1 });
const myAtrGroup = myTab.row();
const myAtrLen = myAtrGroup.number('ATR Length', 14, { min: 1, max: 500 });
const myAtrMult = myAtrGroup.number('ATR Multiplier', 2.0, { min: 0.01, max: 100, step: 0.1 });
const myDirection = myTab.select('Direction', 'Long', ['Long', 'Short']);
// shortened input title (was "Line Length (trading days back)") to
// satisfy the platform's max input name length limit
const myLookbackDays = myTab.number('Line Length (Days)', 22, { min: 1, max: 5000 });

// Compute ATR using built-in function
const myAtrValue = atr(high, low, close, myAtrLen);

// Compute SL distance per the selected type
const mySlDistance = mySlType === 'Percentage'
	? div(mult(close, mySlPct), 100)
	: mySlType === 'Points'
		? series_of(mySlPoints)
		: mult(myAtrValue, myAtrMult);

// Compute SL level based on direction
const mySlLevel = myDirection === 'Long'
	? sub(close, mySlDistance)
	: add(close, mySlDistance);

// Build a line spanning the last "lookbackDays" candles, matching Pine's
// line.new(x1=bar_index-lookbackDays, x2=bar_index) drawn on barstate.islast
const myLastIndex = close.length - 1;
const myStartIndex = Math.max(0, myLastIndex - myLookbackDays);
const myCurrentSlLevel = mySlLevel[myLastIndex];
const myCurrentSlDistance = mySlDistance[myLastIndex];
const mySlLineSeries = series_of(null);

for (let myIndex = myStartIndex; myIndex <= myLastIndex; myIndex += 1) {
	mySlLineSeries[myIndex] = myCurrentSlLevel;
}

const mySlLinePainted = paint(mySlLineSeries, { name: 'Stop Loss Line', color: 'red', style: 'dotted', thickness: 1 });

// Label text mirrors Pine's "SL: value (distance)" format, rounded to 2 decimals
const myLabelText = 'SL ' + myCurrentSlLevel.toFixed(2) + ' Dist ' + myCurrentSlDistance.toFixed(2);
paint_label_at_line(mySlLinePainted, myLastIndex, myLabelText, { color: 'red' });

// Alerts / scanner signals, replicating Pine's alertcondition() logic
const mySlHitLongSignal = for_every(low, mySlLevel, (_low, _slLevel) => myDirection === 'Long' && _low <= _slLevel);
const mySlHitShortSignal = for_every(high, mySlLevel, (_high, _slLevel) => myDirection === 'Short' && _high >= _slLevel);
register_signal(mySlHitLongSignal, 'SL Hit Long');
register_signal(mySlHitShortSignal, 'SL Hit Short');
