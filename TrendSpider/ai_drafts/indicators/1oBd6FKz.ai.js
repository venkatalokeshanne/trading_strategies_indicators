describe_indicator('Kyokutan Ashi', 'price');

// NOTE: TrendSpider has no native plotcandle() equivalent for custom
// synthetic OHLC candles. We approximate the Pine "plotcandle" by
// painting the four synthetic O/H/L/C lines, and we also tint the
// real chart candles (color_candles) using the synthetic direction
// (anti-close >= anti-open => green, else red).

const anchorTab = input.tab('Anchor and Base Settings');
const myAnchorType = anchorTab.select('Anchor Point', 'Open', ['Open', 'Close', 'HL2']);
const myHaMode = anchorTab.select('Heikin Ashi Open Calc', 'Traditional', ['Traditional', 'Simplified']);

const scaleTab = input.tab('Construction and Scale');
const myCalcMode = scaleTab.select('Wick Calculation', 'MaxMin', ['MaxMin', 'Strict']);
const myMultiplier = scaleTab.number('Deviation Multiplier', 1.0, { min: 0.1, max: 50, step: 0.1 });

// Base data is the current chart's own O/H/L/C (equivalent of Pine's
// request.security(stdTicker, timeframe.period, ...) which, since it
// requests the *current* timeframe, simply returns the current chart data).
const myStdOpen = open;
const myStdHigh = high;
const myStdLow = low;
const myStdClose = close;

// Heikin-Ashi close is just ohlc4
const myHaClose = ohlc4;

// Heikin-Ashi open:
//  Traditional: recursive, seeded with (O+C)/2 on bar 0
//  Simplified: (stdO[1] + stdC[1]) / 2, i.e. shifted (O+C)/2
// NOTE: on the very first bar, Pine's "Simplified" haOpen would be `na`
// (there is no bar -1). We approximate bar 0 using the same-bar (O+C)/2
// instead of leaving it null, to keep the series usable from bar 0.
const myHaOpenTraditional = for_every(myHaClose, (_hc, _prevHaOpen, _idx) => {
	if (_idx === 0) {
		return (myStdOpen[0] + myStdClose[0]) / 2.0;
	}
	return (_prevHaOpen + myHaClose[_idx - 1]) / 2.0;
});

const myOc2Shifted = shift(oc2, 1);
const myHaOpenSimplified = for_every(myOc2Shifted, oc2, (_shifted, _oc2cur, _p, _idx) => {
	return _idx === 0 ? _oc2cur : _shifted;
});

const myHaOpen = myHaMode === 'Traditional' ? myHaOpenTraditional : myHaOpenSimplified;

const myHaHigh = max_of(myStdHigh, max_of(myHaOpen, myHaClose));
const myHaLow = min_of(myStdLow, min_of(myHaOpen, myHaClose));

// Raw deviation (noise), scaled by the multiplier
const myRawOpen = mult(sub(myStdOpen, myHaOpen), myMultiplier);
const myRawClose = mult(sub(myStdClose, myHaClose), myMultiplier);
const myRawHigh = mult(sub(myStdHigh, myHaHigh), myMultiplier);
const myRawLow = mult(sub(myStdLow, myHaLow), myMultiplier);

// Candle reconstruction
const myStdHl2 = hl2;
const myAnchor = myAnchorType === 'Open' ? myStdOpen : (myAnchorType === 'Close' ? myStdClose : myStdHl2);

const myAntiOpen = add(myAnchor, myRawOpen);
const myAntiClose = add(myAnchor, myRawClose);

let myAntiHigh;
let myAntiLow;

if (myCalcMode === 'MaxMin') {
	myAntiHigh = add(myAnchor, max_of(myRawOpen, max_of(myRawClose, max_of(myRawHigh, myRawLow))));
	myAntiLow = add(myAnchor, min_of(myRawOpen, min_of(myRawClose, min_of(myRawHigh, myRawLow))));
}
else {
	const myAntiHighRaw = add(myAnchor, myRawHigh);
	const myAntiLowRaw = add(myAnchor, myRawLow);
	myAntiHigh = max_of(myAntiOpen, max_of(myAntiClose, max_of(myAntiHighRaw, myAntiLowRaw)));
	myAntiLow = min_of(myAntiOpen, min_of(myAntiClose, min_of(myAntiHighRaw, myAntiLowRaw)));
}

// Candle direction, used for coloring
const myIsBullish = for_every(myAntiClose, myAntiOpen, (_c, _o) => _c >= _o);
const myCandleColors = for_every(myIsBullish, _b => _b ? 'green' : 'red');

color_candles(myCandleColors);

paint(myAntiOpen, { name: 'KA Open', color: 'gray', thickness: 1, style: 'line' });
paint(myAntiHigh, { name: 'KA High', color: '#26A69A', thickness: 1, style: 'line' });
paint(myAntiLow, { name: 'KA Low', color: '#EF5350', thickness: 1, style: 'line' });
paint(myAntiClose, { name: 'KA Close', color: 'black', thickness: 2, style: 'line' });

// Scanning / strategy signals
register_signal(myIsBullish, 'Kyokutan Ashi Bullish Candle');
register_signal(for_every(myIsBullish, _b => !_b), 'Kyokutan Ashi Bearish Candle');