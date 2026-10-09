describe_indicator('Cambist Swing High Low', 'price');
// NOTE: TradingView draws individual ray objects (line.new) that get
// frozen when broken. The Custom JS API has no equivalent of dynamically
// created line objects, so this is approximated with two step-series
// (one for the active swing high level, one for the active swing low
// level) which hold their value until a new pivot replaces them or
// price closes through them (mirroring the Pine "freeze" logic). This
// reproduces the same values and the same bars where things happen,
// but visually it is a continuous line per swing instead of separate
// segments.
const myPivotLen = input.number('Swing Lookback', 5, { min: 1, max: 200 });
const myShowLabels = input.boolean('Show Swing Labels', true);
const myHighColor = '#1E88FF';
const myLowColor = '#FF1744';

// pivot_high/pivot_low with equal left/right length reproduce
// ta.pivothigh(high, pivotLen, pivotLen) / ta.pivotlow(low, pivotLen, pivotLen)
const myPivotHigh = pivot_high(high, myPivotLen, myPivotLen);
const myPivotLow = pivot_low(low, myPivotLen, myPivotLen);

const myActiveHigh = series_of(null);
const myActiveLow = series_of(null);
const myNewSwingHighSignal = series_of(false);
const myNewSwingLowSignal = series_of(false);
const myHighBrokenSignal = series_of(false);
const myLowBrokenSignal = series_of(false);

let myActiveHighPrice = null;
let myActiveLowPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	// a pivot point detected "now" actually belongs to the candle
	// pivotLen bars back (same as pivotBar = bar_index - pivotLen)
	if (myPivotHigh[myIndex] !== null && myPivotHigh[myIndex] !== undefined) {
		myActiveHighPrice = myPivotHigh[myIndex];
		myNewSwingHighSignal[myIndex] = true;
	}
	if (myPivotLow[myIndex] !== null && myPivotLow[myIndex] !== undefined) {
		myActiveLowPrice = myPivotLow[myIndex];
		myNewSwingLowSignal[myIndex] = true;
	}
	if (myActiveHighPrice !== null && close[myIndex] > myActiveHighPrice) {
		myHighBrokenSignal[myIndex] = true;
		myActiveHighPrice = null;
	}
	if (myActiveLowPrice !== null && close[myIndex] < myActiveLowPrice) {
		myLowBrokenSignal[myIndex] = true;
		myActiveLowPrice = null;
	}
	myActiveHigh[myIndex] = myActiveHighPrice;
	myActiveLow[myIndex] = myActiveLowPrice;
}

const myHighLinePainted = paint(myActiveHigh, { name: 'SwingHigh', color: myHighColor, style: 'dotted', thickness: 3 });
const myLowLinePainted = paint(myActiveLow, { name: 'SwingLow', color: myLowColor, style: 'dotted', thickness: 3 });

// labels are placed at the pivot points themselves (sparse points of the
// original pivot series), showing the swing price, mirroring the Pine labels
const myHighPivotPoints = indexed_points_of(myPivotHigh);
const myLowPivotPoints = indexed_points_of(myPivotLow);
const myMaxLabels = 500;

if (myShowLabels) {
	myHighPivotPoints.slice(-myMaxLabels).forEach(_point => {
		paint_label_at_line(myHighLinePainted, _point.candleIndex, String(_point.value), {
			color: myHighColor,
			vertical_align: 'top'
		});
	});
	myLowPivotPoints.slice(-myMaxLabels).forEach(_point => {
		paint_label_at_line(myLowLinePainted, _point.candleIndex, String(_point.value), {
			color: myLowColor,
			vertical_align: 'bottom'
		});
	});
}

// signals for scanners, alerts, strategy tester
register_signal(myNewSwingHighSignal, 'New Swing High');
register_signal(myNewSwingLowSignal, 'New Swing Low');
register_signal(myHighBrokenSignal, 'Swing High Broken');
register_signal(myLowBrokenSignal, 'Swing Low Broken');