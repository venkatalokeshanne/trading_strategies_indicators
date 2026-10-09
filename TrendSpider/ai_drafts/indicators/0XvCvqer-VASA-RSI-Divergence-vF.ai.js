describe_indicator('VASA RSI Plus Divergence', 'lower');

// ---------- Inputs ----------
const rsiTab = input.tab('RSI');
const mySource = rsiTab.select('Source', 'close', constants.price_source_options);
const myLenR = rsiTab.number('RSI Length', 14, { min: 2 });
const myObLevel = rsiTab.number('Overbought', 70, { min: 50, max: 100 });
const myOsLevel = rsiTab.number('Oversold', 30, { min: 0, max: 50 });

const divTab = input.tab('Divergence (regular)');
const myLb = divTab.number('Pivot left bars', 5, { min: 1 });
const myRb = divTab.number('Pivot right bars', 5, { min: 1 });
const myRngMax = divTab.number('Max bars between pivots', 60, { min: 5 });
const myDrawLn = divTab.boolean('Draw divergence line', true);

const styleTab = input.tab('Style');
const myColUp = styleTab.color('Bullish', '#15803d');
const myColDn = styleTab.color('Bearish', '#b91c1c');

const myPrice = market[mySource];
const myRsi = rsi(myPrice, myLenR);

// ---------- Confirmed pivots on RSI (non-repainting) ----------
// pivot_low/pivot_high mark a value at the PEAK candle index once it is
// confirmed by `myRb` closed candles to its right, mirroring Pine's
// ta.pivotlow/ta.pivothigh behavior (which reports on the confirmation bar
// but references the data of the peak bar via `low[rb]`/`high[rb]`).
const myPl = pivot_low(myRsi, myLb, myRb);
const myPh = pivot_high(myRsi, myLb, myRb);

const myPlPoints = indexed_points_of(myPl);
const myPhPoints = indexed_points_of(myPh);

const myBullDiv = series_of(false);
const myBearDiv = series_of(false);

let myLastBullLine = null;
for (let myI = 1; myI < myPlPoints.length; myI += 1) {
	const myPrev = myPlPoints[myI - 1];
	const myCur = myPlPoints[myI];

	if ((myCur.candleIndex - myPrev.candleIndex) <= myRngMax) {
		// regular bullish: price lower low, RSI higher low
		if (low[myCur.candleIndex] < low[myPrev.candleIndex] && myCur.value > myPrev.value) {
			myBullDiv[myCur.candleIndex] = true;
			myLastBullLine = { fromIndex: myPrev.candleIndex, fromValue: myPrev.value, toIndex: myCur.candleIndex, toValue: myCur.value };
		}
	}
}

let myLastBearLine = null;
for (let myI = 1; myI < myPhPoints.length; myI += 1) {
	const myPrev = myPhPoints[myI - 1];
	const myCur = myPhPoints[myI];

	if ((myCur.candleIndex - myPrev.candleIndex) <= myRngMax) {
		// regular bearish: price higher high, RSI lower high
		if (high[myCur.candleIndex] > high[myPrev.candleIndex] && myCur.value < myPrev.value) {
			myBearDiv[myCur.candleIndex] = true;
			myLastBearLine = { fromIndex: myPrev.candleIndex, fromValue: myPrev.value, toIndex: myCur.candleIndex, toValue: myCur.value };
		}
	}
}

// ---------- Marks for signals ----------
const myBullMarks = for_every(myBullDiv, myRsi, (_myBull, _myR) => _myBull ? _myR : null);
const myBearMarks = for_every(myBearDiv, myRsi, (_myBear, _myR) => _myBear ? _myR : null);

// ---------- Painting ----------
paint(horizontal_line(myObLevel), { name: 'Overbought', color: '#b91c1c', style: 'dotted' });
paint(horizontal_line(myOsLevel), { name: 'Oversold', color: '#15803d', style: 'dotted' });
paint(horizontal_line(50), { name: 'Midline', color: 'gray', style: 'dotted' });

paint(myRsi, { name: 'RSI', color: '#2563eb', thickness: 2 });

paint(myBullMarks, { name: 'Bull', style: 'labels_below', color: myColUp });
paint(myBearMarks, { name: 'Bear', style: 'labels_above', color: myColDn });

// Only the most recent confirmed bullish/bearish divergence line is drawn,
// since the number of paint() calls must stay constant across all runs.
const myBullLineSeries = (myDrawLn && myLastBullLine)
	? line(myLastBullLine.fromIndex, myLastBullLine.fromValue, myLastBullLine.toIndex, myLastBullLine.toValue, false)
	: series_of(null);
const myBearLineSeries = (myDrawLn && myLastBearLine)
	? line(myLastBearLine.fromIndex, myLastBearLine.fromValue, myLastBearLine.toIndex, myLastBearLine.toValue, false)
	: series_of(null);

paint(myBullLineSeries, { name: 'Bullish Divergence Line', color: myColUp, thickness: 2 });
paint(myBearLineSeries, { name: 'Bearish Divergence Line', color: myColDn, thickness: 2 });

// ---------- Signals for scanners, alerts and strategies ----------
register_signal(myBullDiv, 'Bullish Divergence');
register_signal(myBearDiv, 'Bearish Divergence');