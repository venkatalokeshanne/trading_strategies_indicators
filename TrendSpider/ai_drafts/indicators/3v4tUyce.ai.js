describe_indicator('XauLabs Swing Points', 'price');

// ============================================================
// INPUTS
// ============================================================
const majorTab = input.tab('Major Structure');
const myMajorLength = majorTab.number('Major Sensitivity (bars)', 7, { min: 5, max: 21 });
const myShowLabels = majorTab.boolean('Show HH / HL / LH / LL labels', true);
const myShowZigzag = majorTab.boolean('Connect major pivots (zigzag)', true);

const minorTab = input.tab('Minor Structure');
const myShowMinor = minorTab.boolean('Show minor pivots', false);
const myMinorLength = minorTab.number('Minor Sensitivity (bars)', 3, { min: 2, max: 9 });

// Palette (approximation of the original XauLabs color scheme)
const myColorUp = '#4E9B6E';
const myColorDown = '#B0413E';
const myColorNeutral = '#8A8494';
const myColorLine = '#D9A441';
const myColorMinor = '#8A8494';

// ============================================================
// MAJOR STRUCTURE — confirmed pivots (non-repainting)
// ============================================================
const myHighPivots = pivot_high(high, myMajorLength, myMajorLength);
const myLowPivots = pivot_low(low, myMajorLength, myMajorLength);

const myCandleCount = close.length;

// state kept across the whole series (sequential, like Pine's "var" variables)
let myLastHigh = null;
let myLastLow = null;

// output series for signals (true/false per candle)
const myFlagHH = series_of(false);
const myFlagLH = series_of(false);
const myFlagHL = series_of(false);
const myFlagLL = series_of(false);

// chain of all confirmed major pivots, in chronological order, used for the
// zigzag line and for the text labels
const myChainPoints = [];

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myHighPivots[myIndex] !== null) {
		const myIsHH = myLastHigh === null ? false : myHighPivots[myIndex] > myLastHigh;
		const myText = myLastHigh === null ? 'H' : (myIsHH ? 'HH' : 'LH');
		myChainPoints.push({ index: myIndex, value: myHighPivots[myIndex], text: myText });

		if (myLastHigh !== null) {
			if (myIsHH) { myFlagHH[myIndex] = true; }
			else { myFlagLH[myIndex] = true; }
		}
		myLastHigh = myHighPivots[myIndex];
	}

	if (myLowPivots[myIndex] !== null) {
		const myIsHL = myLastLow === null ? false : myLowPivots[myIndex] > myLastLow;
		const myText = myLastLow === null ? 'L' : (myIsHL ? 'HL' : 'LL');
		myChainPoints.push({ index: myIndex, value: myLowPivots[myIndex], text: myText });

		if (myLastLow !== null) {
			if (myIsHL) { myFlagHL[myIndex] = true; }
			else { myFlagLL[myIndex] = true; }
		}
		myLastLow = myLowPivots[myIndex];
	}
}

// sparse series connecting every confirmed major pivot, used both as an
// (hidden) anchor for the labels and as the source for the visible zigzag
const myChainSparse = series_of(null);
myChainPoints.forEach(myPoint => { myChainSparse[myPoint.index] = myPoint.value; });

// hidden anchor line, always painted so labels have a stable target
const myAnchorLine = paint(myChainSparse, { name: 'PivotAnchor', hidden: true, style: 'line' });

// visible zigzag line (constant interpolation keeps this backtestable/non-repainting)
const myZigzagLine = paint(
	myShowZigzag ? interpolate_sparse_series(myChainSparse, 'constant') : constants.empty_series,
	{ name: 'Zigzag', color: myColorLine, thickness: 1, style: 'line' }
);

// text labels on every confirmed major pivot
if (myShowLabels) {
	myChainPoints.forEach(myPoint => {
		const myLabelColor = myPoint.text === 'HH' || myPoint.text === 'HL' ? myColorUp
			: myPoint.text === 'LH' || myPoint.text === 'LL' ? myColorDown
			: myColorNeutral;

		paint_label_at_line(myAnchorLine, myPoint.index, myPoint.text, {
			color: myLabelColor,
			background_color: '#17141A',
			vertical_align: myPoint.value === myHighPivots[myPoint.index] ? 'top' : 'bottom'
		});
	});
}

// ============================================================
// MINOR STRUCTURE — internal waves (optional)
// ============================================================
const myMinorHighPivots = pivot_high(high, myMinorLength, myMinorLength);
const myMinorLowPivots = pivot_low(low, myMinorLength, myMinorLength);

paint(
	myShowMinor ? for_every(myMinorHighPivots, _h => _h !== null ? constants.icons.circle : null) : constants.empty_series,
	{ name: 'MinorHigh', style: 'labels_above', color: myColorMinor }
);

paint(
	myShowMinor ? for_every(myMinorLowPivots, _l => _l !== null ? constants.icons.circle : null) : constants.empty_series,
	{ name: 'MinorLow', style: 'labels_below', color: myColorMinor }
);

// ============================================================
// SIGNALS (for Scanner / Alerts / Strategy Tester)
// ============================================================
register_signal(for_every(myHighPivots, _h => _h !== null), 'Major High Confirmed');
register_signal(for_every(myLowPivots, _l => _l !== null), 'Major Low Confirmed');
register_signal(myFlagHH, 'Higher High (HH)');
register_signal(myFlagLH, 'Lower High (LH)');
register_signal(myFlagHL, 'Higher Low (HL)');
register_signal(myFlagLL, 'Lower Low (LL)');
register_signal(for_every(myMinorHighPivots, _h => _h !== null), 'Minor High Pivot');
register_signal(for_every(myMinorLowPivots, _l => _l !== null), 'Minor Low Pivot');