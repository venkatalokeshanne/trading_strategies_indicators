describe_indicator('Combined Ichimoku and Donchian', 'price');

// ==========================================
// INPUTS
// ==========================================
const ichimokuTab = input.tab('Ichimoku Settings');
const tenkanLen = ichimokuTab.number('Tenkan sen Period', 9, { min: 1 });
const kijunLen = ichimokuTab.number('Kijun sen Period', 26, { min: 1 });
const senkouB = ichimokuTab.number('Senkou Span B Period', 52, { min: 1 });
const disp = ichimokuTab.number('Displacement', 26, { min: 1 });
const showTenkan = ichimokuTab.boolean('Show Tenkan', true);
const showKijun = ichimokuTab.boolean('Show Kijun', true);
const showCloud = ichimokuTab.boolean('Show Cloud', true);
const showChikou = ichimokuTab.boolean('Show Chikou Span', true);

const donchianTab = input.tab('Donchian Settings');
const dcLenFast = donchianTab.number('Fast Band Period', 20, { min: 1 });
const dcLenSlow = donchianTab.number('Slow Band Period', 50, { min: 1 });
const dcBreakLen = donchianTab.number('Breakout Channel Period', 20, { min: 1 });
const showDC = donchianTab.boolean('Show Donchian Ribbon', true);

// ==========================================
// CALCULATIONS
// ==========================================
// get_donchian(len) => avg(highest(high, len), lowest(low, len))
function myGetDonchian(_len) {
	return div(add(highest(high, _len), lowest(low, _len)), 2);
}

const myTenkan = myGetDonchian(tenkanLen);
const myKijun = myGetDonchian(kijunLen);
const mySpanA = div(add(myTenkan, myKijun), 2);
const mySpanB = myGetDonchian(senkouB);

// Donchian Ribbon
const myDcUpperFast = highest(high, dcLenFast);
const myDcLowerFast = lowest(low, dcLenFast);
const myDcUpperSlow = highest(high, dcLenSlow);
const myDcLowerSlow = lowest(low, dcLenSlow);

// Donchian Breakout Logic. Pine's `[1]` means "value from previous candle",
// which is equivalent to shifting the series to the right by 1.
const myDcBreakUpper = shift(highest(high, dcBreakLen), 1);
const myDcBreakLower = shift(lowest(low, dcBreakLen), 1);

// ==========================================
// PLOTTING
// ==========================================
// Ichimoku lines. Cloud lines (Span A/B) are offset forward by (disp - 1)
// candles, exactly matching Pine's `offset=disp-1` behavior.
const myTenkanToPaint = showTenkan ? myTenkan : constants.empty_series;
const myKijunToPaint = showKijun ? myKijun : constants.empty_series;
const mySpanAShifted = shift(showCloud ? mySpanA : constants.empty_series, disp - 1);
const mySpanBShifted = shift(showCloud ? mySpanB : constants.empty_series, disp - 1);

// Chikou Span is offset backward (into the past) by (disp - 1) candles,
// matching Pine's `offset=-disp+1`.
const myChikouShifted = shift(showChikou ? close : constants.empty_series, -(disp - 1));

paint(myTenkanToPaint, { name: 'Tenkan sen', color: '#2962ff', thickness: 1 });
paint(myKijunToPaint, { name: 'Kijun sen', color: '#ef5350', thickness: 1 });
paint(mySpanAShifted, { name: 'Span A', color: '#26a69a', thickness: 1 });
paint(mySpanBShifted, { name: 'Span B', color: '#ef5350', thickness: 1 });

// Dynamic cloud coloring between Span A and Span B. fill() only accepts
// a single static color string, so color_cloud() is used instead since it
// natively supports two colors depending on which line is on top.
color_cloud(
	mySpanAShifted,
	mySpanBShifted,
	'#26a69a',
	'#ef5350',
	'Bullish Cloud',
	'Bearish Cloud',
	0.1
);

paint(myChikouShifted, { name: 'Chikou Span', color: '#9c27b0', thickness: 1 });

// Donchian Ribbon
const myDcUpperFastToPaint = showDC ? myDcUpperFast : constants.empty_series;
const myDcLowerFastToPaint = showDC ? myDcLowerFast : constants.empty_series;
const myDcUpperSlowToPaint = showDC ? myDcUpperSlow : constants.empty_series;
const myDcLowerSlowToPaint = showDC ? myDcLowerSlow : constants.empty_series;

const myDcUpperFastPainted = paint(myDcUpperFastToPaint, { name: 'Fast Upper', color: 'gray', thickness: 1 });
const myDcLowerFastPainted = paint(myDcLowerFastToPaint, { name: 'Fast Lower', color: 'gray', thickness: 1 });
const myDcUpperSlowPainted = paint(myDcUpperSlowToPaint, { name: 'Slow Upper', color: 'silver', thickness: 1 });
const myDcLowerSlowPainted = paint(myDcLowerSlowToPaint, { name: 'Slow Lower', color: 'silver', thickness: 1 });

// Ribbon shading between fast and slow bands
fill(myDcUpperFastPainted, myDcUpperSlowPainted, 'gray', 0.08, 'Upper Ribbon Shading');
fill(myDcLowerFastPainted, myDcLowerSlowPainted, 'gray', 0.08, 'Lower Ribbon Shading');

// ==========================================
// SIGNAL STATE MACHINE
// ==========================================
// Reproduces Pine's `var int lastSignal` state machine: a breakout only
// triggers if it is a change of state from the last recorded signal.
const myLongBreakout = for_every(close, myDcBreakUpper, (_c, _u) => _c > _u);
const myShortBreakout = for_every(close, myDcBreakLower, (_c, _l) => _c < _l);

// lastSignal state series: 0 = none, 1 = long, -1 = short
const myLastSignal = for_every(myLongBreakout, myShortBreakout, (_longBrk, _shortBrk, _prev, _idx) => {
	const myPrevState = _idx === 0 || _prev === undefined || _prev === null ? 0 : _prev;
	const myTriggerLong = _longBrk && myPrevState !== 1;
	const myTriggerShort = _shortBrk && myPrevState !== -1;

	if (myTriggerLong) {
		return 1;
	}
	if (myTriggerShort) {
		return -1;
	}
	return myPrevState;
});

// Recompute trigger flags against the state series produced above,
// matching Pine's triggerLong / triggerShort exactly.
const myTriggerLong = for_every(myLongBreakout, myLastSignal, close.map((_v, _i) => _i), (_longBrk, _state, _idx) => {
	const myPrevState = _idx === 0 ? 0 : myLastSignal[_idx - 1];
	return _longBrk && myPrevState !== 1;
});
const myTriggerShort = for_every(myShortBreakout, myLastSignal, close.map((_v, _i) => _i), (_shortBrk, _state, _idx) => {
	const myPrevState = _idx === 0 ? 0 : myLastSignal[_idx - 1];
	return _shortBrk && myPrevState !== -1;
});

// Visual markers for breakout triggers
const myLongMarks = for_every(myTriggerLong, low, (_trig, _low) => _trig ? constants.icons.triangle_up : null);
const myShortMarks = for_every(myTriggerShort, high, (_trig, _high) => _trig ? constants.icons.triangle_down : null);

paint(myLongMarks, { name: 'Long Breakout', style: 'labels_below', color: 'green' });
paint(myShortMarks, { name: 'Short Breakout', style: 'labels_above', color: 'red' });

// Signals for scanners, alerts and strategies
register_signal(myTriggerLong, 'Donchian Long Entry');
register_signal(myTriggerShort, 'Donchian Short Entry');