describe_indicator('Kalman Trend Filter', 'price');

// ВХОДНЫЕ ПАРАМЕТРЫ
const myShortLen = input.number('Short Period', 50, { min: 1, max: 1000 });
const myLongLen = input.number('Long Period', 150, { min: 1, max: 1000 });
const myProcessNoise = input.number('Process Noise (Q)', 0.01, { min: 0.0001, max: 10, step: 0.001 });

// Kalman filter is a recursive (stateful) calculation, just like Pine's
// `var float` + `:=` persistent variables. We reproduce that recursion using
// a closure variable for the covariance (p) state, updated once per candle,
// sequentially, inside a for_every() callback. for_every() guarantees the
// callback is invoked once per candle in order, so this mirrors Pine exactly.
let myShortP = 1.0;
const myShortR = myShortLen * 0.1;

const myShortX = for_every(close, (_close, _prevX, _index) => {
	const myPrevX = _index === 0 || _prevX === null ? _close : _prevX;
	const myPPred = myShortP + myProcessNoise;
	const myK = myPPred / (myPPred + myShortR);
	const myNewX = myPrevX + myK * (_close - myPrevX);
	myShortP = (1.0 - myK) * myPPred;
	return myNewX;
});

let myLongP = 1.0;
const myLongR = myLongLen * 0.1;

const myLongX = for_every(close, (_close, _prevX, _index) => {
	const myPrevX = _index === 0 || _prevX === null ? _close : _prevX;
	const myPPred = myLongP + myProcessNoise;
	const myK = myPPred / (myPPred + myLongR);
	const myNewX = myPrevX + myK * (_close - myPrevX);
	myLongP = (1.0 - myK) * myPPred;
	return myNewX;
});

// trend_up = short_x > long_x
const myTrendUp = for_every(myShortX, myLongX, (_s, _l) => _s > _l);

// trend_col1 = short_x > short_x[2] ? up : down
const myShortXShift2 = shift(myShortX, 2);
const myShortRising = for_every(myShortX, myShortXShift2, (_s, _s2) => _s > _s2);

const myUpperColor = '#13bd6e';
const myLowerColor = '#af0d4b';

const myShortLineColor = for_every(myShortRising, _rising => _rising ? myUpperColor : myLowerColor);
const myLongLineColor = for_every(myTrendUp, _up => _up ? myUpperColor : myLowerColor);

const myShortLinePainted = paint(myShortX, { name: 'ShortKalman', color: myShortLineColor, thickness: 1 });
const myLongLinePainted = paint(myLongX, { name: 'LongKalman', color: myLongLineColor, thickness: 2 });

// Fill between the two lines, colored by trend direction (approximating
// Pine's per-bar fill color using the overall trend color at each bar;
// TrendSpider's fill() only supports a single static color per call, so we
// use color_cloud() instead, which supports two colors based on which line
// is above the other - this is the closest built-in equivalent).
color_cloud(myShortX, myLongX, myUpperColor, myLowerColor, 'BullFill', 'BearFill', 0.15);

// Scanner / Alert / Strategy signals
register_signal(myTrendUp, 'Trend Up (Short above Long)');
register_signal(for_every(myTrendUp, _up => !_up), 'Trend Down (Short below Long)');

const myTrendUpShift1 = shift(myTrendUp, 1);
const myBullCross = for_every(myTrendUp, myTrendUpShift1, (_now, _prev) => _now === true && _prev === false);
const myBearCross = for_every(myTrendUp, myTrendUpShift1, (_now, _prev) => _now === false && _prev === true);

register_signal(myBullCross, 'Bullish Cross (Short crosses above Long)');
register_signal(myBearCross, 'Bearish Cross (Short crosses below Long)');
register_signal(myShortRising, 'Short Kalman Rising');