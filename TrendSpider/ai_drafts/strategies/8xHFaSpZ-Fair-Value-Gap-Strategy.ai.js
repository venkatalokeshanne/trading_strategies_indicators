describe_indicator('Fair Value Gap Strategy');

// Bullish FVG: High 2 bars ago is lower than current Low
// (gap between bar-2 high and current low never got filled)
const myBullishFVG = for_every(high, low, (_h, _l, _prev, _i) => {
	if (_i < 2) return false;
	return high[_i - 2] < low[_i];
});

// Bearish FVG: Low 2 bars ago is higher than current High
const myBearishFVG = for_every(low, high, (_l, _h, _prev, _i) => {
	if (_i < 2) return false;
	return low[_i - 2] > high[_i];
});

// Labels marking FVG bars, placed below/above the bar like plotshape did
const myBullishLabels = for_every(myBullishFVG, low, (_b, _l) => _b ? _l : null);
const myBearishLabels = for_every(myBearishFVG, high, (_b, _h) => _b ? _h : null);

paint(myBullishLabels, { name: 'BullishFVG', style: 'labels_below', color: 'green' });
paint(myBearishLabels, { name: 'BearishFVG', style: 'labels_above', color: 'red' });

// Gap zone top/bottom lines (visual equivalent of the Pine box).
// Top of bullish zone = current low, bottom = high 2 bars back.
const myBullishZoneTop = for_every(myBullishFVG, low, (_b, _l) => _b ? _l : null);
const myBullishZoneBottom = series_of(null);
const myBearishZoneTop = series_of(null);
const myBearishZoneBottom = for_every(myBearishFVG, high, (_b, _h) => _b ? _h : null);

for (let myIndex = 2; myIndex < close.length; myIndex += 1) {
	if (myBullishFVG[myIndex]) {
		myBullishZoneBottom[myIndex] = high[myIndex - 2];
	}
	if (myBearishFVG[myIndex]) {
		myBearishZoneTop[myIndex] = low[myIndex - 2];
	}
}

fill(
	paint(myBullishZoneTop, { name: 'BullishZoneTop', color: 'green', style: 'dotted' }),
	paint(myBullishZoneBottom, { name: 'BullishZoneBottom', color: 'green', style: 'dotted' }),
	'green',
	0.15
);

fill(
	paint(myBearishZoneTop, { name: 'BearishZoneTop', color: 'red', style: 'dotted' }),
	paint(myBearishZoneBottom, { name: 'BearishZoneBottom', color: 'red', style: 'dotted' }),
	'red',
	0.15
);

// Signals for use in Scanners, Alerts and Strategy Tester
register_signal(myBullishFVG, 'Bullish FVG Long Entry');
register_signal(myBearishFVG, 'Bearish FVG Short Entry');