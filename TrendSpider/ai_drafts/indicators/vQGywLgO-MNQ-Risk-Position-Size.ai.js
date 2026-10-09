describe_indicator('MNQ Risk Position Size', 'price');

// Risk amount in dollars, user adjustable
const myRiskDollars = input.number('Risk ($)', 1000, { min: 1 });

// MNQ point value, fixed per contract spec ($2 per point for Micro Nasdaq)
const myPointValue = 2.0;

const myBullish = for_every(close, open, (_c, _o) => _c > _o);
const myBearish = for_every(close, open, (_c, _o) => _c < _o);

// Bullish stop distance: close - low
const myBullStopDistance = sub(close, low);

// Bearish stop distance: high - close
const myBearStopDistance = sub(high, close);

// Micros for bullish signals: floor(risk / (stopDistance * pointValue)), null if stopDistance <= 0
const myBullMicros = for_every(myBullish, myBullStopDistance, (_bull, _dist) => {
	if (!_bull) return null;
	if (_dist <= 0) return null;
	const myRiskPerMicro = _dist * myPointValue;
	return Math.floor(myRiskDollars / myRiskPerMicro);
});

// Micros for bearish signals: floor(risk / (stopDistance * pointValue)), null if stopDistance <= 0
const myBearMicros = for_every(myBearish, myBearStopDistance, (_bear, _dist) => {
	if (!_bear) return null;
	if (_dist <= 0) return null;
	const myRiskPerMicro = _dist * myPointValue;
	return Math.floor(myRiskDollars / myRiskPerMicro);
});

// Series used to position the lines (at low for bulls, at high for bears)
// NOTE: paint_label_at_line() can't attach to labels_above/labels_below lines,
// so we paint these as regular (thin) lines instead, which do support labels.
const myBullLabelPos = for_every(myBullish, low, (_bull, _low) => _bull ? _low : null);
const myBearLabelPos = for_every(myBearish, high, (_bear, _high) => _bear ? _high : null);

const myBullLine = paint(myBullLabelPos, { name: 'BullishSignal', style: 'line', color: 'green', thickness: 1 });
const myBearLine = paint(myBearLabelPos, { name: 'BearishSignal', style: 'line', color: 'red', thickness: 1 });

// Paint label text (micros count) at each bullish/bearish candle
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myBullLabelPos[myIndex] !== null && myBullMicros[myIndex] !== null) {
		paint_label_at_line(myBullLine, myIndex, String(myBullMicros[myIndex]), {
			color: 'white',
			background_color: 'green',
			vertical_align: 'bottom'
		});
	}
	if (myBearLabelPos[myIndex] !== null && myBearMicros[myIndex] !== null) {
		paint_label_at_line(myBearLine, myIndex, String(myBearMicros[myIndex]), {
			color: 'white',
			background_color: 'red',
			vertical_align: 'top'
		});
	}
}

// Signals for scanner/alert/strategy usage
register_signal(myBullish, 'Bullish Candle');
register_signal(myBearish, 'Bearish Candle');
register_signal(for_every(myBullMicros, _m => _m !== null && _m > 0), 'Bullish Position Sizable');
register_signal(for_every(myBearMicros, _m => _m !== null && _m > 0), 'Bearish Position Sizable');