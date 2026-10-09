describe_indicator('Empowerment Assets Core v1', 'price');

const myShowEMA = input.boolean('Show EMAs', true);
const myShowVWAP = input.boolean('Show VWAP', true);
const myShowLabels = input.boolean('Show EMA Labels', true);

const myEma5 = ema(close, 5);
const myEma10 = ema(close, 10);
const myEma20 = ema(close, 20);
const myEma50 = ema(close, 50);
const myEma90 = ema(close, 90);

// ta.vwap(close) in Pine resets at the start of every session (day).
// We replicate this by manually accumulating sum(close*volume) and
// sum(volume) and resetting them whenever a new trading session starts.
const mySessionAtIndex = time.map(_t => bar_at(_t).session);
const myVwapLine = series_of(null);
let myCumPV = 0;
let myCumV = 0;
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myNewSession = myIndex === 0 || mySessionAtIndex[myIndex] !== mySessionAtIndex[myIndex - 1];
	if (myNewSession) {
		myCumPV = 0;
		myCumV = 0;
	}
	myCumPV += close[myIndex] * volume[myIndex];
	myCumV += volume[myIndex];
	myVwapLine[myIndex] = myCumV !== 0 ? myCumPV / myCumV : null;
}

const myEma5Painted = paint(myShowEMA ? myEma5 : constants.empty_series, { name: 'EMA5', color: 'lime', thickness: 2 });
const myEma10Painted = paint(myShowEMA ? myEma10 : constants.empty_series, { name: 'EMA10', color: 'aqua', thickness: 2 });
const myEma20Painted = paint(myShowEMA ? myEma20 : constants.empty_series, { name: 'EMA20', color: 'yellow', thickness: 2 });
const myEma50Painted = paint(myShowEMA ? myEma50 : constants.empty_series, { name: 'EMA50', color: 'orange', thickness: 2 });
const myEma90Painted = paint(myShowEMA ? myEma90 : constants.empty_series, { name: 'EMA90', color: 'red', thickness: 2 });
const myVwapPainted = paint(myShowVWAP ? myVwapLine : constants.empty_series, { name: 'VWAP', color: 'fuchsia', thickness: 2 });

// Labels at the last candle, mimicking the Pine "barstate.islast" labels.
const myLastIndex = close.length - 1;

if (myShowLabels) {
	paint_label_at_line(myEma5Painted, myLastIndex, 'EMA 5', { background_color: 'lime', color: 'black' });
	paint_label_at_line(myEma10Painted, myLastIndex, 'EMA 10', { background_color: 'aqua', color: 'black' });
	paint_label_at_line(myEma20Painted, myLastIndex, 'EMA 20', { background_color: 'yellow', color: 'black' });
	paint_label_at_line(myEma50Painted, myLastIndex, 'EMA 50', { background_color: 'orange', color: 'black' });
	paint_label_at_line(myEma90Painted, myLastIndex, 'EMA 90', { background_color: 'red', color: 'white' });
	paint_label_at_line(myVwapPainted, myLastIndex, 'VWAP', { background_color: 'purple', color: 'white' });
}

// Trend logic, identical conditions as the Pine script.
const myBullTrend = for_every(close, myEma5, myEma10, myEma20, myEma50, myEma90, myVwapLine, (_c, _e5, _e10, _e20, _e50, _e90, _vwap) =>
	_c > _e5 && _e5 > _e10 && _e10 > _e20 && _e20 > _e50 && _e50 > _e90 && _c > _vwap
);

const myBearTrend = for_every(close, myEma5, myEma10, myEma20, myEma50, myEma90, myVwapLine, (_c, _e5, _e10, _e20, _e50, _e90, _vwap) =>
	_c < _e5 && _e5 < _e10 && _e10 < _e20 && _e20 < _e50 && _e50 < _e90 && _c < _vwap
);

// Pine's bgcolor() paints the whole chart background; Custom JS API has no
// background-paint primitive, so we approximate it by coloring the candles
// instead (green for bullish trend, red for bearish trend).
const myCandleColors = for_every(myBullTrend, myBearTrend, (_bull, _bear) => _bull ? 'rgba(0,128,0,0.3)' : (_bear ? 'rgba(255,0,0,0.3)' : null));
color_candles(myCandleColors);

register_signal(myBullTrend, 'Bull Trend');
register_signal(myBearTrend, 'Bear Trend');

// Dashboard overlay, equivalent of the Pine table.
const myTrendText = myBullTrend[myLastIndex] ? 'BULLISH' : (myBearTrend[myLastIndex] ? 'BEARISH' : 'NEUTRAL');
const myVwapRelation = close[myLastIndex] > myVwapLine[myLastIndex] ? 'ABOVE' : 'BELOW';

paint_overlay('EmpowermentAssetsDashboard', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'EMPOWERMENT' }, { text: 'ASSETS' }] },
		{ cells: [{ text: 'Trend' }, { text: myTrendText }] },
		{ cells: [{ text: 'Price' }, { text: String(close[myLastIndex]) }] },
		{ cells: [{ text: 'EMA 5' }, { text: String(myEma5[myLastIndex]) }] },
		{ cells: [{ text: 'EMA 10' }, { text: String(myEma10[myLastIndex]) }] },
		{ cells: [{ text: 'EMA 20' }, { text: String(myEma20[myLastIndex]) }] },
		{ cells: [{ text: 'VWAP' }, { text: myVwapRelation }] }
	]
});