describe_indicator('The Island MTF', 'price');

// Higher timeframe selector
const myHigherTF = input.select('Higher Timeframe', '240', constants.time_frames);

// NOTE: We rebuild the higher timeframe (HTF) candles ourselves by
// bucketing the current chart's candles into HTF periods based on
// Unix time. This assumes the HTF buckets align to UTC epoch
// boundaries (e.g. 00:00 UTC for daily multiples). If your broker's
// actual HTF candles use a different session alignment, bucket
// boundaries (and therefore signals) may shift slightly.
const myHigherTFMinutes = parseInt(myHigherTF, 10);
assert(!isNaN(myHigherTFMinutes) && myHigherTFMinutes > 0, 'Higher Timeframe must resolve to a number of minutes');
const myBucketSeconds = myHigherTFMinutes * 60;

const myBuySignal = series_of(false);
const mySellSignal = series_of(false);

let myCurrentBucket = null;
let myHtfOpen = null;
let myHtfHigh = -Infinity;
let myHtfLow = Infinity;
let myHtfClose = null;
const myCompletedCandles = [];

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myBucket = Math.floor(time[myIndex] / myBucketSeconds);

	if (myCurrentBucket === null) {
		myCurrentBucket = myBucket;
		myHtfOpen = open[myIndex];
		myHtfHigh = high[myIndex];
		myHtfLow = low[myIndex];
		myHtfClose = close[myIndex];
	}
	else if (myBucket !== myCurrentBucket) {
		// the HTF candle that was being built just closed
		myCompletedCandles.push({
			open: myHtfOpen,
			high: myHtfHigh,
			low: myHtfLow,
			close: myHtfClose
		});

		if (myCompletedCandles.length >= 2) {
			const myCurr4H = myCompletedCandles[myCompletedCandles.length - 1];
			const myPrev4H = myCompletedCandles[myCompletedCandles.length - 2];

			const myBullishOutsideBar = myCurr4H.low < myPrev4H.low && myCurr4H.close > myPrev4H.high;
			const myBearishOutsideBar = myCurr4H.high > myPrev4H.high && myCurr4H.close < myPrev4H.low;

			// signals are plotted one chart bar back (offset -1 in Pine),
			// which lands on the last chart bar of the just-closed HTF candle
			const mySignalIndex = myIndex - 1;

			if (mySignalIndex >= 0) {
				if (myBullishOutsideBar) {
					myBuySignal[mySignalIndex] = true;
				}
				if (myBearishOutsideBar) {
					mySellSignal[mySignalIndex] = true;
				}
			}
		}

		myCurrentBucket = myBucket;
		myHtfOpen = open[myIndex];
		myHtfHigh = high[myIndex];
		myHtfLow = low[myIndex];
		myHtfClose = close[myIndex];
	}
	else {
		myHtfHigh = Math.max(myHtfHigh, high[myIndex]);
		myHtfLow = Math.min(myHtfLow, low[myIndex]);
		myHtfClose = close[myIndex];
	}
}

// Build label marker series (null where no signal, icon where signal fires)
const myBuyMarks = for_every(series_of(0), (_v, _p, _i) => myBuySignal[_i] ? constants.icons.triangle_up : null);
const mySellMarks = for_every(series_of(0), (_v, _p, _i) => mySellSignal[_i] ? constants.icons.triangle_down : null);

paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: 'red' });

// Register signals for use in Scanners, Alerts and Strategy Tester
register_signal(myBuySignal, 'Buy Signal (Bullish Outside Bar)');
register_signal(mySellSignal, 'Sell Signal (Bearish Outside Bar)');