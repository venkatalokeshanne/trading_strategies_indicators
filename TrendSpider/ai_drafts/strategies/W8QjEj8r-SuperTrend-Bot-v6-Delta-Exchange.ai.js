describe_indicator('SuperTrend Bot v6', 'price');

// ═══════════════════════════════════════════════
//  INPUTS
// ═══════════════════════════════════════════════
const myAtrLen = input.number('ATR Length', 10, { min: 1 });
const myFactor = input.number('Factor (Multiplier)', 3.0, { min: 0.1, step: 0.1 });
const myShowLabels = input.boolean('Show BUY / SELL Labels', true);

// ═══════════════════════════════════════════════
//  SUPERTREND CALCULATION (manual, to exactly
//  reproduce Pine's ta.supertrend recursive logic,
//  since the built-in supertrend() does not expose
//  a documented direction output matching Pine's
//  sign convention)
// ═══════════════════════════════════════════════
const myAtr = atr(high, low, close, myAtrLen);
const myHl2 = hl2;

const myUp = series_of(null);
const myDn = series_of(null);
const myTrend = series_of(1);
const mySupertrend = series_of(null);
const myDirection = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myBasicUp = myHl2[myIndex] - myFactor * myAtr[myIndex];
	const myBasicDn = myHl2[myIndex] + myFactor * myAtr[myIndex];

	if (myIndex === 0) {
		myUp[myIndex] = myBasicUp;
		myDn[myIndex] = myBasicDn;
		myTrend[myIndex] = 1;
	}
	else {
		myUp[myIndex] = (close[myIndex - 1] > myUp[myIndex - 1]) ? Math.max(myBasicUp, myUp[myIndex - 1]) : myBasicUp;
		myDn[myIndex] = (close[myIndex - 1] < myDn[myIndex - 1]) ? Math.min(myBasicDn, myDn[myIndex - 1]) : myBasicDn;

		if (myTrend[myIndex - 1] === -1 && close[myIndex] > myDn[myIndex - 1]) {
			myTrend[myIndex] = 1;
		}
		else if (myTrend[myIndex - 1] === 1 && close[myIndex] < myUp[myIndex - 1]) {
			myTrend[myIndex] = -1;
		}
		else {
			myTrend[myIndex] = myTrend[myIndex - 1];
		}
	}

	mySupertrend[myIndex] = (myTrend[myIndex] === 1) ? myUp[myIndex] : myDn[myIndex];

	// direction == -1  ->  price ABOVE supertrend  ->  BULLISH
	// direction ==  1  ->  price BELOW supertrend  ->  BEARISH
	myDirection[myIndex] = -myTrend[myIndex];
}

const myIsBullish = for_every(series_of(null), (_x, _p, _i) => myDirection[_i] === -1);
const myIsBearish = for_every(series_of(null), (_x, _p, _i) => myDirection[_i] === 1);

// Signal fires ONLY on the flip candle (direction change)
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	myBuySignal[myIndex] = (myDirection[myIndex] === -1) && (myDirection[myIndex - 1] === 1);
	mySellSignal[myIndex] = (myDirection[myIndex] === 1) && (myDirection[myIndex - 1] === -1);
}

// ═══════════════════════════════════════════════
//  PLOT SUPERTREND LINE (split into uptrend/downtrend)
// ═══════════════════════════════════════════════
const myUptrendLine = for_every(series_of(null), (_x, _p, _i) => myDirection[_i] === -1 ? mySupertrend[_i] : null);
const myDowntrendLine = for_every(series_of(null), (_x, _p, _i) => myDirection[_i] === 1 ? mySupertrend[_i] : null);

const myUptrendPainted = paint(myUptrendLine, { name: 'Uptrend Line', color: '#2ecc71', thickness: 2, style: 'line' });
const myDowntrendPainted = paint(myDowntrendLine, { name: 'Downtrend Line', color: '#e74c3c', thickness: 2, style: 'line' });

// ═══════════════════════════════════════════════
//  BUY / SELL LABELS
// ═══════════════════════════════════════════════
const myBuyLabelSeries = for_every(series_of(null), (_x, _p, _i) => (myShowLabels && myBuySignal[_i]) ? low[_i] : null);
const mySellLabelSeries = for_every(series_of(null), (_x, _p, _i) => (myShowLabels && mySellSignal[_i]) ? high[_i] : null);

paint(myBuyLabelSeries, { name: 'BUY Labels', color: '#2ecc71', style: 'labels_below' });
paint(mySellLabelSeries, { name: 'SELL Labels', color: '#e74c3c', style: 'labels_above' });

// ═══════════════════════════════════════════════
//  BAR COLOURING (trend context)
// ═══════════════════════════════════════════════
const myBarColors = for_every(series_of(null), (_x, _p, _i) => myDirection[_i] === -1 ? 'rgba(46,204,113,0.3)' : 'rgba(231,76,60,0.3)');
color_candles(myBarColors);

// ═══════════════════════════════════════════════
//  SCANNER / STRATEGY SIGNALS
// ═══════════════════════════════════════════════
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(myIsBullish, 'Bullish Trend');
register_signal(myIsBearish, 'Bearish Trend');