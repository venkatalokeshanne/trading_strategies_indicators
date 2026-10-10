describe_indicator('SuperTrend Bot (Pine v6 Port)', 'price');

// ───────────────────────────────────────────────
// INPUTS (mirroring Pine script's input groups)
// ───────────────────────────────────────────────
const myAtrLenTab = input.tab('SuperTrend Settings');
const myAtrLen = myAtrLenTab.number('ATR Length', 10, { min: 1, max: 200 });
const myFactor = myAtrLenTab.number('Factor Multiplier', 3.0, { min: 0.1, max: 20, step: 0.1 });

const myDisplayTab = input.tab('Display');
const myShowLabels = myDisplayTab.boolean('Show BUY SELL Labels', true);

// ───────────────────────────────────────────────
// SUPERTREND CALCULATION
// supertrend() built-in returns the SuperTrend line
// itself (equivalent to Pine's "supertrend" output).
// Trend direction is derived the same way Pine does
// it internally: price above the line = bullish
// (direction == -1), price below = bearish
// (direction == 1).
// ───────────────────────────────────────────────
const mySupertrendLine = supertrend(myAtrLen, myFactor);

// isBullish/isBearish per candle
const myIsBullish = for_every(close, mySupertrendLine, (_c, _s) => _c > _s);

// Flip detection: signal fires only on the candle where
// direction actually changes, exactly like Pine's
// `direction[1]` comparison.
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myWasBullish = myIsBullish[myIndex - 1];
	const myNowBullish = myIsBullish[myIndex];

	myBuySignal[myIndex] = myNowBullish && !myWasBullish;
	mySellSignal[myIndex] = !myNowBullish && myWasBullish;
}

// Split the SuperTrend line into uptrend/downtrend
// segments, like Pine's two separate plot() calls.
const myUptrendLine = for_every(mySupertrendLine, myIsBullish, (_s, _b) => _b ? _s : null);
const myDowntrendLine = for_every(mySupertrendLine, myIsBullish, (_s, _b) => !_b ? _s : null);

paint(myUptrendLine, { name: 'Uptrend Line', color: '#1fb15a', thickness: 2, style: 'line' });
paint(myDowntrendLine, { name: 'Downtrend Line', color: '#e5473b', thickness: 2, style: 'line' });

// BUY / SELL labels at flip bars
const myBuyLabelSeries = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const mySellLabelSeries = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);

const myBuyLabelToPaint = myShowLabels ? myBuyLabelSeries : constants.empty_series;
const mySellLabelToPaint = myShowLabels ? mySellLabelSeries : constants.empty_series;

paint(myBuyLabelToPaint, { name: 'BuyLabel', style: 'labels_below', color: '#1fb15a' });
paint(mySellLabelToPaint, { name: 'SellLabel', style: 'labels_above', color: '#e5473b' });

// Bar coloring (visual trend context)
const myBarColors = for_every(myIsBullish, _b => _b ? 'rgba(31,177,90,0.3)' : 'rgba(229,71,59,0.3)');
color_candles(myBarColors);

// ───────────────────────────────────────────────
// SIGNALS for scanner/alert/strategy usage
// ───────────────────────────────────────────────
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(myIsBullish, 'Bullish Trend');