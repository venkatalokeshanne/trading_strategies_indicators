describe_indicator('Order Block Strategy', 'price');

// ─── INPUTS ───
const myLookback = input.number('Lookback Period', 10, { min: 1, max: 200 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMult = input.number('ATR Multiplier (SL)', 7.5, { min: 0.1, max: 50 });
const myRR = input.number('Risk:Reward Ratio', 1.5, { min: 0.1, max: 50 });
const mySlMode = input.select('Stop Loss Mode', 'ATR', ['ATR', 'Percentage']);
const mySlPercent = input.number('SL % (if Percentage mode)', 1.0, { min: 0.01, max: 100 });

// ─── ATR ───
const myAtr = atr(high, low, close, myAtrLen);

// ─── SWING HIGH / LOW (Pine ta.pivothigh/pivotlow with equal left/right) ───
const mySwingHigh = pivot_high(high, myLookback, myLookback);
const mySwingLow = pivot_low(low, myLookback, myLookback);

// high[lookback] / low[lookback] from Pine, equivalent to shifting forward by lookback
const myHighLB = shift(high, myLookback);
const myLowLB = shift(low, myLookback);

// ─── ORDER BLOCK STATE (reproduces Pine's "var float" persistence) ───
const myBullOBHigh = series_of(null);
const myBullOBLow = series_of(null);
const myBearOBHigh = series_of(null);
const myBearOBLow = series_of(null);

let myCurrBullHigh = null;
let myCurrBullLow = null;
let myCurrBearHigh = null;
let myCurrBearLow = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (mySwingLow[myIndex] !== null) {
		myCurrBullHigh = myHighLB[myIndex];
		myCurrBullLow = myLowLB[myIndex];
	}
	if (mySwingHigh[myIndex] !== null) {
		myCurrBearHigh = myHighLB[myIndex];
		myCurrBearLow = myLowLB[myIndex];
	}
	myBullOBHigh[myIndex] = myCurrBullHigh;
	myBullOBLow[myIndex] = myCurrBullLow;
	myBearOBHigh[myIndex] = myCurrBearHigh;
	myBearOBLow[myIndex] = myCurrBearLow;
}

// ─── ENTRY CONDITIONS ───
const myLongCondition = for_every(myBullOBHigh, myBullOBLow, close, open, (_bh, _bl, _c, _o) =>
	_bh !== null && _c <= _bh && _c >= _bl && _c > _o
);

const myShortCondition = for_every(myBearOBHigh, myBearOBLow, close, open, (_bh, _bl, _c, _o) =>
	_bh !== null && _c >= _bl && _c <= _bh && _c < _o
);

// ─── SL DISTANCE / SL / TP ───
const mySlDistance = for_every(close, myAtr, (_c, _a) =>
	mySlMode === 'Percentage' ? _c * (mySlPercent / 100) : _a * myAtrMult
);

const myLongSL = sub(close, mySlDistance);
const myLongTP = add(close, mult(mySlDistance, myRR));
const myShortSL = add(close, mySlDistance);
const myShortTP = sub(close, mult(mySlDistance, myRR));

// Only show SL/TP values on the bars where a signal actually fires
const myLongSLPlot = for_every(myLongCondition, myLongSL, (_cond, _v) => _cond ? _v : null);
const myLongTPPlot = for_every(myLongCondition, myLongTP, (_cond, _v) => _cond ? _v : null);
const myShortSLPlot = for_every(myShortCondition, myShortSL, (_cond, _v) => _cond ? _v : null);
const myShortTPPlot = for_every(myShortCondition, myShortTP, (_cond, _v) => _cond ? _v : null);

// ─── PAINT ORDER BLOCK ZONES ───
// Boxes are not supported by the Custom JS API, approximated as filled
// zones between the OB high/low lines instead.
fill(
	paint(myBullOBHigh, { name: 'Bull OB High', color: 'green', style: 'ladder', thickness: 1 }),
	paint(myBullOBLow, { name: 'Bull OB Low', color: 'green', style: 'ladder', thickness: 1 }),
	'green',
	0.1
);

fill(
	paint(myBearOBHigh, { name: 'Bear OB High', color: 'red', style: 'ladder', thickness: 1 }),
	paint(myBearOBLow, { name: 'Bear OB Low', color: 'red', style: 'ladder', thickness: 1 }),
	'red',
	0.1
);

// ─── PAINT SL / TP MARKERS ON SIGNAL BARS ───
paint(myLongSLPlot, { name: 'Long SL', color: 'maroon', style: 'labels_below' });
paint(myLongTPPlot, { name: 'Long TP', color: 'darkgreen', style: 'labels_above' });
paint(myShortSLPlot, { name: 'Short SL', color: 'maroon', style: 'labels_above' });
paint(myShortTPPlot, { name: 'Short TP', color: 'darkgreen', style: 'labels_below' });

// ─── SIGNALS (for scanner, alerts, strategy tester) ───
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');

// ─── INFO TABLE ───
const mySlValueText = mySlMode === 'Percentage'
	? `${mySlPercent}%`
	: `ATR x ${myAtrMult}`;

paint_overlay('OrderBlockInfoTable', { position: 'top_right' }, {
	rows: [{
		cells: [
			{ text: 'SL Mode', color: 'white', background_color: 'gray' },
			{ text: mySlMode, color: 'white', background_color: 'gray' }
		]
	}, {
		cells: [
			{ text: 'SL Value', color: 'white', background_color: 'gray' },
			{ text: mySlValueText, color: 'yellow', background_color: 'gray' }
		]
	}, {
		cells: [
			{ text: 'R:R Ratio', color: 'white', background_color: 'gray' },
			{ text: `${myRR}x`, color: 'yellow', background_color: 'gray' }
		]
	}]
});